import asyncio
import serial_asyncio as serial
from libscrc import crc8

import ctypes
from ctypes import c_uint8, c_size_t,\
    c_uint16, c_uint32, c_uint64,\
    c_int8, c_int16, c_int32, c_int64, POINTER, c_char, sizeof, cast

import zmq
from zmq.asyncio import Context
from .zeta import Channel
from .zeta_pkt import IPCPacket
from .messages import ZetaMessage

ipc = None
context = Context.instance()


class ZT_MSG_U8(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_uint8),
    ]


class ZT_MSG_U16(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_uint16),
    ]


class ZT_MSG_U32(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_uint32),
    ]


class ZT_MSG_U64(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_uint64),
    ]


class ZT_MSG_S8(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_int8),
    ]


class ZT_MSG_S16(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_int16),
    ]


class ZT_MSG_S32(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_int32),
    ]


class ZT_MSG_S64(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_int64),
    ]


class ZT_MSG_BYTES(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("size", c_size_t),
        ("value", c_uint8 * 256),
    ]


class ZT_MSG(ctypes.Union):
    _fields_ = [
        ("s8", ZT_MSG_S8),
        ("u8", ZT_MSG_U8),
        ("s16", ZT_MSG_S16),
        ("u16", ZT_MSG_U16),
        ("s32", ZT_MSG_S32),
        ("u32", ZT_MSG_U32),
        ("s64", ZT_MSG_S64),
        ("u64", ZT_MSG_U64),
        ("bytes", ZT_MSG_BYTES),
    ]


