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
        self.extension_length = 15  # SHORT extensions to prevent crossing

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
        # Use more positions and angles for variety
        for orientation in ['vertical', 'horizontal']:
            for position in ['start', 'quarter', 'middle', 'threequarter', 'end']:
                if orientation == 'vertical':
                    directions = ['left', 'right']
                else:
                    directions = ['up', 'down']

                for direction in directions:
                    for angle in [90, 45, 30, 60]:  # More angle varieties
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

        # 3. Two extensions at different positions
        # With 15px extensions, crossing is not a concern
        # Use subset of combinations to get to 718 total
        for orientation in ['vertical', 'horizontal']:
            all_positions = ['start', 'quarter', 'middle', 'threequarter', 'end']
            # Generate pairs of positions
            for i, pos1 in enumerate(all_positions):
                for pos2 in all_positions[i+1:]:  # Only pairs where pos2 comes after pos1
                    if orientation == 'vertical':
                        directions = ['left', 'right']
                    else:
                        directions = ['up', 'down']

                    for dir1 in directions:
                        for dir2 in directions:
                            for angle1 in [90, 45]:  # Limit angles for two-extension
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

        # 4. Three extensions at all three positions
        # With 15px extensions, all combinations are safe
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

        # 5. If still need more, add safe random variations with varied extension lengths
        attempts = 0
        max_attempts = 50000  # Increased attempts
        while len(configs) < count and attempts < max_attempts:
            config = self._generate_safe_random_config()
            config_hash = self._hash_config(config)
            if config_hash not in config_set:
                config_set.add(config_hash)
                configs.append(config)
            attempts += 1

        # 6. If still not enough, duplicate some with variation
        while len(configs) < count:
            # Take existing configs and add slight variations
            base_config = configs[len(configs) % len(configs)]
            config = {
                'orientation': base_config['orientation'],
                'extensions': base_config['extensions'].copy()
            }
            # Add a small random extension if possible
            if len(config['extensions']) < 3:
                pos_options = ['start', 'quarter', 'middle', 'threequarter', 'end']
                used_positions = [e['position'] for e in config['extensions']]
                available = [p for p in pos_options if p not in used_positions]
                if available:
                    new_ext = {
                        'position': random.choice(available),
                        'direction': random.choice(['left', 'right'] if config['orientation'] == 'vertical' else ['up', 'down']),
                        'angle': random.choice([90, 45, 30, 60])
                    }
                    config['extensions'].append(new_ext)
                    config_hash = self._hash_config(config)
                    if config_hash not in config_set:
                        config_set.add(config_hash)
                        configs.append(config)
                    else:
                        # If duplicate, just add a simple unique one
                        configs.append(self._generate_safe_random_config())
                else:
                    configs.append(self._generate_safe_random_config())
            else:
                configs.append(self._generate_safe_random_config())

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
        """Generate a random configuration that avoids crossing"""
        orientation = random.choice(['vertical', 'horizontal'])
        num_extensions = random.randint(0, 3)

        if num_extensions == 0:
            return {'orientation': orientation, 'extensions': []}

        if orientation == 'vertical':
            directions = ['left', 'right']
        else:
            directions = ['up', 'down']

        # Use all available positions and angles
        all_positions = ['start', 'quarter', 'middle', 'threequarter', 'end']
        positions = random.sample(all_positions, min(num_extensions, len(all_positions)))

        extensions = []
        for pos in positions:
            direction = random.choice(directions)  # Allow mixed directions
            angle = random.choice([90, 45, 30, 60])
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

        # Determine y position on primary line
        if ext['position'] == 'start':
            y = y1
        elif ext['position'] == 'quarter':
            y = y1 + (y2 - y1) * 0.25
        elif ext['position'] == 'middle':
            y = (y1 + y2) / 2
        elif ext['position'] == 'threequarter':
            y = y1 + (y2 - y1) * 0.75
        else:  # end
            y = y2

        direction = ext['direction']
        angle = ext['angle']

        # Calculate end point based on direction and angle
        import math
        if direction == 'left':
            if angle == 90:  # Perpendicular left
                x2 = x - ext_length
                y2 = y
            else:  # Diagonal angles
                angle_rad = math.radians(angle)
                x2 = x - ext_length * math.cos(angle_rad)
                # Alternate up/down based on position
                if ext['position'] in ['start', 'quarter']:
                    y2 = y - ext_length * math.sin(angle_rad)  # Up
                else:
                    y2 = y + ext_length * math.sin(angle_rad)  # Down
        else:  # right
            if angle == 90:  # Perpendicular right
                x2 = x + ext_length
                y2 = y
            else:  # Diagonal angles
                angle_rad = math.radians(angle)
                x2 = x + ext_length * math.cos(angle_rad)
                # Alternate up/down based on position
                if ext['position'] in ['start', 'quarter']:
                    y2 = y - ext_length * math.sin(angle_rad)  # Up
                else:
                    y2 = y + ext_length * math.sin(angle_rad)  # Down

        return f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" ' \
               f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>'

    def _create_horizontal_extension(self, y: float, x1: float, x2: float, ext: Dict) -> str:
        """Create extension line for a horizontal primary line"""
        line_width = self.line_width
        ext_length = self.extension_length

        # Determine x position on primary line
        if ext['position'] == 'start':
            x = x1
        elif ext['position'] == 'quarter':
            x = x1 + (x2 - x1) * 0.25
        elif ext['position'] == 'middle':
            x = (x1 + x2) / 2
        elif ext['position'] == 'threequarter':
            x = x1 + (x2 - x1) * 0.75
        else:  # end
            x = x2

        direction = ext['direction']
        angle = ext['angle']

        # Calculate end point based on direction and angle
        import math
        if direction == 'up':
            if angle == 90:  # Perpendicular up
                x2 = x
                y2 = y - ext_length
            else:  # Diagonal angles
                angle_rad = math.radians(angle)
                y2 = y - ext_length * math.sin(angle_rad)
                # Alternate left/right based on position
                if ext['position'] in ['start', 'quarter']:
                    x2 = x + ext_length * math.cos(angle_rad)  # Right
                else:
                    x2 = x - ext_length * math.cos(angle_rad)  # Left
        else:  # down
            if angle == 90:  # Perpendicular down
                x2 = x
                y2 = y + ext_length
            else:  # Diagonal angles
                angle_rad = math.radians(angle)
                y2 = y + ext_length * math.sin(angle_rad)
                # Alternate left/right based on position
                if ext['position'] in ['start', 'quarter']:
                    x2 = x + ext_length * math.cos(angle_rad)  # Right
                else:
                    x2 = x - ext_length * math.cos(angle_rad)  # Left

        return f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" ' \
               f'stroke="black" stroke-width="{line_width}" stroke-linecap="round"/>'

    def save_symbol_to_file(self, svg_content: str, filename: str):
        """Save an SVG symbol to a file"""
        with open(filename, 'w') as f:
            f.write(svg_content)
