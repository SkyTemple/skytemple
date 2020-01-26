"""Utilities for dealing with images"""
import cairo


def pil_to_cairo_surface(im, format=cairo.FORMAT_ARGB32) -> cairo.Surface:
    """
    :param im: Pillow Image
    :param format: Pixel format for output surface
    """
    assert format in (cairo.FORMAT_RGB24, cairo.FORMAT_ARGB32), "Unsupported pixel format: %s" % format
    arr = bytearray(im.tobytes('raw', 'BGRa'))
    surface = cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)
    return surface
