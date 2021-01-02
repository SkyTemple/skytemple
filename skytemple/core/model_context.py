#  Copyright 2020-2021 Parakoopa and the SkyTemple Contributors
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
import threading
from typing import TypeVar, Generic

T = TypeVar('T')


class ModelContext(Generic[T]):
    """
    ContextManager that wraps a model for thread-safe data access.
    References to the model are invalid outside of the context provided.
    """
    def __init__(self, model: T):
        self._model = model
        self._lock = threading.Lock()

    def __enter__(self) -> T:
        self._lock.acquire()
        return self._model

    def __exit__(self, exc_type, value, traceback):
        self._lock.release()
