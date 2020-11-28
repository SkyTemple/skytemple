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
from typing import Generator, Tuple, Optional, Callable, List

from PIL import Image

from skytemple_files.graphics.kao.model import Kao, KAO_IMG_IMG_DIM, KAO_IMG_METAPIXELS_DIM, SUBENTRIES, KaoImage

PORTRAIT_SIZE = KAO_IMG_IMG_DIM * KAO_IMG_METAPIXELS_DIM
PORTRAIT_TILE_X = 5
PORTRAIT_TILE_Y = 8


class SpriteBotSheet:
    @classmethod
    def create(cls, kao: Kao, portrait_item_id: int) -> Image.Image:
        image = Image.new('RGBA', (PORTRAIT_SIZE * PORTRAIT_TILE_X, PORTRAIT_SIZE * PORTRAIT_TILE_Y))
        max_x = 1
        max_y = 1
        for idx, (unflipped, flipped) in enumerate(cls._iter_portraits(kao, portrait_item_id)):
            max_x, max_y = cls._place_portrait(image, idx, max_x, max_y, unflipped, False)
            max_x, max_y = cls._place_portrait(image, idx, max_x, max_y, flipped, True)

        return image.crop((0, 0, max_x, max_y))

    @classmethod
    def load(cls, fn: str, portrait_name_fn: Callable[[int], str]) -> Generator[Tuple[int, Image.Image], None, None]:
        img = Image.open(fn)
        occupied = cls._verify_portraits(img, portrait_name_fn)
        for xx, column in enumerate(occupied):
            for yy, o in enumerate(column):
                if o:
                    si = cls._convert_index((yy * PORTRAIT_TILE_X + xx))
                    yield si, img.crop((
                        xx * PORTRAIT_SIZE, yy * PORTRAIT_SIZE,
                        (xx + 1) * PORTRAIT_SIZE, (yy + 1) * PORTRAIT_SIZE,
                    ))

    @classmethod
    def _iter_portraits(
            cls, kao: Kao, portrait_item_id: int
    ) -> Generator[Tuple[Optional[KaoImage], Optional[KaoImage]], None, None]:
        for i in range(0, SUBENTRIES, 2):
            yield kao.get(portrait_item_id, i), kao.get(portrait_item_id, i + 1)

    @classmethod
    def _place_portrait(
            cls, image: Image.Image, idx: int, max_x: int, max_y: int, kao_image: Optional[KaoImage], flip: bool
    ) -> Tuple[int, int]:
        """Original author: Audino (https://github.com/audinowho)"""
        if kao_image is None:
            return max_x, max_y
        place_x = PORTRAIT_SIZE * (idx % PORTRAIT_TILE_X)
        place_y = PORTRAIT_SIZE * (idx // PORTRAIT_TILE_X)
        # handle flips
        if flip:
            place_y += 4 * PORTRAIT_SIZE
        image.paste(kao_image.get(), (place_x, place_y))
        return max(max_x, place_x + PORTRAIT_SIZE), max(max_y, place_y + PORTRAIT_SIZE)

    @classmethod
    def _verify_portraits(cls, img: Image.Image, portrait_name_fn: Callable[[int], str]) -> List[List[Optional[bool]]]:
        """
        Verifies the input sheet and returns a matrix of occupied portraits.

        Original author: Audino (https://github.com/audinowho)
        """
        # make sure the dimensions are sound
        if img.size[0] % PORTRAIT_SIZE != 0 or img.size[1] % PORTRAIT_SIZE != 0:
            raise ValueError(f"Portrait has an invalid size of {img.size}, Not divisble by {PORTRAIT_SIZE}x{PORTRAIT_SIZE}")

        img_tile_size = (img.size[0] // PORTRAIT_SIZE, img.size[1] // PORTRAIT_SIZE)
        max_size = (PORTRAIT_TILE_X * PORTRAIT_SIZE, PORTRAIT_TILE_Y * PORTRAIT_SIZE)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            raise ValueError(f"Portrait has an invalid size of {img.size}, exceeding max of {max_size}")

        in_data = img.convert('RGBA').getdata()
        occupied = [[]] * PORTRAIT_TILE_X
        for ii in range(PORTRAIT_TILE_X):
            occupied[ii] = [None] * PORTRAIT_TILE_Y

        # iterate every portrait and ensure that all pixels in that portrait are either solid or transparent
        rogue_pixels = []
        rogue_tiles = []
        for xx in range(PORTRAIT_TILE_X):
            for yy in range(PORTRAIT_TILE_Y):
                if xx >= img_tile_size[0] or yy >= img_tile_size[1]:
                    continue
                first_pos = (xx * PORTRAIT_SIZE, yy * PORTRAIT_SIZE)
                first_pixel = in_data[first_pos[1] * img.size[0] + first_pos[0]]
                occupied[xx][yy] = (first_pixel[3] > 0)

                is_rogue = False
                for mx in range(PORTRAIT_SIZE):
                    for my in range(PORTRAIT_SIZE):
                        cur_pos = (first_pos[0] + mx, first_pos[1] + my)
                        cur_pixel = in_data[cur_pos[1] * img.size[0] + cur_pos[0]]
                        cur_occupied = (cur_pixel[3] > 0)
                        if cur_occupied and cur_pixel[3] < 255:
                            rogue_pixels.append(cur_pos)
                        if cur_occupied != occupied[xx][yy]:
                            is_rogue = True
                            break
                    if is_rogue:
                        break
                if is_rogue:
                    rogue_str = portrait_name_fn(cls._convert_index((yy * PORTRAIT_TILE_X + xx)))
                    rogue_tiles.append(rogue_str)

        if len(rogue_pixels) > 0:
            raise ValueError(f"Semi-transparent pixels found at: {rogue_pixels}")
        if len(rogue_tiles) > 0:
            raise ValueError(f"The following emotions have transparent pixels: {rogue_tiles}")

        # make sure all mirrored emotions have their original emotions
        # make sure if there is one mirrored emotion, there is all mirrored emotions
        halfway = PORTRAIT_TILE_Y // 2
        flipped_tiles = []
        has_one_flip = False
        for xx in range(PORTRAIT_TILE_X):
            for yy in range(halfway, PORTRAIT_TILE_Y):
                if occupied[xx][yy] is None:
                    continue
                if occupied[xx][yy]:
                    has_one_flip = True
                if occupied[xx][yy] and not occupied[xx][yy-halfway]:
                    rogue_str = portrait_name_fn(cls._convert_index((yy * PORTRAIT_TILE_X + xx)))
                    flipped_tiles.append(rogue_str)

        if has_one_flip and len(flipped_tiles) > 0:
            raise ValueError(f"File should have original and flipped versions of emotions: {str(flipped_tiles)}")

        return occupied

    @classmethod
    def _convert_index(cls, i):
        if i >= PORTRAIT_TILE_X * PORTRAIT_TILE_Y / 2:
            return i * 2 - (PORTRAIT_TILE_X * PORTRAIT_TILE_Y - 1)
        return i * 2
