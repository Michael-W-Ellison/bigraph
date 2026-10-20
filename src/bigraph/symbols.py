"""
Symbol generation for the Bigraph Cryptography System

Generates geometric line-based symbols using SVG format.
Each symbol consists of a primary line (vertical or horizontal) with
extensions at controlled positions and angles.

Design Rules:
- Primary line: vertical or horizontal
- Extensions: placed at the start, middle, or end of the primary line
- Each position can have an extension on one or both sides of the primary line
- Extensions are perpendicular (90°) or diagonal (45°), and a diagonal can
  slant toward either end of the primary line
- A diagonal at an end of the primary line that points away from the line
  is half the normal length, to keep the symbols compact
- Extensions do not cross each other; diagonal tips may touch to form
  closed triangles
- Two diagonals at the same position that would form one straight line
  crossing the primary line are not used
- A plain vertical line is not used as a symbol; it is the partial marker
  ("|") that shows only one letter of a bigram is used
"""

import math
import random
from itertools import combinations, product
from typing import List, Dict
from .constants import TOTAL_SYMBOLS

POSITIONS = ['start', 'middle', 'end']

# Perpendicular, or diagonal slanting toward the start or end of the primary line
EXTENSION_TYPES = ['perpendicular', 'toward_start', 'toward_end']

# Sides of the primary line: left/right for vertical, up/down for horizontal
SIDES = {'vertical': ['left', 'right'], 'horizontal': ['up', 'down']}


