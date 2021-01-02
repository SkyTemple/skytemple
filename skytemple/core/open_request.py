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


# These constants are some request types used by core modules.
REQUEST_TYPE_SCENE     = 'scene'   # identifier is the map name.
REQUEST_TYPE_MAP_BG    = 'map_bg'  # identifier is the map bg id.
REQUEST_TYPE_SCENE_SSE = 'sse'     # identifier is the map name.
REQUEST_TYPE_SCENE_SSS = 'sss'     # identifier is (map name, file name). (file name != path)
REQUEST_TYPE_SCENE_SSA = 'ssa'     # identifier is (map name, file name). (file name != path)
REQUEST_TYPE_DUNGEONS  = "dungeon_list" # no identifier
REQUEST_TYPE_DUNGEON_TILESET = 'dungeon_tileset'  # identifier is the tileset id
REQUEST_TYPE_DUNGEON_FIXED_FLOOR = 'dungeon_fixed_floor'  # identifier is the fixed floor id
REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY = 'dungeon_fixed_floor_entity'  # identifier is the entity id to highlight


class OpenRequest:
    """
    This request can be given to the RomProject (request_open) to open another resource of the ROM.
    The request will be forwarded to all modules and the first module to take it, will get it's returned
    view opened and focused in the view tree.
    """
    def __init__(self, type: str, identifier: any):
        """
        :param type:       A string identifier for the type of the requested resource
        :param identifier: The identifier for the instance of the type to open the view for, usually str or int.
        """
        self.type = type
        self.identifier = identifier
