"""skytemple-files data handler that wraps skytemple-files Ssb models in skytemple-ssb-debugger's LoadedSsbFile"""
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
from typing import Optional

from skytemple_files.common.types.data_handler import DataHandler
from skytemple_files.common.types.file_types import FileType
from skytemple_files.script.ssb.handler import SsbHandler
from skytemple_ssb_debugger.model.ssb_files.file import SsbLoadedFile
from skytemple_ssb_debugger.model.ssb_files.file_manager import SsbFileManager


class SsbLoadedFileHandler(DataHandler['SsbLoadedFile']):
    @classmethod
    def deserialize(cls, data: bytes, *, filename, static_data, project_fm, **kwargs) -> 'SsbLoadedFile':
        f = SsbLoadedFile(
            filename, FileType.SSB.deserialize(data, static_data),
            None, project_fm
        )
        f.exps.ssb_hash = SsbFileManager.hash(data)
        return f

    @classmethod
    def serialize(cls, data: 'SsbLoadedFile', *, static_data, **kwargs) -> bytes:
        return FileType.SSB.serialize(data.ssb_model, static_data)

    @classmethod
    def create(cls, filename, static_data, project_fm) -> SsbLoadedFile:
        """Create a new empty Ssb + SsbLoadedFile"""

        return cls.deserialize(FileType.SSB.serialize(SsbHandler.create(static_data), static_data),
                               filename=filename, static_data=static_data, project_fm=project_fm)
