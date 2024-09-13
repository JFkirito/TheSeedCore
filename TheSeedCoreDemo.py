import asyncio

from TheSeedCore import *


async def testFunction():
    print("This is TheSeedCore. Welcome home sir")
    for i in range(10):
        await asyncio.sleep(1)
        print("System shutdown countdown:", 10 - i)
    print("System shutdown")
    LinkStop()


if __name__ == "__main__":
    ConnectNERvGear()
    MainEventLoop.create_task(testFunction())
    LinkStart()
