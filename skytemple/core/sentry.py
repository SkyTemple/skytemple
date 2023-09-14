"""Module that manages capturing debugging information and sending it to sentry.io."""
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
import logging
import typing
from datetime import datetime
from functools import partial
from typing import Optional, TYPE_CHECKING, Dict, Union, TypeVar, Callable
import atexit
import contextlib

import sentry_sdk
from sentry_sdk import Hub
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.sessions import auto_session_tracking
from sentry_sdk.utils import logger as sentry_sdk_logger

from skytemple.core.logger import SKYTEMPLE_LOGLEVEL, current_log_level
from skytemple.core.ui_utils import version, assert_not_none

if TYPE_CHECKING:
    from skytemple.core.error_handler import ExceptionInfo
    from skytemple_files.common.util import Capturable, Captured
    from skytemple.core.settings import SkyTempleSettingsStore
    from skytemple.core.ssb_debugger.manager import DebuggerManager

# I'm versioning this since it's public knowledge anyway. Please do not misuse this.
SENTRY_ENDPOINT = "https://d4fa0c44839145a39bd6014ca7407ab3@o1155044.ingest.sentry.io/6235225"
already_init = False
logger = logging.getLogger(__name__)
T = TypeVar('T')
APP_START_TIME = datetime.utcnow()


def release_version(is_dev_version: bool):
    """Same as ui_utils.version but for dev builds this will only return the SHA."""
    raw_version = version(ignore_dev=True)
    try:
        return raw_version[raw_version.index('.dev0+') + 6:]
    except ValueError:
        if is_dev_version:
            # Get commit
            import shutil
            git_bin = shutil.which("git")
            if git_bin is None:
                import subprocess
                try:
                    return subprocess.check_output([git_bin, 'rev-parse', 'HEAD']).decode('utf-8')[:8]  # type: ignore
                except subprocess.CalledProcessError as ex:
                    raise ValueError("Was unable to determine dev version") from ex
        else:
            return raw_version


def init():
    global already_init
    if not already_init:
        try:
            is_dev = version() == 'dev'
            if is_dev:
                settings = {
                    'debug': True,
                    'environment': 'development'
                }
            else:
                settings = {
                    'debug': False,
                    'environment': 'production'
                }
            sentry_sdk_logger.setLevel(SKYTEMPLE_LOGLEVEL)
            logger.setLevel(SKYTEMPLE_LOGLEVEL)
            sentry_logging = LoggingIntegration(
                level=current_log_level(),  # Capture as breadcrumbs
                event_level=None  # Send no errors as events
            )
            sentry_sdk.init(
                SENTRY_ENDPOINT,
                traces_sample_rate=0.2,
                release=release_version(is_dev),
                integrations=[sentry_logging],
                **settings  # type: ignore
            )
            # Make sure we actually track this release being used.
            session_ctx = contextlib.ExitStack()
            hub = Hub(Hub.current)
            atexit.register(session_ctx.close)
            session_ctx.enter_context(auto_session_tracking(hub))  # type: ignore
        except Exception as ex:
            logger.error("Failed setting up Sentry", exc_info=ex)
        already_init = True


# noinspection PyBroadException
def try_ignore_err(source: Callable[[], T], sink: Callable[[T], None]):
    try:
        sink(source())
    except Exception as ex:
        logger.error(f"Ignored exception (fn: {source.__name__}) while setting up Sentry.", exc_info=ex)


@typing.no_type_check
def collect_device_context() -> Dict[str, 'Captured']:
    import platform
    import socket
    import psutil
    mem = psutil.virtual_memory()

    screen_info = {}
    try:
        from gi.repository.Gdk import Display
        display = Display.get_default()
        if display is not None:
            mon_geoms = [
                assert_not_none(display.get_monitor(i)).get_geometry()
                for i in range(display.get_n_monitors())
            ]

            x0 = min(r.x for r in mon_geoms)
            y0 = min(r.y for r in mon_geoms)
            x1 = max(r.x + r.width for r in mon_geoms)
            y1 = max(r.y + r.height for r in mon_geoms)
            width, height = x1 - x0, y1 - y0
            screen_info = {
                "screen_resolution": f"{width}x{height}",
                "screen_height_pixels": height,
                "screen_width_pixels": width,
            }
    except Exception:
        pass

    return dict(**{
        "name": socket.gethostname(),
        "arch": platform.machine(),
        "low_memory": mem.percent > 90,
        "memory_size": mem.total,
        "free_memory": mem.available
    }, **screen_info)


def collect_os_context() -> Dict[str, 'Captured']:
    import platform
    uname = platform.uname()
    return {
        "name": platform.system(),
        "version": platform.release(),
        "kernel_version": f"{uname.system} {uname.node} {uname.release} {uname.version} {uname.machine}"
    }


def collect_runtime_context() -> Dict[str, 'Captured']:
    import platform
    return {
        "name": platform.python_implementation(),
        "version": platform.python_version(),
        "raw_description": f"Compiler: {platform.python_compiler()}"
    }


def collect_app_context() -> Dict[str, 'Captured']:
    return {
        "app_start_time": APP_START_TIME.isoformat(),
        "app_version": version()
    }


def if_not_none(obj, cb):
    if obj is None:
        return None
    return cb(obj)


# noinspection PyProtectedMember
def debugger_open_scripts(manager: 'DebuggerManager'):
    if not manager.is_opened():
        return None
    notebook = manager.get_controller().editor_notebook  # type: ignore
    if notebook is None or not hasattr(notebook, '_open_editors') or notebook._open_editors is None:
        return None
    return list(notebook._open_editors.keys())


