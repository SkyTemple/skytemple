"""Manages asyncio event loop in a separate loop handler thread"""
#  Copyright 2020 Parakoopa
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
import traceback
from threading import Thread

from gi.repository import GLib


class AsyncTaskRunner(Thread):
    _instance = None
    daemon = True

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance.start()
        return cls._instance

    @classmethod
    def end(cls):
        if cls._instance:
            cls._instance.stop()
            cls._instance = None

    def __init__(self):
        Thread.__init__(self)
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_forever()
        except (KeyboardInterrupt, SystemExit):
            pass

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)

    def run_task(self, coro):
        """Runs an asynchronous task"""
        return asyncio.run_coroutine_threadsafe(self.coro_runner(coro), self.loop)

    @staticmethod
    async def coro_runner(coro):
        """Wrapper class to use ensure_future, to deal with uncaught exceptions..."""
        try:
            return await asyncio.ensure_future(coro)
        except BaseException as ex:
            # TODO Proper logging
            print(f"Uncaught AsyncTaskRunner task exception:")
            print(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))
