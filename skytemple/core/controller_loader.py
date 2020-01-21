"""Module to load a module view and controller"""
from typing import TYPE_CHECKING

from skytemple.core.task import AsyncTaskRunner
from skytemple.core.ui_signals import SIGNAL_VIEW_LOADED_ERROR

if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule


async def load_controller(module: 'AbstractModule', controller_class, item_id: int, go=None):
    # TODO
    try:
        raise NotImplementedError("Not implemented yet")
    except NotImplementedError as err:
        if go:
            AsyncTaskRunner.emit(go, SIGNAL_VIEW_LOADED_ERROR, err)
