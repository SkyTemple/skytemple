#  Copyright 2020-2025 SkyTemple Contributors
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
from abc import abstractmethod
from collections.abc import Coroutine
from typing import Protocol


class AsyncTaskRunnerProtocol(Protocol):
    @classmethod
    @abstractmethod
    def instance(cls) -> "AsyncTaskRunnerProtocol":
        pass

    @abstractmethod
    def run_task(self, coro: Coroutine) -> bool:
        """Runs an asynchronous task. Returns True if the task was run."""
