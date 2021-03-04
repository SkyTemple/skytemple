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
from functools import partial
from typing import List, Dict

import pygal
from pygal import Graph
from pygal.style import DarkSolarizedStyle

from skytemple_files.data.level_bin_entry.model import LevelBinEntry, LEVEL_BIN_ENTRY_LEVEL_LEN
from skytemple_files.data.md.model import MdEntry
from skytemple_files.data.waza_p.model import MoveLearnset
from skytemple_files.common.i18n_util import f, _


class LevelUpGraphProvider:
    def __init__(self, monster: MdEntry, level_bin_entry: LevelBinEntry,
                 move_learnset: MoveLearnset, move_strings: List[str]):
        self.monster = monster
        self.level_bin_entry = level_bin_entry
        self.move_learnset = move_learnset
        self.move_strings = move_strings

    def provide(self, add_title=None, dark=False, disable_xml_declaration=False) -> Graph:
        chart = pygal.XY(
            xrange=(1, len(self.level_bin_entry.levels) + 1),
            secondary_range=(0, max([x.experience_required for x in self.level_bin_entry.levels])),
            disable_xml_declaration=disable_xml_declaration
        )
        if add_title:
            chart.title = add_title
        if dark:
            chart.style = DarkSolarizedStyle

        exps = []
        hps = []
        atks = []
        sp_atks = []
        defs = []
        sp_defs = []
        hp_accu = self.monster.base_hp
        atk_accu = self.monster.base_atk
        sp_atk_accu = self.monster.base_sp_atk
        def_accu = self.monster.base_def
        sp_def_accu = self.monster.base_sp_def
        for i, level in enumerate(self.level_bin_entry.levels):
            exps.append((i + 1, level.experience_required))
            hp_accu += level.hp_growth
            hps.append((i + 1, hp_accu))
            atk_accu += level.attack_growth
            atks.append((i + 1, atk_accu))
            sp_atk_accu += level.special_attack_growth
            sp_atks.append((i + 1, sp_atk_accu))
            def_accu += level.defense_growth
            defs.append((i + 1, def_accu))
            sp_def_accu += level.special_defense_growth
            sp_defs.append((i + 1, sp_def_accu))

        max_val = max(hp_accu, atk_accu, sp_atk_accu, def_accu, sp_def_accu)
        moves = []
        processed_levels: Dict[int, int] = {}
        for lum in self.move_learnset.level_up_moves:
            if lum.level_id in processed_levels:
                processed_levels[lum.level_id] += 1
            else:
                processed_levels[lum.level_id] = 1
            count_so_far = processed_levels[lum.level_id] - 1
            moves.append({
                'value': (lum.level_id, max_val + 5 + (5 * count_so_far)),
                'label': self.move_strings[lum.move_id]
            })

        chart.add(_('Exp.'), exps, secondary=True)  # TRANSLATORS: Experience
        chart.add(_('HP'), hps)  # TRANSLATORS: Health Points
        chart.add(_('ATK'), atks)  # TRANSLATORS: Attack
        chart.add(_('Sp. ATK'), sp_atks)  # TRANSLATORS: Special Attack
        chart.add(_('DEF'), defs)  # TRANSLATORS: Defense
        chart.add(_('Sp. DEF'), sp_defs)  # TRANSLATORS: Special Defense
        chart.add(_('Moves'), moves, stroke=False,
                  formatter=lambda x: f(_('at level {x[0]}')))

        return chart


if __name__ == '__main__':
    def main_test():
        import os
        from skytemple_files.common.types.file_types import FileType
        from ndspy.rom import NintendoDSRom
        from skytemple_files.common.util import get_ppmdu_config_for_rom
        # Testing.
        base_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
        rom = NintendoDSRom.fromFile(os.path.join(base_dir, 'skyworkcopy_us.nds'))
        config = get_ppmdu_config_for_rom(rom)
        out_dir = '/tmp/monster_graphs'
        os.makedirs(out_dir, exist_ok=True)
        monster_md = FileType.MD.deserialize(rom.getFileByName('BALANCE/monster.md'))
        level_bin = FileType.BIN_PACK.deserialize(rom.getFileByName('BALANCE/m_level.bin'))
        waza_p = FileType.WAZA_P.deserialize(rom.getFileByName('BALANCE/waza_p.bin'))
        move_string_block = config.string_index_data.string_blocks['Move Names']
        monster_name_block = config.string_index_data.string_blocks['Pokemon Names']
        strings = FileType.STR.deserialize(rom.getFileByName('MESSAGE/text_e.str'))
        move_strings = strings.strings[move_string_block.begin:move_string_block.end]
        monster_strings = strings.strings[monster_name_block.begin:monster_name_block.end]

        level_bin = level_bin

        # The level_bin has no entry for monster 0.
        for monster, lbinentry_bin, waza_entry in zip(monster_md.entries[1:], level_bin, waza_p.learnsets[1:]):
            level_bin_entry = FileType.LEVEL_BIN_ENTRY.deserialize(
                FileType.COMMON_AT.deserialize(FileType.SIR0.deserialize(lbinentry_bin).content).decompress()
            )
            graph_provider = LevelUpGraphProvider(monster, level_bin_entry, waza_entry, move_strings)
            g = graph_provider.provide(
                f'{monster_strings[monster.md_index]}',
                dark=True
            )
            g.render_to_file(os.path.join(out_dir, f'{monster.md_index}.svg'))
            g.render_to_png(os.path.join(out_dir, f'{monster.md_index}.png'), dpi=92)


    main_test()
