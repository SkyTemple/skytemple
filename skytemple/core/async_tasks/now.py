#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
import asyncio
from asyncio import AbstractEventLoop
from typing import Coroutine

from skytemple.core.async_tasks import AsyncTaskRunnerProtocol


class Now(AsyncTaskRunnerProtocol):
    """
    An implementation of an asynchronous task runner, that just runs the task synchronously.
    """
    _instance = None

    @classmethod
    def instance(cls) -> 'Now':
        if cls._instance is None:
            cls._instance = Now()
        return cls._instance

    def __init__(self):
        self._loop: AbstractEventLoop = None  # type: ignore

    def run_task(self, coro: Coroutine):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(self._loop)
                return self._loop.run_until_complete(coro)
            finally:
                try:
                    self._cancel_all_tasks()
                    self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                    if hasattr(self._loop, 'shutdown_default_executor'):
                        self._loop.run_until_complete(self._loop.shutdown_default_executor())
                finally:
                    asyncio.set_event_loop(None)
                    self._loop.close()
                    self._loop = None
        else:
            # NOTE: This requires nested asyncio to be possible.
            return self._loop.run_until_complete(coro)

    # stolen straight from asyncio core :)
    def _cancel_all_tasks(self):
        to_cancel = asyncio.all_tasks(self._loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        self._loop.run_until_complete(
            asyncio.gather(*to_cancel, loop=self._loop, return_exceptions=True)  # type: ignore
        )

        for task in to_cancel:
            if task.cancelled():
                continue
            if task.exception() is not None:
                self._loop.call_exception_handler({
                    'message': 'unhandled exception during asyncio.run() shutdown',
                    'exception': task.exception(),
                    'task': task,
                })
