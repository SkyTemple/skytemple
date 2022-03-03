#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import sys
from asyncio import AbstractEventLoop

import gi

from skytemple.core.logger import async_handle_exeception
from skytemple_files.common.i18n_util import _

gi.require_version('Gtk', '3.0')
import asyncio
from typing import Coroutine, Optional
from enum import Enum, auto

import gbulb
from gi.repository import Gtk, GLib
from typing import Callable

from skytemple.core.async_tasks.now import Now
from skytemple_files.common.task_runner import AsyncTaskRunner


class AsyncEventLoopType(Enum):
    # The Glib Gtk main loop is running, and no PEP 3156 compliant event loop is running.
    GLIB_ONLY = auto()
    # Run a PEP 3156 compliant event loop using the Glib Gtk main loop using Gbulb.
    # This allows for real concurrency (AsyncTaskRunnerType.EVENT_LOOP_CONCURRENT).
    GBULB = auto()


class AsyncTaskRunnerType(Enum):
    # Run asynchronous tasks in a separate thread.
    THREAD_BASED = auto()
    # Starts a new asyncio event loop to run the coroutine in immediately.
    EVENT_LOOP_BLOCKING = auto()
    # Waits for GLib idle, then starts a new asyncio event loop to run the coroutine in immediately.
    EVENT_LOOP_BLOCKING_SOON = auto()
    # Schedule the coroutine as a real task on the event loop to be run as soon as there is time.
    EVENT_LOOP_CONCURRENT = auto()


class AsyncConfiguration(Enum):
    THREAD_BASED = "thread_based", _("Thread-based"), AsyncEventLoopType.GLIB_ONLY, AsyncTaskRunnerType.THREAD_BASED
    BLOCKING = "blocking", _("Synchronous"), AsyncEventLoopType.GLIB_ONLY, AsyncTaskRunnerType.EVENT_LOOP_BLOCKING
    BLOCKING_SOON = "blocking_soon", "GLib", AsyncEventLoopType.GLIB_ONLY, AsyncTaskRunnerType.EVENT_LOOP_BLOCKING_SOON
    GBULB = "gbulb", _("Using Gbulb event loop"), AsyncEventLoopType.GBULB, AsyncTaskRunnerType.EVENT_LOOP_CONCURRENT

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, name_localized: str = None, event_loop_type: AsyncEventLoopType = None, async_task_runner_type: AsyncTaskRunnerType = None):
        self.name_localized = name_localized
        self.event_loop_type = event_loop_type
        self.async_task_runner_type = async_task_runner_type

    def available(self):
        return self != AsyncConfiguration.GBULB  # TODO: Need to iron out some issues.
        if self == AsyncConfiguration.GBULB and sys.platform.startswith('win'):
            # Currently not available under Windows!
            return False
        return True

    @classmethod
    def default(cls) -> 'AsyncConfiguration':
        if AsyncConfiguration.GBULB.available():
            return AsyncConfiguration.GBULB
        return AsyncConfiguration.BLOCKING_SOON


class AsyncTaskDelegator:
    """Allows SkyTemple to run asynchronous tasks without blocking the whole UI."""
    _config_type = None

    @classmethod
    def run_main(cls, main: Callable, *main_args, **main_kwargs):
        try:
            main(*main_args, **main_kwargs)
            if cls.config_type().event_loop_type == AsyncEventLoopType.GLIB_ONLY:
                Gtk.main()
            elif cls.config_type().event_loop_type == AsyncEventLoopType.GBULB:
                gbulb.install(gtk=True)
                gbulb.get_event_loop().set_exception_handler(async_handle_exeception)
                from skytemple.core.events.manager import EventManager
                GLib.idle_add(EventManager.instance().async_init)
                asyncio.get_event_loop().run_forever()
            else:
                raise RuntimeError("Invalid async configuration")
        except OSError as ex:
            if hasattr(ex, 'winerror') and ex.winerror == 6:
                # [WinError 6] The handle is invalid
                # Originates in gi/_ossighelper.py - Some issues with socket cleanup. We will ignore that.
                pass
            else:
                raise
        except (SystemExit, KeyboardInterrupt):
            pass
        finally:
            # TODO: Currently always required for Debugger compatibility
            #  (since that ALWAYS uses this async implementation)
            AsyncTaskRunner.end()

    @classmethod
    def run_task(cls, coro: Coroutine):
        """
        This runs the coroutine, depending on the current configuration for async tasks.
        """
        if cls.config_type().async_task_runner_type == AsyncTaskRunnerType.THREAD_BASED:
            AsyncTaskRunner.instance().run_task(coro)
        elif cls.config_type().async_task_runner_type == AsyncTaskRunnerType.EVENT_LOOP_BLOCKING:
            Now.instance().run_task(coro)
        elif cls.config_type().async_task_runner_type == AsyncTaskRunnerType.EVENT_LOOP_BLOCKING_SOON:
            GLib.idle_add(lambda: Now.instance().run_task(coro))
        elif cls.config_type().async_task_runner_type == AsyncTaskRunnerType.EVENT_LOOP_CONCURRENT:
            asyncio.create_task(coro)
        else:
            raise RuntimeError("Invalid async configuration")

    @classmethod
    async def buffer(cls):
        """Pauses and continues running other tasks for a while, if other tasks are still pending.
        This is mostly useful for giving the UI loop a chance to catch up during heavy computations.
        This is only supported with AsyncRunnerType.EVENT_LOOP_CONCURRENT, otherwise this does nothing."""
        if cls.config_type().async_task_runner_type == AsyncTaskRunnerType.EVENT_LOOP_CONCURRENT:
            await asyncio.sleep(0.001)

    @classmethod
    def config_type(cls):
        if cls._config_type is None:
            from skytemple.core.settings import SkyTempleSettingsStore
            cls._config_type = SkyTempleSettingsStore().get_async_configuration()
        return cls._config_type

    @classmethod
    def support_aio(cls):
        return cls.config_type().async_task_runner_type == AsyncTaskRunnerType.EVENT_LOOP_CONCURRENT

    @classmethod
    def event_loop(cls) -> Optional[AbstractEventLoop]:
        """Returns the current event loop."""
        return asyncio.get_event_loop()
