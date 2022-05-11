from asyncio import (Future, StreamWriter, create_task, open_connection,
                     shield, sleep, wait_for)
from logging import Logger
from typing import Callable

from . import parse_cmd


class EcoFlowLocalClient:
    connected_handler: Callable[[], None] = None
    disconnected_handler: Callable[[], None] = None
    received_handler: Callable[[tuple[int, int, int], bytes], None] = None
    __tx = None

    def __init__(self, host: str, logger: Logger, timeout=15):
        self.host = host
        self.logger = logger
        self.timeout = timeout
        self.__listeners = dict[int, Callable[[
            tuple[int, int, int], bytes], None]]()

    async def close(self):
        if self.__tx.done():
            tx = self.__tx.result()
            try:
                tx.close()
                await tx.wait_closed()
            except:
                pass

    async def request(self, data: bytes):
        future = Future[bytes]()

        async def send():
            while not future.done():
                try:
                    await self.send(data)
                except Exception as ex:
                    if not future.done():
                        future.set_exception(ex)
                    break
                await sleep(2)

        def recv(cmd: tuple[int, int, int], args: bytes):
            if future.done():
                return
            if (data[13], data[14], data[15]) == cmd:
                future.set_result(args)

        self.__listeners[id(recv)] = recv
        create_task(send())
        try:
            return await wait_for(shield(future), self.timeout)
        finally:
            future.cancel()
            self.__listeners.pop(id(recv))

    def run(self):
        if self.__tx:
            raise RuntimeError()
        self.__tx = Future[StreamWriter]()
        create_task(self.__run())

    async def send(self, data: bytes):
        tx = await self.__tx
        tx.write(data)
        await tx.drain()

    async def __run(self):
        connected = False
        while True:
            try:
                (rx, tx) = await open_connection(self.host, 8055)
            except:
                continue
            self.__tx.set_result(tx)
            while not rx.at_eof():
                try:
                    data = await wait_for(rx.read(1024), self.timeout)
                except Exception:
                    break
                if not connected and self.connected_handler:
                    self.connected_handler()
                connected = True
                rcv = parse_cmd(data)
                if rcv is None:
                    continue
                for f in [*self.__listeners.values(), self.received_handler]:
                    try:
                        if f:
                            f(*rcv)
                    except Exception as ex:
                        self.logger.exception(ex)
            if connected and self.disconnected_handler:
                self.disconnected_handler()
            connected = False
            if tx.is_closing():
                break
            self.__tx = Future[StreamWriter]()
            try:
                tx.close()
                await tx.wait_closed()
            except:
                pass
