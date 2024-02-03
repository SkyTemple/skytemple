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

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import ConvertibleToFloat


class CanvasScale(float):
    """
    Floats that are clamped to some reasonable values for UI scaling.
    """

    def __new__(cls, x: ConvertibleToFloat):
        x = float(x)
        if x > 128:
            x = 128
        elif x < 0.015625:
            x = 0.015625
        return super().__new__(cls, x)

    def __imul__(self, x: ConvertibleToFloat) -> CanvasScale:
        return CanvasScale(self * float(x))

    def __ifloordiv__(self, x: ConvertibleToFloat) -> CanvasScale:
        return CanvasScale(self // float(x))

    def __itruediv__(self, x: ConvertibleToFloat) -> CanvasScale:
        return CanvasScale(self / float(x))

    def __iadd__(self, x: ConvertibleToFloat) -> CanvasScale:
        return CanvasScale(self + float(x))

    def __isub__(self, x: ConvertibleToFloat) -> CanvasScale:
        return CanvasScale(self - float(x))
