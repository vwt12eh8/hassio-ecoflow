from asyncio import Future, create_task, open_connection, sleep
from logging import getLogger
from typing import Optional

from reactivex import Subject

_LOGGER = getLogger(__name__)


class RxTcpAutoConnection:
    __rx = None
    __tx = None

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.received = Subject[Optional[bytes]]()
        self.__is_open = True
        self.__task = create_task(self.__loop())
        self.__opened = Future()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.close()
        await self.wait_closed()

    def close(self):
        self.__is_open = False
        if self.__rx:
            self.__rx.feed_eof()

    async def drain(self):
        await self.__tx.drain()

    def reconnect(self):
        if self.__rx:
            self.__rx.feed_eof()

    async def wait_closed(self):
        try:
            await self.__task
        except:
            pass
        try:
            await self.__tx.wait_closed()
        except:
            pass

    async def wait_opened(self):
        await self.__opened

    def write(self, data: bytes):
        self.__tx.write(data)

    async def __loop(self):
        while self.__is_open:
            _LOGGER.debug(f"connecting {self.host}")
            try:
                (self.__rx, self.__tx) = await open_connection(self.host, self.port)
            except Exception as ex:
                _LOGGER.debug(ex)
                await sleep(1)
                continue
            _LOGGER.debug(f"connected {self.host}")
            if not self.__opened.done():
                self.__opened.set_result(None)
            try:
                while not self.__rx.at_eof():
                    data = await self.__rx.read(1024)
                    if data:
                        self.received.on_next(data)
            except Exception as ex:
                if type(ex) is not TimeoutError:
                    _LOGGER.exception(ex)
            except BaseException as ex:
                self.received.on_error(ex)
                return
            finally:
                self.__rx.feed_eof()
                self.__tx.close()
            self.received.on_next(None)
        self.received.on_completed()
