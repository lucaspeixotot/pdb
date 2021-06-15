import asyncio
import zmq
from zmq.asyncio import Context
import ctypes
from colored import fg, bg, attr
from zeta import IPCPacket, create_base_message

context = Context.instance()


async def sub_handler(status_queue):
    print("\nConnecting to zeta host IPC sub…", end="")
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5556")
    socket.setsockopt(zmq.SUBSCRIBE, b'\x00')
    print("[OK]\n")

    ZT_MSG = create_base_message("./zeta.yaml")
    msg = ZT_MSG()

    while (True):
        pkt = IPCPacket.from_bytes(await socket.recv())
        pkt.struct_contents_set(msg)
        must_turn_on = False
        if msg.SUNLIGHT_LEVEL_MSG.value.level < 10:
            must_turn_on = True
        await status_queue.put(must_turn_on)


async def pub_handler(status_queue):

    #  Socket to talk to server
    print("\nConnecting to zeta host IPC pub…", end="")
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")
    print("[OK]\n")

    ZT_MSG = create_base_message("./zeta.yaml")

    while (True):
        must_turn_on = await status_queue.get()
        light_status = ZT_MSG()
        light_status.LIGHT_STATUS_MSG.value.is_on = must_turn_on
        light_status.LIGHT_STATUS_MSG.size = ctypes.sizeof(
            light_status.LIGHT_STATUS_MSG.value)
        pkt = IPCPacket().set_header(
            channel=1,
            op=IPCPacket.OP_WRITE,
        ).set_data_with_struct(light_status.LIGHT_STATUS_MSG)

        await socket.send(pkt.to_bytes())
        # receive response
        await socket.recv()

    socket.close()


async def main():
    # global ZT_MSG
    # ZT_MSG = create_base_message("./zeta.yaml")
    # s = ZT_MSG()
    status_queue = asyncio.Queue()
    await asyncio.gather(pub_handler(status_queue), sub_handler(status_queue))


try:
    asyncio.run(main())
except KeyboardInterrupt:
    exit(1)
