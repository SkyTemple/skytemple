"""skytemple-files data handler that wraps skytemple-files Ssb models in skytemple-ssb-debugger's LoadedSsbFile"""
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
from skytemple_files.common.types.data_handler import DataHandler
from skytemple_files.common.types.file_types import FileType
from skytemple_ssb_debugger.model.ssb_files.file import SsbLoadedFile


class SsbLoadedFileHandler(DataHandler['SsbLoadedFile']):
    @classmethod
    def deserialize(cls, data: bytes, *, filename, static_data, ssb_file_manager, project_fm, **kwargs) -> 'SsbLoadedFile':
        f = SsbLoadedFile(
            filename, FileType.SSB.deserialize(data, static_data),
            ssb_file_manager, project_fm
        )
        f.exps.ssb_hash = ssb_file_manager.hash(data)
        return f

    @classmethod
    def serialize(cls, data: 'SsbLoadedFile', *, static_data, **kwargs) -> bytes:
        return FileType.SSB.serialize(data.ssb_model, static_data)
