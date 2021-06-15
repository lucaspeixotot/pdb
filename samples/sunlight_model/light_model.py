import asyncio
import zmq
from zmq.asyncio import Context
from colored import fg, bg, attr
from zeta import IPCPacket, create_base_message

context = Context.instance()


async def sub_handler():
    print("\nConnecting to zeta host IPC…", end="")
    socket = context.socket(zmq.SUB)
    socket.connect("tcp://localhost:5556")
    socket.setsockopt(zmq.SUBSCRIBE, b'\x01')
    print("[OK]\n")

    ZT_MSG = create_base_message("./zeta.yaml")
    msg = ZT_MSG()

    status = "OFF"
    color = 59
    print(f'\r LIGHT STATUS {status}:{bg(color)}  {attr(0)}', end="")
    while (True):
        pkt = IPCPacket.from_bytes(await socket.recv())
        pkt.struct_contents_set(msg)
        if msg.LIGHT_STATUS_MSG.value.is_on:
            status = "ON "
            color = 220
        else:
            status = "OFF"
            color = 59
        print(f'\r LIGHT STATUS {status}:{bg(color)}  {attr(0)}', end="")


try:
    asyncio.run(sub_handler())
except KeyboardInterrupt:
    exit(1)
