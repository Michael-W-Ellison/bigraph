"""
Key Management for Bigraph Cryptography System

Handles generation, storage, and management of encryption keys.
Each key maps symbols to bigrams/characters randomly.

Key files are encrypted with a password and stored so only the current user
can read them (see security.py).
"""

import json
import random
import secrets
import os
from typing import Dict, List, Optional
from datetime import datetime
from .constants import (BIGRAMS, SPACE_MARKERS, SPECIAL_CHARS, MATH_OPERATORS,
                       DIGITS, MULTIPLY_DIVIDE_MARKER, WORD_SYMBOL_BUDGET,
                       word_symbol_counts, BIGRAM_SYMBOL_BUDGET,
                       bigram_symbol_counts)
from .symbols import SymbolGenerator
from .security import (default_keys_directory, ensure_private_directory, write_private_file,
                       encrypt_key_file, decrypt_key_file, read_key_file_header, KeyFileError)

# Key data that is rebuilt when a key is loaded, so it is not stored in key files
DERIVED_FIELDS = ('meaning_to_symbol', 'symbols_svg')


class KeyManager:
    """Manages encryption keys for the bigraph system"""

    def __init__(self, keys_directory: Optional[str] = None):
        """
        Initialize the key manager

        Args:
            keys_directory: Directory to store key files (default: a per-user
                data folder). It is created, readable only by the current
                user, when the first key is saved.
        """
        self.keys_directory = keys_directory or default_keys_directory()

    def generate_key(self, recipient_name: str, seed: int = None,
                     word_symbol_budget: int = WORD_SYMBOL_BUDGET,
                     bigram_symbol_budget: int = BIGRAM_SYMBOL_BUDGET) -> Dict:
        """
        Generate a new random key for a recipient

        The key maps symbol indices to their meanings (bigrams, numbers, etc.)

        Without a seed, the mapping is shuffled with the operating system's
        secure random source, and the symbol drawings are chosen with a
        128-bit seed from the same source.

        Args:
            recipient_name: Name/identifier for the recipient
            seed: Optional random seed for reproducible keys. Seeded keys can
                be recreated by anyone who knows or guesses the seed, so use
                them only for testing and examples.
            word_symbol_budget: Number of symbols shared among the common
                words (0 for none)
            bigram_symbol_budget: Number of extra symbols shared among the
                common bigrams (0 for none)

        Returns:
            Dictionary containing the key mapping and metadata
        """
        if seed is None:
            rng = secrets.SystemRandom()
            symbol_seed = secrets.randbits(128)
            mac_key = secrets.token_hex(32)
        else:
            rng = random.Random(seed)
            symbol_seed = seed
            mac_key = '%064x' % rng.getrandbits(256)

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

        # Add mathematical operators (stored as special characters)
        items.extend([f"SPECIAL_{op}" for op in MATH_OPERATORS])

        # Add space markers
        items.extend([f"SPACE_{marker}" for marker in SPACE_MARKERS])

        # Add several symbols for each common word
        for word, count in word_symbol_counts(word_symbol_budget).items():
            items.extend([f"WORD_{word}_{i}" for i in range(count)])

        # Add extra symbols for common bigrams
        for bigram, count in bigram_symbol_counts(bigram_symbol_budget).items():
            items.extend([f"ALT_{bigram}_{i}" for i in range(count)])

        # Shuffle to create random mapping
        shuffled_items = items.copy()
        rng.shuffle(shuffled_items)

        # Create mapping: symbol_index -> meaning
        symbol_to_meaning = {i: shuffled_items[i] for i in range(len(shuffled_items))}

        # Create reverse mapping: meaning -> symbol_index
        meaning_to_symbol = {v: k for k, v in symbol_to_meaning.items()}

        # Generate the actual SVG symbols
        symbol_gen = SymbolGenerator(seed=symbol_seed)
        symbols_svg = symbol_gen.generate_all_symbols(len(shuffled_items))

        # Create key object
        key = {
            'recipient': recipient_name,
            'created': datetime.now().isoformat(),
            'seed': seed,
            'symbol_seed': symbol_seed,
            'symbol_to_meaning': symbol_to_meaning,
            'meaning_to_symbol': meaning_to_symbol,
            'symbols_svg': symbols_svg,
            # Secret for message check codes
            'mac_key': mac_key,
            'version': '2.0'
        }

        return key

    def _key_data(self, key: Dict) -> Dict:
        """Key data to store: without rebuilt fields or load-time notes"""
        return {k: v for k, v in key.items() if k not in DERIVED_FIELDS and not k.startswith('_')}

    def save_key(self, key: Dict, password: str) -> str:
        """
        Save a key to an encrypted file in the keys directory

        The file gets a random name, so it does not reveal the recipient.

        Args:
            key: Key dictionary to save
            password: Password protecting the file (at least 8 characters)

        Returns:
            Path to the saved key file
        """
        ensure_private_directory(self.keys_directory)
        while True:
            filepath = os.path.join(self.keys_directory, f"key_{secrets.token_hex(8)}.key")
            if not os.path.exists(filepath):
                break
        self.export_key(key, filepath, password)
        return filepath

    def load_key(self, filepath: str, password: Optional[str] = None) -> Dict:
        """
        Load a key from a file

        Reads encrypted key files, and older unencrypted ones (marked with
        '_stored_unencrypted', which key_warnings reports).

        Args:
            filepath: Path to the key file
            password: Password for an encrypted key file

        Returns:
            Key dictionary

        Raises:
            PasswordRequiredError: the file is encrypted and no password was given
            WrongPasswordError: the password is wrong or the file was changed
        """
        with open(filepath, 'r') as f:
            text = f.read()

        if read_key_file_header(text) is not None:
            key = decrypt_key_file(text, password)
        else:
            key = json.loads(text)
            key['_stored_unencrypted'] = True

        # Convert string keys back to integers for symbol_to_meaning
        key['symbol_to_meaning'] = {int(k): v for k, v in key['symbol_to_meaning'].items()}
        key['meaning_to_symbol'] = {v: k for k, v in key['symbol_to_meaning'].items()}

        # Redraw the symbols with the current symbol generator, so a key saved
        # by an older version does not use that version's symbols. Keys saved
        # before symbol_seed was added use their seed.
        symbol_seed = key.get('symbol_seed', key.get('seed'))
        if symbol_seed is not None:
            symbol_gen = SymbolGenerator(seed=symbol_seed)
            key['symbols_svg'] = symbol_gen.generate_all_symbols(len(key['symbol_to_meaning']))

        return key

    def list_keys(self) -> List[Dict]:
        """
        List all available keys without opening them

        Encrypted key files only reveal their creation date, so 'recipient' is
        None for them until the key is loaded with its password.

        Returns:
            List of key metadata dictionaries
        """
        keys = []
        if not os.path.isdir(self.keys_directory):
            return keys

        for filename in sorted(os.listdir(self.keys_directory)):
            if not filename.endswith('.key'):
                continue
            filepath = os.path.join(self.keys_directory, filename)
            try:
                with open(filepath, 'r') as f:
                    text = f.read()
                header = read_key_file_header(text)
                if header is not None:
                    info = {'recipient': None, 'created': header.get('created', 'Unknown'),
                            'encrypted': True}
                else:
                    data = json.loads(text)
                    info = {'recipient': data.get('recipient', 'Unknown'),
                            'created': data.get('created', 'Unknown'), 'encrypted': False}
            except (OSError, ValueError, KeyFileError) as e:
                print(f"Error reading key {filename}: {e}")
                continue
            keys.append({'filename': filename, 'filepath': filepath, **info})

        return keys

    def export_key(self, key: Dict, filepath: str, password: str):
        """
        Write a key to an encrypted file at a chosen location

        Args:
            key: Key dictionary to export
            filepath: Destination file path
            password: Password protecting the file (at least 8 characters)
        """
        created = str(key.get('created', ''))[:10]
        text = encrypt_key_file(self._key_data(key), password, created)
        write_private_file(filepath, text)

    def import_key(self, filepath: str, password: Optional[str] = None) -> Dict:
        """
        Import a key from a file

        Args:
            filepath: Path to the key file to import
            password: Password for an encrypted key file

        Returns:
            Imported key dictionary
        """
        return self.load_key(filepath, password)

    @staticmethod
    def key_warnings(key: Dict) -> List[str]:
        """
        Reasons a key is weak or stored unsafely

        Returns:
            List of warnings (empty if none)
        """
        warnings = []
        if 'symbol_seed' not in key:
            warnings.append("This key was made before secure key generation, from a 32-bit seed. "
                            "Someone with this program can find it by trying every seed. "
                            "Replace it with a new key.")
        elif key.get('seed') is not None:
            warnings.append("This key was made from a seed. Anyone who knows or guesses the seed "
                            "can recreate it. Use keys made without a seed for real messages.")
        if key.get('_stored_unencrypted'):
            warnings.append("This key file is not protected by a password. Anyone who can read the "
                            "file can read your messages. Import it again to protect it.")
        if not key.get('mac_key'):
            warnings.append("This key has no check secret, so changed messages cannot be detected.")
        return warnings

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
        Get the symbol index for a special character or math operator

        Args:
            key: Key dictionary
            char: Special character or math operator

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