class SymbolGenerator:
    """Generates unique geometric line-based symbols"""

    def __init__(self, seed: int = None):
        """
        Initialize the symbol generator

        Args:
            seed: Random seed for reproducible symbol generation
        """
        self.seed = seed
        self.random = random.Random(seed)

        self.symbol_size = 100  # SVG viewBox size
        self.line_width = 4
        self.margin = 15

        # Diagonals from neighbouring positions on the same side meet at their
        # tips, so a diagonal covers half the spacing between positions
        spacing = (self.symbol_size - 2 * self.margin) / 2
        self.diagonal_offset = spacing / 2
        self.extension_length = self.diagonal_offset * math.sqrt(2)

    def generate_all_symbols(self, count: int = TOTAL_SYMBOLS) -> List[str]:
        """
        Generate all unique symbols needed for the system

        Args:
            count: Number of symbols to generate

        Returns:
            List of SVG strings, one for each symbol
        """
        symbol_configs = self._generate_symbol_configurations(count)
        return [self._create_svg_symbol(config) for config in symbol_configs]

    def _generate_symbol_configurations(self, count: int) -> List[Dict]:
        """
        Generate unique symbol configurations

        Symbols with fewer extensions are used first. When only part of a
        group with the same number of extensions is needed, that part is
        chosen at random using the seed.

        Each configuration:
        - Primary line orientation (vertical/horizontal)
        - Extensions: list of {position, side, type}
          * position: 'start', 'middle', or 'end'
          * side: 'left', 'right' (for vertical) or 'up', 'down' (for horizontal)
          * type: 'perpendicular', 'toward_start', or 'toward_end'

        Args:
            count: Number of unique symbols to generate

        Returns:
            List of configuration dictionaries
        """
        configs = []
        num_slots = len(POSITIONS) * 2

        for num_extensions in range(num_slots + 1):
            group = self._configurations_with_extensions(num_extensions)
            needed = count - len(configs)

            if len(group) <= needed:
                configs.extend(group)
            else:
                configs.extend(self.random.sample(group, needed))

            if len(configs) == count:
                break

        if len(configs) < count:
            raise ValueError(f"Cannot generate {count} unique symbols")

        return configs

    def _configurations_with_extensions(self, num_extensions: int) -> List[Dict]:
        """Generate every configuration with the given number of extensions"""
        configs = []

        for orientation in ['vertical', 'horizontal']:
            slots = [(position, side) for position in POSITIONS
                     for side in SIDES[orientation]]

            for chosen_slots in combinations(slots, num_extensions):
                for types in product(EXTENSION_TYPES, repeat=num_extensions):
                    extensions = [
                        {'position': position, 'side': side, 'type': ext_type}
                        for (position, side), ext_type in zip(chosen_slots, types)
                    ]
                    is_partial_marker = orientation == 'vertical' and not extensions
                    if not is_partial_marker and not self._has_crossing_diagonals(extensions):
                        configs.append({
                            'orientation': orientation,
                            'extensions': extensions
                        })

        return configs

    def _has_crossing_diagonals(self, extensions: List[Dict]) -> bool:
        """
        Check for two diagonals at the same position on opposite sides that
        slant in opposite directions, forming one line across the primary line
        """
        for position in POSITIONS:
            diagonal_types = {e['type'] for e in extensions
                              if e['position'] == position and e['type'] != 'perpendicular'}
            if diagonal_types == {'toward_start', 'toward_end'}:
                return True
        return False

    def create_partial_marker_svg(self) -> str:
        """
        Create the SVG for the partial marker ("|")

        The marker is the plain vertical primary line, drawn in a narrow
        viewBox so it takes less horizontal space than a symbol.

        Returns:
            SVG string
        """
        size = self.symbol_size
        width = 2 * self.margin
        left = (size - width) / 2
        center = size / 2

        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{left:g} 0 {width} {size}" '
                f'width="{width}" height="{size}">\n'
                f'  <line x1="{center:g}" y1="{self.margin}" x2="{center:g}" y2="{size - self.margin}" '
                f'stroke="black" stroke-width="{self.line_width}" stroke-linecap="square"/>\n'
                f'</svg>')

    def _create_svg_symbol(self, config: Dict) -> str:
        """
        Create SVG representation of a symbol from configuration

        Args:
            config: Symbol configuration dictionary

        Returns:
            SVG string
        """
        size = self.symbol_size
        start = self.margin
        end = size - self.margin

        segments = [((start, 0), (end, 0))]
        for ext in config['extensions']:
            segments.append(self._extension_segment(config['orientation'], ext))

        lines = []
        for p1, p2 in segments:
            x1, y1 = self._to_xy(config['orientation'], p1)
            x2, y2 = self._to_xy(config['orientation'], p2)
            lines.append(f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" '
                         f'stroke="black" stroke-width="{self.line_width}" '
                         f'stroke-linecap="square"/>')

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100" height="100">
{chr(10).join(['  ' + line for line in lines])}
</svg>'''

        return svg

    def _extension_segment(self, orientation: str, ext: Dict):
        """
        Get the end points of an extension

        Points are (along, across): the distance along the primary line, and
        the signed distance from it (negative for left/up).
        """
        start = self.margin
        end = self.symbol_size - self.margin
        along = {'start': start, 'middle': (start + end) / 2, 'end': end}[ext['position']]
        sign = -1 if ext['side'] == SIDES[orientation][0] else 1

        if ext['type'] == 'perpendicular':
            return (along, 0), (along, sign * self.extension_length)

        offset = self.diagonal_offset
        points_away = ((ext['position'] == 'start' and ext['type'] == 'toward_start') or
                       (ext['position'] == 'end' and ext['type'] == 'toward_end'))
        if points_away:
            offset /= 2

        direction = -1 if ext['type'] == 'toward_start' else 1
        return (along, 0), (along + direction * offset, sign * offset)

    def _to_xy(self, orientation: str, point) -> tuple:
        """Convert an (along, across) point to SVG coordinates"""
        along, across = point
        center = self.symbol_size / 2
        if orientation == 'vertical':
            x, y = center + across, along
        else:
            x, y = along, center + across
        return round(x, 2), round(y, 2)

    def save_symbol_to_file(self, svg_content: str, filename: str):
        """Save an SVG symbol to a file"""
        with open(filename, 'w') as f:
            f.write(svg_content)
