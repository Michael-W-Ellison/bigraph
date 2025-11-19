"""
Symbol generation for the Bigraph Cryptography System

Generates geometric line-based symbols using SVG format.
Each symbol consists of a primary line (vertical or horizontal) with
short extensions at controlled positions and angles.

Design Rules:
- Primary line: vertical or horizontal
- Extensions: placed at start, middle, or end of primary line
- Only ONE extension per position
- Extensions are SHORT (15 pixels)
- Extensions do NOT cross each other
- Extensions can be perpendicular (90°) or diagonal (45°)
"""

import random
from typing import List, Dict, Tuple
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
        self.line_width = 3
        self.margin = 15
        self.extension_length = 25  # Visible extensions matching spec examples (T, L, E, K)

    def generate_all_symbols(self) -> List[str]:
        """
        Generate all unique symbols needed for the system

        Returns:
            List of SVG strings, one for each symbol
        """
        symbols = []

        # Generate symbols using systematic approach
        symbol_configs = self._generate_symbol_configurations(TOTAL_SYMBOLS)

        for config in symbol_configs:
            svg = self._create_svg_symbol(config)
            symbols.append(svg)

        return symbols

    def _generate_symbol_configurations(self, count: int) -> List[Dict]:
        """
        Generate unique symbol configurations systematically

        Each configuration:
        - Primary line orientation (vertical/horizontal)
        - Extensions: list of (position, direction, angle)
          * position: 'start', 'middle', or 'end'
          * direction: 'left', 'right' (for vertical) or 'up', 'down' (for horizontal)
          * angle: 90 (perpendicular) or 45 (diagonal)

        Args:
            count: Number of unique symbols to generate

        Returns:
            List of configuration dictionaries
        """
        configs = []
        config_set = set()

        # 1. No extensions (2 configs: vertical, horizontal)
        for orientation in ['vertical', 'horizontal']:
            config = {
                'orientation': orientation,
                'extensions': []
            }
            config_hash = self._hash_config(config)
            if config_hash not in config_set:
                config_set.add(config_hash)
                configs.append(config)

        # 2. Single extension configurations
        # THREE positions, TWO angles, one or both sides (per spec)
        for orientation in ['vertical', 'horizontal']:
            for position in ['start', 'middle', 'end']:  # THREE equally spaced positions
                if orientation == 'vertical':
                    direction_options = ['left', 'right', 'both']  # Can be on both sides
                else:
                    direction_options = ['up', 'down', 'both']

                for direction in direction_options:
                    for angle in [90, 45]:  # Only perpendicular or 45° diagonal
                        if direction == 'both':
                            # Both sides means two extensions at same position
                            if orientation == 'vertical':
                                exts = [
                                    {'position': position, 'direction': 'left', 'angle': angle},
                                    {'position': position, 'direction': 'right', 'angle': angle}
                                ]
                            else:
                                exts = [
                                    {'position': position, 'direction': 'up', 'angle': angle},
                                    {'position': position, 'direction': 'down', 'angle': angle}
                                ]
                            config = {
                                'orientation': orientation,
                                'extensions': exts
                            }
                        else:
                            config = {
                                'orientation': orientation,
                                'extensions': [{
                                    'position': position,
                                    'direction': direction,
                                    'angle': angle
                                }]
                            }
                        config_hash = self._hash_config(config)
                        if config_hash not in config_set:
                            config_set.add(config_hash)
                            configs.append(config)

        # 3. Two and more extensions at different positions or with "both sides"
        for orientation in ['vertical', 'horizontal']:
            all_positions = ['start', 'middle', 'end']  # THREE positions only

            # First: pairs of different positions
            for i, pos1 in enumerate(all_positions):
                for pos2 in all_positions[i+1:]:
                    if orientation == 'vertical':
                        directions = ['left', 'right']
                    else:
                        directions = ['up', 'down']

                    for dir1 in directions:
                        for dir2 in directions:
                            for angle1 in [90, 45]:
                                for angle2 in [90, 45]:
                                    config = {
                                        'orientation': orientation,
                                        'extensions': [
                                            {'position': pos1, 'direction': dir1, 'angle': angle1},
                                            {'position': pos2, 'direction': dir2, 'angle': angle2}
                                        ]
                                    }
                                    config_hash = self._hash_config(config)
                                    if config_hash not in config_set:
                                        config_set.add(config_hash)
                                        configs.append(config)

            # Second: one position with both sides (can be different angles), plus another position
            for pos1 in all_positions:
                for pos2 in all_positions:
                    if pos1 != pos2:
                        # Can have different angles on each side
                        for angle_left in [90, 45]:
                            for angle_right in [90, 45]:
                                if orientation == 'vertical':
                                    exts_both = [
                                        {'position': pos1, 'direction': 'left', 'angle': angle_left},
                                        {'position': pos1, 'direction': 'right', 'angle': angle_right}
                                    ]
                                    dir_options = ['left', 'right']
                                else:
                                    exts_both = [
                                        {'position': pos1, 'direction': 'up', 'angle': angle_left},
                                        {'position': pos1, 'direction': 'down', 'angle': angle_right}
                                    ]
                                    dir_options = ['up', 'down']

                                for dir2 in dir_options:
                                    for angle2 in [90, 45]:
                                        config = {
                                            'orientation': orientation,
                                            'extensions': exts_both + [{'position': pos2, 'direction': dir2, 'angle': angle2}]
                                        }
                                        config_hash = self._hash_config(config)
                                        if config_hash not in config_set:
                                            config_set.add(config_hash)
                                            configs.append(config)

        # 4. Three extensions at all three positions
        for orientation in ['vertical', 'horizontal']:
            if orientation == 'vertical':
                directions = ['left', 'right']
            else:
                directions = ['up', 'down']

            for dir1 in directions:
                for dir2 in directions:
                    for dir3 in directions:
                        for angle1 in [90, 45]:
                            for angle2 in [90, 45]:
                                for angle3 in [90, 45]:
                                    config = {
                                        'orientation': orientation,
                                        'extensions': [
                                            {'position': 'start', 'direction': dir1, 'angle': angle1},
                                            {'position': 'middle', 'direction': dir2, 'angle': angle2},
                                            {'position': 'end', 'direction': dir3, 'angle': angle3}
                                        ]
                                    }
                                    config_hash = self._hash_config(config)
                                    if config_hash not in config_set:
                                        config_set.add(config_hash)
                                        configs.append(config)

        # 4.5. More complex "both sides" configurations
        for orientation in ['vertical', 'horizontal']:
            all_positions = ['start', 'middle', 'end']

            # Two positions, each with "both sides" (4 total extensions)
            for i, pos1 in enumerate(all_positions):
                for pos2 in all_positions[i+1:]:
                    for angle1_left in [90, 45]:
                        for angle1_right in [90, 45]:
                            for angle2_left in [90, 45]:
                                for angle2_right in [90, 45]:
                                    if orientation == 'vertical':
                                        exts = [
                                            {'position': pos1, 'direction': 'left', 'angle': angle1_left},
                                            {'position': pos1, 'direction': 'right', 'angle': angle1_right},
                                            {'position': pos2, 'direction': 'left', 'angle': angle2_left},
                                            {'position': pos2, 'direction': 'right', 'angle': angle2_right}
                                        ]
                                    else:
                                        exts = [
                                            {'position': pos1, 'direction': 'up', 'angle': angle1_left},
                                            {'position': pos1, 'direction': 'down', 'angle': angle1_right},
                                            {'position': pos2, 'direction': 'up', 'angle': angle2_left},
                                            {'position': pos2, 'direction': 'down', 'angle': angle2_right}
                                        ]
                                    config = {
                                        'orientation': orientation,
                                        'extensions': exts
                                    }
                                    config_hash = self._hash_config(config)
                                    if config_hash not in config_set:
                                        config_set.add(config_hash)
                                        configs.append(config)

                                    if len(configs) >= count:
                                        return configs

        # 5. If still need more, add safe random variations
        attempts = 0
        max_attempts = 50000  # Increased attempts
        while len(configs) < count and attempts < max_attempts:
            config = self._generate_safe_random_config()
            config_hash = self._hash_config(config)
            if config_hash not in config_set:
                config_set.add(config_hash)
                configs.append(config)
            attempts += 1

        # 6. If still not enough, create more complex unique variations
        safety_counter = 0
        max_safety = 10000
        while len(configs) < count and safety_counter < max_safety:
            safety_counter += 1

            # Create complex configs with 4-6 extensions
            orientation = random.choice(['vertical', 'horizontal'])
            all_positions = ['start', 'middle', 'end']

            # Randomly pick 2-3 positions
            num_positions = random.randint(2, 3)
            positions = random.sample(all_positions, num_positions)

            exts = []
            for pos in positions:
                # Decide if this position gets "both sides" or one side
                if random.random() < 0.5:  # 50% chance of "both sides"
                    if orientation == 'vertical':
                        exts.append({'position': pos, 'direction': 'left', 'angle': random.choice([90, 45])})
                        exts.append({'position': pos, 'direction': 'right', 'angle': random.choice([90, 45])})
                    else:
                        exts.append({'position': pos, 'direction': 'up', 'angle': random.choice([90, 45])})
                        exts.append({'position': pos, 'direction': 'down', 'angle': random.choice([90, 45])})
                else:  # One side only
                    if orientation == 'vertical':
                        exts.append({'position': pos, 'direction': random.choice(['left', 'right']), 'angle': random.choice([90, 45])})
                    else:
                        exts.append({'position': pos, 'direction': random.choice(['up', 'down']), 'angle': random.choice([90, 45])})

            config = {
                'orientation': orientation,
                'extensions': exts
            }
            config_hash = self._hash_config(config)
            if config_hash not in config_set:
                config_set.add(config_hash)
                configs.append(config)

        return configs

    def _would_cross(self, orientation: str, pos1: str, dir1: str, angle1: int,
                     pos2: str, dir2: str, angle2: int) -> bool:
        """
        Check if two extensions would cross each other

        For simplicity, we'll be conservative:
        - Diagonal extensions from different positions going toward each other: potential cross
        - Extensions at start and end going diagonally toward middle: potential cross
        """
        # If both are perpendicular (90°), they won't cross
        if angle1 == 90 and angle2 == 90:
            return False

        # If they're on opposite sides, they won't cross
        if orientation == 'vertical':
            if (dir1 == 'left' and dir2 == 'right') or (dir1 == 'right' and dir2 == 'left'):
                return False
        else:
            if (dir1 == 'up' and dir2 == 'down') or (dir1 == 'down' and dir2 == 'up'):
                return False

        # Diagonal extensions from adjacent positions going same direction might cross
        if angle1 == 45 and angle2 == 45:
            if dir1 == dir2:
                # Same side, same angle - might get too close but won't cross
                return False
            else:
                # Different sides, diagonal - could cross
                return True

        # Conservative: if one diagonal, one perpendicular, same side
        if dir1 == dir2 and (angle1 == 45 or angle2 == 45):
            return False

        return False  # Default to allowing

    def _generate_safe_random_config(self) -> Dict:
        """Generate a random configuration per spec"""
        orientation = random.choice(['vertical', 'horizontal'])
        num_extensions = random.randint(0, 3)

        if num_extensions == 0:
            return {'orientation': orientation, 'extensions': []}

        if orientation == 'vertical':
            directions = ['left', 'right']
        else:
            directions = ['up', 'down']

        # THREE positions only
        all_positions = ['start', 'middle', 'end']
        positions = random.sample(all_positions, min(num_extensions, len(all_positions)))

        extensions = []
        for pos in positions:
            direction = random.choice(directions)
            angle = random.choice([90, 45])  # Only 90° or 45°
            extensions.append({
                'position': pos,
                'direction': direction,
                'angle': angle
            })

        return {'orientation': orientation, 'extensions': extensions}

    def _hash_config(self, config: Dict) -> str:
        """Create a hashable string from configuration"""
        ext_str = '_'.join([
            f"{e['position']}{e['direction']}{e['angle']}"
            for e in sorted(config['extensions'], key=lambda x: x['position'])
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
                ext_line = self._create_vertical_extension(x, y1, y2, ext)
                if ext_line:
                    lines.append(ext_line)
        else:
            # Horizontal line in the center
            y = size / 2
            x1 = margin
            x2 = size - margin
            lines.append(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
                        f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>')

            # Add extensions
            for ext in config['extensions']:
                ext_line = self._create_horizontal_extension(y, x1, x2, ext)
                if ext_line:
                    lines.append(ext_line)

        # Combine into SVG
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100" height="100">
{chr(10).join(['  ' + line for line in lines])}
</svg>'''

        return svg

    def _create_vertical_extension(self, x: float, y1: float, y2: float, ext: Dict) -> str:
        """Create extension line for a vertical primary line"""
        line_width = self.line_width
        ext_length = self.extension_length

        # Determine y position on primary line (THREE positions only)
        if ext['position'] == 'start':
            y = y1
        elif ext['position'] == 'middle':
            y = (y1 + y2) / 2
        else:  # end
            y = y2

        direction = ext['direction']
        angle = ext['angle']

        # Calculate end point based on direction and angle
        if direction == 'left':
            if angle == 90:  # Perpendicular left
                x2 = x - ext_length
                y2 = y
            else:  # 45° diagonal
                x2 = x - ext_length
                # True 45° angle means equal horizontal and vertical distance
                if ext['position'] == 'start':
                    y2 = y - ext_length  # Up-left diagonal
                elif ext['position'] == 'end':
                    y2 = y + ext_length  # Down-left diagonal
                else:  # middle - go up
                    y2 = y - ext_length  # Up-left diagonal
        else:  # right
            if angle == 90:  # Perpendicular right
                x2 = x + ext_length
                y2 = y
            else:  # 45° diagonal
                x2 = x + ext_length
                # True 45° angle means equal horizontal and vertical distance
                if ext['position'] == 'start':
                    y2 = y - ext_length  # Up-right diagonal
                elif ext['position'] == 'end':
                    y2 = y + ext_length  # Down-right diagonal
                else:  # middle - go up
                    y2 = y - ext_length  # Up-right diagonal

        return f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" ' \
               f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>'

    def _create_horizontal_extension(self, y: float, x1: float, x2: float, ext: Dict) -> str:
        """Create extension line for a horizontal primary line"""
        line_width = self.line_width
        ext_length = self.extension_length

        # Determine x position on primary line (THREE positions only)
        if ext['position'] == 'start':
            x = x1
        elif ext['position'] == 'middle':
            x = (x1 + x2) / 2
        else:  # end
            x = x2

        direction = ext['direction']
        angle = ext['angle']

        # Calculate end point based on direction and angle
        if direction == 'up':
            if angle == 90:  # Perpendicular up
                x2 = x
                y2 = y - ext_length
            else:  # 45° diagonal
                y2 = y - ext_length
                # True 45° angle means equal horizontal and vertical distance
                if ext['position'] == 'start':
                    x2 = x + ext_length  # Up-right diagonal
                elif ext['position'] == 'end':
                    x2 = x - ext_length  # Up-left diagonal
                else:  # middle - go right
                    x2 = x + ext_length  # Up-right diagonal
        else:  # down
            if angle == 90:  # Perpendicular down
                x2 = x
                y2 = y + ext_length
            else:  # 45° diagonal
                y2 = y + ext_length
                # True 45° angle means equal horizontal and vertical distance
                if ext['position'] == 'start':
                    x2 = x + ext_length  # Down-right diagonal
                elif ext['position'] == 'end':
                    x2 = x - ext_length  # Down-left diagonal
                else:  # middle - go right
                    x2 = x + ext_length  # Down-right diagonal

        return f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" ' \
               f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>'

    def save_symbol_to_file(self, svg_content: str, filename: str):
        """Save an SVG symbol to a file"""
        with open(filename, 'w') as f:
            f.write(svg_content)
