"""
Key Management for Bigraph Cryptography System

Handles generation, storage, and management of encryption keys.
Each key maps symbols to bigrams/characters randomly.
"""

import json
import random
import os
from typing import Dict, List, Optional
from datetime import datetime
from .constants import (BIGRAMS, SPACE_MARKERS, SPECIAL_CHARS, DIGITS,
                       MULTIPLY_DIVIDE_MARKER, TOTAL_SYMBOLS)
from .symbols import SymbolGenerator


class KeyManager:
    """Manages encryption keys for the bigraph system"""

    def __init__(self, keys_directory: str = "keys"):
        """
        Initialize the key manager

        Args:
            keys_directory: Directory to store key files
        """
        self.keys_directory = keys_directory
        os.makedirs(keys_directory, exist_ok=True)

    def generate_key(self, recipient_name: str, seed: int = None) -> Dict:
        """
        Generate a new random key for a recipient

        The key maps symbol indices to their meanings (bigrams, numbers, etc.)

        Args:
            recipient_name: Name/identifier for the recipient
            seed: Optional random seed for reproducible keys

        Returns:
            Dictionary containing the key mapping and metadata
        """
        if seed is None:
            seed = random.randint(0, 2**32 - 1)

        random.seed(seed)

        # Create list of all items that need symbols
        items = []

        # Add all bigrams
        items.extend(BIGRAMS)

        # Add digits (positive indices for multiplication)
        items.extend([f"NUM_{d}" for d in DIGITS])

        # Add negative digits (for division)
        items.extend([f"NUM_NEG_{d}" for d in DIGITS])

        # Add multiply/divide indicator
        items.append(MULTIPLY_DIVIDE_MARKER)

        # Add special characters
        items.extend([f"SPECIAL_{char}" for char in SPECIAL_CHARS])

        # Add space markers
        items.extend([f"SPACE_{marker}" for marker in SPACE_MARKERS])

        # Shuffle to create random mapping
        shuffled_items = items.copy()
        random.shuffle(shuffled_items)

        # Create mapping: symbol_index -> meaning
        symbol_to_meaning = {i: shuffled_items[i] for i in range(len(shuffled_items))}

        # Create reverse mapping: meaning -> symbol_index
        meaning_to_symbol = {v: k for k, v in symbol_to_meaning.items()}

        # Generate the actual SVG symbols
        symbol_gen = SymbolGenerator(seed=seed)
        symbols_svg = symbol_gen.generate_all_symbols()

        # Create key object
        key = {
            'recipient': recipient_name,
            'created': datetime.now().isoformat(),
            'seed': seed,
            'symbol_to_meaning': symbol_to_meaning,
            'meaning_to_symbol': meaning_to_symbol,
            'symbols_svg': symbols_svg[:len(shuffled_items)],  # Only include needed symbols
            'version': '1.0'
        }

        return key

    def save_key(self, key: Dict) -> str:
        """
        Save a key to a JSON file

        Args:
            key: Key dictionary to save

        Returns:
            Path to the saved key file
        """
        recipient = key['recipient'].replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{recipient}_{timestamp}.key"
        filepath = os.path.join(self.keys_directory, filename)

        with open(filepath, 'w') as f:
            json.dump(key, f, indent=2)

        return filepath

    def load_key(self, filepath: str) -> Dict:
        """
        Load a key from a JSON file

        Args:
            filepath: Path to the key file

        Returns:
            Key dictionary
        """
        with open(filepath, 'r') as f:
            key = json.load(f)

        # Convert string keys back to integers for symbol_to_meaning
        if 'symbol_to_meaning' in key:
            key['symbol_to_meaning'] = {
                int(k): v for k, v in key['symbol_to_meaning'].items()
            }

        return key

    def list_keys(self) -> List[Dict]:
        """
        List all available keys

        Returns:
            List of key metadata dictionaries
        """
        keys = []

        for filename in os.listdir(self.keys_directory):
            if filename.endswith('.key'):
                filepath = os.path.join(self.keys_directory, filename)
                try:
                    key = self.load_key(filepath)
                    keys.append({
                        'filename': filename,
                        'filepath': filepath,
                        'recipient': key.get('recipient', 'Unknown'),
                        'created': key.get('created', 'Unknown'),
                        'version': key.get('version', '1.0')
                    })
                except Exception as e:
                    print(f"Error loading key {filename}: {e}")

        return keys

    def export_key(self, key: Dict, filepath: str):
        """
        Export a key to a specific file location

        Args:
            key: Key dictionary to export
            filepath: Destination file path
        """
        with open(filepath, 'w') as f:
            json.dump(key, f, indent=2)

    def import_key(self, filepath: str) -> Dict:
        """
        Import a key from a file

        Args:
            filepath: Path to the key file to import

        Returns:
            Imported key dictionary
        """
        return self.load_key(filepath)

    def get_symbol_for_bigram(self, key: Dict, bigram: str) -> Optional[int]:
        """
        Get the symbol index for a bigram

        Args:
            key: Key dictionary
            bigram: Two-letter bigram

        Returns:
            Symbol index or None if not found
        """
        return key['meaning_to_symbol'].get(bigram)

    def get_symbol_for_number(self, key: Dict, number: int) -> Optional[int]:
        """
        Get the symbol index for a number

        Args:
            key: Key dictionary
            number: Digit (0-9) or negative digit for division

        Returns:
            Symbol index or None if not found
        """
        if number >= 0:
            meaning = f"NUM_{number}"
        else:
            meaning = f"NUM_NEG_{abs(number)}"

        return key['meaning_to_symbol'].get(meaning)

    def get_symbol_for_special(self, key: Dict, char: str) -> Optional[int]:
        """
        Get the symbol index for a special character

        Args:
            key: Key dictionary
            char: Special character

        Returns:
            Symbol index or None if not found
        """
        meaning = f"SPECIAL_{char}"
        return key['meaning_to_symbol'].get(meaning)

    def get_symbol_for_space_marker(self, key: Dict, marker: str) -> Optional[int]:
        """
        Get the symbol index for a space marker

        Args:
            key: Key dictionary
            marker: Space marker bigram (e.g., 'JQ')

        Returns:
            Symbol index or None if not found
        """
        meaning = f"SPACE_{marker}"
        return key['meaning_to_symbol'].get(meaning)

    def get_muldiv_symbol(self, key: Dict) -> Optional[int]:
        """
        Get the symbol index for the multiply/divide indicator

        Args:
            key: Key dictionary

        Returns:
            Symbol index or None if not found
        """
        return key['meaning_to_symbol'].get(MULTIPLY_DIVIDE_MARKER)

    def get_meaning_from_symbol(self, key: Dict, symbol_index: int) -> Optional[str]:
        """
        Get the meaning (bigram/character) from a symbol index

        Args:
            key: Key dictionary
            symbol_index: Index of the symbol

        Returns:
            Meaning string or None if not found
        """
        return key['symbol_to_meaning'].get(symbol_index)

    def get_svg_for_symbol(self, key: Dict, symbol_index: int) -> Optional[str]:
        """
        Get the SVG representation for a symbol

        Args:
            key: Key dictionary
            symbol_index: Index of the symbol

        Returns:
            SVG string or None if not found
        """
        if symbol_index < len(key['symbols_svg']):
            return key['symbols_svg'][symbol_index]
        return None
