#!/usr/bin/env python3
"""
Draw the app icon: one symbol in the program's own style, white on a dark
rounded square, using the symbol generator's line geometry.

Writes packaging/icons/bigraph.png (256 x 256) and packaging/icons/bigraph.ico
(16 to 256 pixels). Needs Pillow (in requirements-dev.txt).

Usage:
    python3 packaging/make_icon.py
"""

import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

from bigraph.symbols import SymbolGenerator  # noqa: E402

# The symbol: a crossbar at the top, a diagonal from the middle, and an
# inward diagonal at the bottom
SYMBOL = {
    'orientation': 'vertical',
    'extensions': [
        {'position': 'start', 'side': 'left', 'type': 'perpendicular'},
        {'position': 'start', 'side': 'right', 'type': 'perpendicular'},
        {'position': 'middle', 'side': 'right', 'type': 'toward_end'},
        {'position': 'end', 'side': 'left', 'type': 'toward_start'},
    ],
}

BACKGROUND = (28, 36, 52, 255)
STROKE = (245, 245, 240, 255)
SIZE = 1024  # drawn large, then scaled down for smooth edges


def segments(generator):
    """The symbol's lines, in the generator's 100 x 100 coordinates"""
    start, end = generator.margin, generator.symbol_size - generator.margin
    lines = [((start, 0), (end, 0))]
    lines += [generator._extension_segment(SYMBOL['orientation'], ext) for ext in SYMBOL['extensions']]
    return [(generator._to_xy(SYMBOL['orientation'], a), generator._to_xy(SYMBOL['orientation'], b))
            for a, b in lines]


def draw(size=SIZE):
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    canvas.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=BACKGROUND)

    generator = SymbolGenerator(seed=0)
    scale = size / generator.symbol_size
    width = round(generator.line_width * scale * 1.6)
    for (x1, y1), (x2, y2) in segments(generator):
        points = [(x1 * scale, y1 * scale), (x2 * scale, y2 * scale)]
        canvas.line(points, fill=STROKE, width=width)
        # Square caps, as in the SVG symbols
        for x, y in points:
            half = width / 2
            canvas.rectangle([x - half, y - half, x + half, y + half], fill=STROKE)
    return image


def main():
    out = os.path.join(HERE, 'icons')
    os.makedirs(out, exist_ok=True)
    image = draw()
    image.resize((256, 256), Image.LANCZOS).save(os.path.join(out, 'bigraph.png'))
    image.save(os.path.join(out, 'bigraph.ico'),
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Wrote icons to {out}")


if __name__ == '__main__':
    main()