# noinspection PyProtectedMember
def debugger_focused_script(manager: 'DebuggerManager'):
    if not manager.is_opened():
        return None
    notebook = manager.get_controller().editor_notebook  # type: ignore
    if notebook is None or notebook.currently_open is None or not hasattr(notebook.currently_open, '_explorerscript_view'):
        return None
    exps_view = notebook.currently_open._explorerscript_view
    if exps_view is None:
        return None
    return {
        "name": notebook.currently_open.filename,
        "content": exps_view.get_buffer().props.text
    }


# noinspection PyProtectedMember
def debugger_emulator_state(manager: 'DebuggerManager'):
    if not manager.is_opened():
        return None
    debugger = manager.get_controller().debugger  # type: ignore
    vars = manager.get_controller().variable_controller  # type: ignore
    if debugger is None or vars is None:
        return None
    ges = debugger.ground_engine_state
    if ges is None:
        return None
    ground_state = None
    if ges.running:
        ground_state = {
            "loaded_ssx_files": [({"file_name": x.file_name, "hanger": x.hanger} if x is not None else None) for x in ges.loaded_ssx_files],
            "loaded_ssb_files": [({"file_name": x.file_name, "hanger": x.hanger} if x is not None else None) for x in ges.loaded_ssb_files],
            "actors": [
                ({
                    "id": x.id,
                    "hanger": x.hanger,
                    "direction": x.direction.ssa_id if x.direction is not None else None,
                    "kind": x.kind.name,
                    "sector": x.sector
                 } if x is not None else None) for x in ges.actors
            ],
            "objects": [
                ({
                    "id": x.id,
                    "hanger": x.hanger,
                    "direction": x.direction.ssa_id if x.direction is not None else None,
                    "kind": x.kind.unique_name,
                    "sector": x.sector
                 } if x is not None else None) for x in ges.objects
            ],
            "performers": [
                ({
                    "id": x.id,
                    "hanger": x.hanger,
                    "direction": x.direction.ssa_id if x.direction is not None else None,
                    "kind": x.kind,
                    "sector": x.sector
                 } if x is not None else None) for x in ges.performers
            ],
            "events": [
                ({
                    "id": x.id,
                    "hanger": x.hanger,
                    "kind": x.kind,
                    "sector": x.sector
                 } if x is not None else None) for x in ges.events
            ],
        }
    return {
        "running": ges.running,
        "ground_state": ground_state,
        "game_vars": {k.name: v for k, v in vars._variable_cache.items()} if hasattr(vars, "_variable_cache") and vars._variable_cache is not None else None
    }


# noinspection PyProtectedMember
def collect_state_context() -> Dict[str, 'Captured']:
    from skytemple.controller.main import MainController
    from skytemple.core.rom_project import RomProject
    from skytemple_files.common.util import capture_any
    rom_project = RomProject.get_current()
    try:
        view_state = MainController._instance._current_view_module.collect_debugging_info(  # type: ignore
            MainController._instance._current_view  # type: ignore
        )
        if "models" in view_state:  # type: ignore
            view_state["models"] = {k: capture_any(v) for k, v in view_state["models"].items()}  # type: ignore
    except Exception as ex:
        view_state = {
            "error_collecting": str(ex)
        }
    w, h = MainController.window().get_size()
    dw = if_not_none(MainController.debugger_manager()._opened_main_window, lambda w: w.get_size()[0])
    dh = if_not_none(MainController.debugger_manager()._opened_main_window, lambda w: w.get_size()[1])
    return {
        "skytemple": {
            "window": {
                "width": w,
                "height": h,
            },
            "rom": {
                "filename": if_not_none(rom_project, lambda p: p.get_rom_name()),
                "edition": if_not_none(rom_project, lambda p: p.get_rom_module().get_static_data()),
            },
            "module": type(MainController._instance._current_view_module).__qualname__,
            "view": MainController._instance._current_view_controller_class.__qualname__,  # type: ignore
            "view_state": view_state  # type: ignore
        },
        "ssb_debugger": {
            "window": {
                "width": dw,
                "height": dh,
            },
            "open_scripts": debugger_open_scripts(MainController.debugger_manager()),
            "focused_script": debugger_focused_script(MainController.debugger_manager()),
            #"emulator_state": debugger_emulator_state(MainController.debugger_manager())
        }
    }


def collect_config_context(settings: 'SkyTempleSettingsStore') -> Dict[str, 'Captured']:
    return dict(settings.loaded_config.items())  # type: ignore


def capture(settings: 'SkyTempleSettingsStore', exc_info: Optional['ExceptionInfo'], **error_context_in: 'Capturable'):
    from skytemple_files.common.util import capture_capturable
    error_context: Dict[str, Union[str, int]] = {k: capture_capturable(v) for k, v in error_context_in.items()}  # type: ignore
    try_ignore_err(collect_device_context, lambda c: sentry_sdk.set_context("device", c))
    try_ignore_err(collect_os_context, lambda c: sentry_sdk.set_context("os", c))
    try_ignore_err(collect_runtime_context, lambda c: sentry_sdk.set_context("runtime", c))
    try_ignore_err(collect_app_context, lambda c: sentry_sdk.set_context("app", c))
    try_ignore_err(collect_state_context, lambda c: sentry_sdk.set_context("skytemple_state", c))
    try_ignore_err(partial(collect_config_context, settings), lambda c: sentry_sdk.set_context("config", c))
    sentry_sdk.set_context("error", error_context)
    if exc_info:
        sentry_sdk.capture_exception(exc_info)
    else:
        if 'message' in error_context:
            sentry_sdk.capture_message(f"Error without exception: {error_context['message']}")
        else:
            sentry_sdk.capture_message("Unknown event. See context.")
