"""
Symbol generation for the Bigraph Cryptography System

Generates geometric line-based symbols using SVG format.
Each symbol consists of a primary line (vertical or horizontal) with
intersecting lines at controlled angles.
"""

import random
from typing import List, Tuple, Dict
from .constants import TOTAL_SYMBOLS


class SymbolGenerator:
    """Generates unique geometric line-based symbols"""

    def __init__(self, seed: int = None):
        """
        Initialize the symbol generator

        Args:
            seed: Random seed for reproducible symbol generation
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)

        self.symbol_size = 100  # SVG viewBox size
        self.line_width = 4
        self.margin = 10

    def generate_all_symbols(self) -> List[str]:
        """
        Generate all unique symbols needed for the system

        Returns:
            List of SVG strings, one for each symbol
        """
        symbols = []

        # Generate symbols using systematic approach
        # We need to generate enough unique combinations
        symbol_configs = self._generate_symbol_configurations(TOTAL_SYMBOLS)

        for config in symbol_configs:
            svg = self._create_svg_symbol(config)
            symbols.append(svg)

        return symbols

    def _generate_symbol_configurations(self, count: int) -> List[Dict]:
        """
        Generate unique symbol configurations

        Each configuration defines:
        - Primary line orientation (vertical/horizontal)
        - Extension positions (top, middle, bottom for vertical; left, middle, right for horizontal)
        - Extension angles (90° perpendicular or 45° diagonal)
        - Extension sides (left, right, both for vertical; up, down, both for horizontal)

        Args:
            count: Number of unique symbols to generate

        Returns:
            List of configuration dictionaries
        """
        configs = []
        config_set = set()  # To track unique configs

        # Systematic generation to ensure uniqueness
        orientations = ['vertical', 'horizontal']
        positions = ['start', 'middle', 'end']
        angles = [90, 45]  # perpendicular or diagonal
        sides = ['left', 'right', 'both', 'left_only', 'right_only']

        # Generate all combinations
        for orientation in orientations:
            for num_extensions in range(0, 4):  # 0-3 extensions
                for ext_combo in self._get_extension_combinations(num_extensions):
                    if len(configs) >= count:
                        return configs

                    config = {
                        'orientation': orientation,
                        'extensions': ext_combo
                    }

                    # Convert config to hashable form for uniqueness check
                    config_hash = self._hash_config(config)
                    if config_hash not in config_set:
                        config_set.add(config_hash)
                        configs.append(config)

        # If we need more symbols, add random variations
        while len(configs) < count:
            config = self._generate_random_config()
            config_hash = self._hash_config(config)
            if config_hash not in config_set:
                config_set.add(config_hash)
                configs.append(config)

        return configs[:count]

    def _get_extension_combinations(self, num_extensions: int) -> List[List[Dict]]:
        """Generate combinations of extensions"""
        if num_extensions == 0:
            return [[]]

        positions = ['start', 'middle', 'end']
        angles = [90, 45, -45]
        sides = ['left', 'right', 'both']

        combinations = []

        # Generate various extension patterns
        if num_extensions == 1:
            for pos in positions:
                for angle in angles:
                    for side in sides:
                        combinations.append([{
                            'position': pos,
                            'angle': angle,
                            'side': side
                        }])
        elif num_extensions == 2:
            for pos1 in positions:
                for pos2 in positions:
                    if pos1 != pos2:
                        for angle in angles:
                            for side in sides:
                                combinations.append([
                                    {'position': pos1, 'angle': angle, 'side': side},
                                    {'position': pos2, 'angle': angle, 'side': 'left' if side == 'right' else 'right'}
                                ])
                                if len(combinations) >= 50:  # Limit combinations
                                    return combinations
        elif num_extensions == 3:
            for angle in angles:
                for side in sides:
                    combinations.append([
                        {'position': 'start', 'angle': angle, 'side': side},
                        {'position': 'middle', 'angle': angle, 'side': side},
                        {'position': 'end', 'angle': angle, 'side': side}
                    ])

        return combinations

    def _generate_random_config(self) -> Dict:
        """Generate a random symbol configuration"""
        orientation = random.choice(['vertical', 'horizontal'])
        num_extensions = random.randint(0, 3)

        extensions = []
        for _ in range(num_extensions):
            ext = {
                'position': random.choice(['start', 'middle', 'end']),
                'angle': random.choice([90, 45, -45]),
                'side': random.choice(['left', 'right', 'both'])
            }
            extensions.append(ext)

        return {
            'orientation': orientation,
            'extensions': extensions
        }

    def _hash_config(self, config: Dict) -> str:
        """Create a hashable string from configuration"""
        ext_str = '_'.join([
            f"{e['position']}{e['angle']}{e['side']}"
            for e in config['extensions']
        ])
        return f"{config['orientation']}_{ext_str}"

    def _create_svg_symbol(self, config: Dict) -> str:
        """
        Create SVG representation of a symbol from configuration

        Args:
            config: Symbol configuration dictionary

        Returns:
            SVG string
        """
        size = self.symbol_size
        margin = self.margin
        line_width = self.line_width

        lines = []

        # Create primary line
        if config['orientation'] == 'vertical':
            # Vertical line in the center
            x = size / 2
            y1 = margin
            y2 = size - margin
            lines.append(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
                        f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

            # Add extensions
            for ext in config['extensions']:
                ext_lines = self._create_vertical_extension(x, y1, y2, ext, margin)
                lines.extend(ext_lines)
        else:
            # Horizontal line in the center
            y = size / 2
            x1 = margin
            x2 = size - margin
            lines.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
                        f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

            # Add extensions
            for ext in config['extensions']:
                ext_lines = self._create_horizontal_extension(y, x1, x2, ext, margin)
                lines.extend(ext_lines)

        # Combine into SVG
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100" height="100">
{chr(10).join(['  ' + line for line in lines])}
</svg>'''

        return svg

    def _create_vertical_extension(self, x: float, y1: float, y2: float,
                                   ext: Dict, margin: float) -> List[str]:
        """Create extension lines for a vertical primary line"""
        lines = []
        line_width = self.line_width

        # Determine y position on primary line
        if ext['position'] == 'start':
            y = y1
        elif ext['position'] == 'middle':
            y = (y1 + y2) / 2
        else:  # end
            y = y2

        # Extension length
        ext_length = 30

        # Create extension based on angle and side
        angle = ext['angle']
        side = ext['side']

        if side in ['left', 'both']:
            if angle == 90:  # Perpendicular left
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x - ext_length}" y2="{y}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == 45:  # 45° up-left
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x - ext_length}" y2="{y - ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == -45:  # 45° down-left
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x - ext_length}" y2="{y + ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

        if side in ['right', 'both']:
            if angle == 90:  # Perpendicular right
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x + ext_length}" y2="{y}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == 45:  # 45° up-right
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x + ext_length}" y2="{y - ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == -45:  # 45° down-right
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x + ext_length}" y2="{y + ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

        return lines

    def _create_horizontal_extension(self, y: float, x1: float, x2: float,
                                     ext: Dict, margin: float) -> List[str]:
        """Create extension lines for a horizontal primary line"""
        lines = []
        line_width = self.line_width

        # Determine x position on primary line
        if ext['position'] == 'start':
            x = x1
        elif ext['position'] == 'middle':
            x = (x1 + x2) / 2
        else:  # end
            x = x2

        # Extension length
        ext_length = 30

        # Create extension based on angle and side
        angle = ext['angle']
        side = ext['side']

        # For horizontal, 'left' means up, 'right' means down
        if side in ['left', 'both']:  # up
            if angle == 90:  # Perpendicular up
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y - ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == 45:  # 45° up-left
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x - ext_length}" y2="{y - ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == -45:  # 45° up-right
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x + ext_length}" y2="{y - ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

        if side in ['right', 'both']:  # down
            if angle == 90:  # Perpendicular down
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == 45:  # 45° down-left
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x - ext_length}" y2="{y + ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')
            elif angle == -45:  # 45° down-right
                lines.append(f'<line x1="{x}" y1="{y}" x2="{x + ext_length}" y2="{y + ext_length}" '
                           f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

        return lines

    def save_symbol_to_file(self, svg_content: str, filename: str):
        """Save an SVG symbol to a file"""
        with open(filename, 'w') as f:
            f.write(svg_content)
