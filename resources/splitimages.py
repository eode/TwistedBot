# -*- coding: utf-8 -*-
"""
Created on Sat Mar  9 16:29:33 2013

@author: silver
"""

import Image
try:
    from path import path
except:
    print "This module requires path.py (try pip install path.py)"


X = 0
Y = 1

def make_tiles(file_name, tile_width, tile_height, out_dir='',
               name_fmt="{orig_base}x{tile_x}y{tile_y}.{ext}"):
    """make_tiles(file_name, tile_width, tile_height, out_dir, name_fmt) -> []
    file_name := path to the file to be split into tiles
    tile_width := width for each tile (must divide evenly into image size)
    tile_height := height for each tile (must divide evenly into image size)
    out_dir := if none is given, make a dir named after file_name in the same
               parent folder -- e.g., 'foo/bar.png' would create 'foo/bar/'.
               This means that an image without an extension will try to
TODO: explain what happens when no extension is used
               out_dir will be created in full -- e.g., if "foo/bar/baz" is
               specified, and only 'foo' exists, both bar and baz will be
               created.
    name_fmt := the format of the out file names, structure explained below

    name_fmt may include any of these variable names, enclosed in braces:
        file_name: original file_name (with full absolute path)
        orig_dir: original file_name's parent dir
        orig_base: original file_name without extension or parent dir
        size_x: original image width
        size_y: original image height
        pixel_x/pixel_y: starting positions of tile (top-left corner)
        pixend_x/pixend_y: ending positiions of tile (bottom-right corner)
        tile_x/tile_y: position of tile (by tile, not by pixel)
        tile_width: the width of the tile
        tile_height: the height of the tile
        tile_num: the number of the tiles as processed in order, from
                  left-to-right, then top-to-bottom
        ext: file extension (you probably want this on the end)

    default name_fmt is "{orig_base}x{tile_x}y{tile_y}{ext}"
    """
    file_name = path(file_name).abspath()
    orig_dir = file_name.parent
    orig_base = file_name.basename().splitext()[0]
    out_dir = path(out_dir) if out_dir else file_name.parent / orig_base
    ext = file_name.splitext()[1]
    tile_width, tile_height = int(tile_width), int(tile_height)

    if not out_dir.exists():
        out_dir.makedirs()

    image = Image.open(file_name)

    if image.size[X] % tile_width != 0:
        msg = "Image of width {} cannot be broken into tiles of width {}."
        raise ValueError(msg.format(image.size[X], tile_width))
    if image.size[Y] % tile_height != 0:
        msg = "Image of height %s cannot be broken into tiles of height %s."
        raise ValueError(msg.format(image.size[Y], tile_height))

    pixel_x = pixel_y = 0
    tile_x = tile_y = 0
    pixend_x = pixel_x + tile_width
    pixend_y = pixel_y + tile_width
    tile_num = 0
    while pixel_y < image.size[Y]:
        while pixel_x < image.size[X]:
            tile = image.crop((pixel_x, pixel_y, pixend_x, pixend_y))
            out_name = out_dir/name_fmt.format(**locals())
            if out_name.abspath == file_name:
                msg = ("Choose a different name_fmt -- an out_name is"
                       "identical to the original file_name")
                raise ValueError(msg)
            tile.save(out_name)
            pixel_x = pixend_x
            pixend_x += tile_width
            tile_num += 1
            tile_x += 1
        pixel_y = pixend_y
        pixend_y += tile_height
        tile_y += 1
        # reset x to first tile in row
        pixel_x = 0
        pixend_x = pixel_x + tile_width
        tile_x = 0


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    help_ = False
    for arg in sys.argv[1:]:
        if arg in ('?', '/help', '--help', '-?', '/?'):
            help_ = True
            break
    if not args:
        help_ = True
    if help_:
        print make_tiles.__doc__
        print "command-line: use positional arguments for the make_tiles method."
        exit()
    make_tiles(*sys.argv[1:])