class ZT_MSG_BASE(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [("size", ctypes.c_size_t)]


def repr(self):
    channel_repr = []
    for k, v in self.__dict__.items():
        channel_repr.append("\n" + f"    {k}: {v}")
    return f"CustomMessage({''.join(channel_repr)});"


class IPCChannel():
    def __init__(self, metadata: Channel = None):
        self.metadata = metadata
        self.data = bytes(self.metadata.size)
        self.add_global_message()

    def __repr__(self):
        channel_repr = []
        for k, v in self.__dict__.items():
            channel_repr.append("\n" + f"    {k}: {v}")
        return f"IPCChannel({''.join(channel_repr)});"

    def add_global_message(self):
        if self.metadata.message_obj is not None:
            message_code_factory = ZetaMessage(
                name=self.metadata.message_obj.name,
                **self.metadata.message_obj.msg_format)

            type_name = self.create_struct(self.metadata.message_obj.name,
                                           message_code_factory)
            globals()[self.metadata.message_obj.name] = type(
                self.metadata.message_obj.name, (ZT_MSG_BASE, ),
                {"_fields_": [("size", c_size_t), ("value", type_name)]})

    def create_struct(self, name: str, struct: ZetaMessage):
        size_suffix = ""
        if struct.size > 1:
            size_suffix = f"*{struct.size}"
        if struct.mtype in ["struct", "union"]:
            base_type = ctypes.LittleEndianStructure
            if struct.mtype == "union":
                base_type = ctypes.Union
            fields_dict = []
            for field in struct.fields:
                fields_dict.append(
                    (field.name.strip(), self.create_struct(field.name,
                                                            field)))
            t = type(name.title().strip(), (base_type, ), {
                "_pack_": 1,
                "_fields_": fields_dict
            })
            return eval(f"t{size_suffix}")
        elif struct.mtype == "bitarray":
            fields_dict = []
            unsigned_type = 'u' if struct.mtype_base_type[0] == 'u' else ''
            mtype_base_type = f"c_{unsigned_type}int{struct.mtype_base_type[1:]}"
            for field in struct.fields:
                fields_dict.append(
                    (field.name.strip(), eval(mtype_base_type), field.size))
            t = type(name.title().strip(), (ctypes.LittleEndianStructure, ), {
                "_pack_": 1,
                "_fields_": fields_dict
            })
            return eval(f"t{size_suffix}")
        else:
            return eval(f"c_{struct.mtype_obj.statement[:-2]}{size_suffix}")


class IPC:
    def __init__(self, zeta, channel_changed_queue: asyncio.Queue):
        self.__zeta = zeta
        self.sem = asyncio.Lock()
        self.channel_changed_queue = channel_changed_queue
        self.__channels = []
        self.create_channels()

    def create_channels(self):
        for channel in self.__zeta.channels:
            self.__channels.append(IPCChannel(channel))
        for ipc_channel in self.__channels:
            print(ipc_channel)

    async def digest_packet(self, pkt: IPCPacket):
        if pkt.header.op == IPCPacket.OP_READ:
            pkt.header.op = IPCPacket.OP_READ_RESPONSE
            response_message = await self.read_channel(pkt.header.channel)
            if response_message:
                pkt.header.status = IPCPacket.STATUS_OK
                pkt.set_data(response_message)
            else:
                pkt.header.status = IPCPacket.STATUS_FAILED

        elif pkt.header.op == IPCPacket.OP_WRITE:
            pkt.header.op = IPCPacket.OP_WRITE_RESPONSE
            op_status = await self.set_channel(pkt.header.channel, pkt.data())
            if op_status:
                pkt.header.status = IPCPacket.STATUS_FAILED
            else:
                pkt.header.status = IPCPacket.STATUS_OK
            pkt.clear_data()
        elif pkt.header.op == IPCPacket.OP_DEBUG:
            print(f">>> [Target ISC]: {pkt.data()}")
        return pkt

    async def read_channel(self, cid):
        await self.sem.acquire()
        print("reading channel")
        channel_data = None
        try:
            channel_data = self.__channels[cid].data
        except IndexError:
            pass
        self.sem.release()
        return channel_data

    async def set_channel(self, cid, msg):
        await self.sem.acquire()
        print("changing channel")
        set_result = 0
        try:
            assert self.__channels[
                cid].metadata.read_only == 0, "This is a read-only channel"
            assert self.__channels[cid].metadata.size >= len(
                msg
            ), f"Message sent to channel {cid} is too big. {self.__channels[cid].metadata.size}"
            if self.__channels[cid].data != msg:
                self.__channels[cid].data = msg
                await self.channel_changed_queue.put(bytes([cid]) + msg)
            else:
                print("Message is not new")
        except IndexError:
            set_result = 1
        except AssertionError as err:
            print(err)
            set_result = 2
        self.sem.release()
        return set_result


class SerialDataHandler:
    STATE_DIGEST_HEADER_OP = 0
    STATE_DIGEST_HEADER_DATA_INFO = 1
    STATE_DIGEST_BODY = 2

    def __init__(self):
        self.iqueue = asyncio.Queue()
        self.oqueue = asyncio.Queue()
        self.__buffer = bytearray()
        self.__state = self.STATE_DIGEST_HEADER_OP
        self.__current_pkt = None

    async def append(self, data):
        self.__buffer.extend(data)
        await self.digest()

    async def send_command(self, cmd: IPCPacket):
        print("sending command via uart!")
        await self.oqueue.put(cmd.to_bytes())

    async def digest(self):
        if self.__state == self.STATE_DIGEST_HEADER_OP:
            if len(self.__buffer) >= 2:
                self.__current_pkt = IPCPacket()
                self.__current_pkt.set_header_from_bytes(self.__buffer[:2])
                self.__buffer = self.__buffer[2:]
                if self.__current_pkt.header.has_data != IPCPacket.DATA_UNAVALABLE:
                    self.__state = self.STATE_DIGEST_HEADER_DATA_INFO
                else:
                    print("Only a command!")
        if self.__state == self.STATE_DIGEST_HEADER_DATA_INFO:
            if len(self.__buffer) >= 2:
                self.__current_pkt.set_data_info_from_bytes(self.__buffer[:2])
                self.__buffer = self.__buffer[2:]
                self.__state = self.STATE_DIGEST_BODY
        if self.__state == self.STATE_DIGEST_BODY:
            if len(self.__buffer) == self.__current_pkt.data_info.size:
                if crc8(self.__buffer) == self.__current_pkt.data_info.crc:
                    self.__current_pkt.set_data(bytes(self.__buffer))
                    print("Pkt received by uart: {}".format(
                        self.__current_pkt))
                    await ipc.digest_packet(self.__current_pkt)
                    self.__current_pkt = None
                else:
                    print("CRC error, pkt discarded")
                self.__state = self.STATE_DIGEST_HEADER_OP
                self.__buffer = bytearray()

    async def run(self):
        while (True):
            data = await self.iqueue.get()
            # print("digesting data", data)
            await self.append(data)


async def uart_write_handler(w: asyncio.StreamWriter, oqueue: asyncio.Queue):
    print("Running uart write handler task")
    while True:
        data = await oqueue.get()
        print(f"Data to be sent: {data}")
        w.write(data)


async def uart_read_handler(r, iqueue: asyncio.Queue):
    print("Running uart read handler task")
    while True:
        data = await r.read(1)
        # print("data arrived:", data)
        await iqueue.put(data)


def struct_contents(struct):
    return cast(ctypes.byref(struct),
                POINTER(c_char * sizeof(struct))).contents.raw


def struct_contents_set(struct, raw_data):
    cast(ctypes.byref(struct),
         POINTER(c_char * sizeof(struct))).contents.raw = raw_data


async def callback_handler(channel_changed_queue: asyncio.Queue,
                           zt_data_handler: SerialDataHandler):
    print("Publisher handler running...")
    socket = context.socket(zmq.PUB)
    socket.bind("tcp://*:5556")
    while (True):
        """ The data comes from the channel_changed_queue in the following
        format:

        +------------+-----------+
        |   Byte[0]  |  Byte[1:] |
        +------------+-----------+
        | channel id |  message  |
        +------------+-----------+
        """
        channel, *message = await channel_changed_queue.get()

        pkt = IPCPacket().set_header(
            channel=channel,
            op=IPCPacket.OP_UPDATE,
        ).set_data(bytes(message))
        print("Send packet to subscribers", pkt)
        await zt_data_handler.send_command(pkt)
        await socket.send(pkt.to_bytes())


async def pub_read_handler(channel_changed_queue: asyncio.Queue):
    print("Response handler running...")
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")

    while True:
        pkt = IPCPacket.from_bytes(await socket.recv())
        print(">>> Received request: %s" % pkt)
        await ipc.digest_packet(pkt)
        await socket.send(pkt.to_bytes())


async def isc_run(zeta, port: str = "/dev/ttyACM0", baudrate: int = 115200):
    print("Running main task", zeta)
    global ipc
    channel_changed_queue = asyncio.Queue()
    ipc = IPC(zeta, channel_changed_queue)
    zt_data_handler = SerialDataHandler()
    reader, writer = await serial.open_serial_connection(
        url=port,
        baudrate=baudrate,
    )
    await asyncio.gather(
        uart_write_handler(writer, zt_data_handler.oqueue),
        uart_read_handler(reader, zt_data_handler.iqueue),
        zt_data_handler.run(),
        callback_handler(channel_changed_queue, zt_data_handler),
        pub_read_handler(channel_changed_queue))
