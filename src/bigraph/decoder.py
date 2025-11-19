"""
Decoder for Bigraph Cryptography System

Converts encoded number lists back to plaintext using the encryption key.
"""

from typing import List, Dict
from .constants import SPACE_MARKERS
from .key_manager import KeyManager


class BigramDecoder:
    """Decodes encoded messages using the bigram system"""

    def __init__(self, key: Dict):
        """
        Initialize the decoder with a key

        Args:
            key: Decryption key dictionary (same as encryption key)
        """
        self.key = key
        self.key_manager = KeyManager()

    def decode(self, encoded: List[int]) -> str:
        """
        Decode a list of symbol indices back to plaintext

        Args:
            encoded: List of symbol indices

        Returns:
            Decoded plaintext string
        """
        result = []
        i = 0

        while i < len(encoded):
            symbol_idx = encoded[i]

            # Check if this is a partial marker case
            if symbol_idx < 0:
                # Negative number indicates partial marker BEFORE symbol
                # The actual symbol index is -(symbol_idx + 1)
                actual_symbol = -(symbol_idx + 1)
                meaning = self.key_manager.get_meaning_from_symbol(self.key, actual_symbol)

                if meaning and meaning in self.key['meaning_to_symbol']:
                    # This is a bigram, use only the first letter
                    result.append(meaning[0])

            elif symbol_idx >= 10000:
                # High offset indicates partial marker AFTER symbol
                actual_symbol = symbol_idx - 10000
                meaning = self.key_manager.get_meaning_from_symbol(self.key, actual_symbol)

                if meaning and meaning in self.key['meaning_to_symbol']:
                    # This is a bigram, use only the second letter
                    result.append(meaning[1])

            else:
                # Regular symbol
                meaning = self.key_manager.get_meaning_from_symbol(self.key, symbol_idx)

                if meaning:
                    # Check what type of symbol this is
                    if meaning.startswith('SPACE_'):
                        # Check if this is part of a sentence ending (two consecutive space markers)
                        if i + 1 < len(encoded):
                            next_meaning = self.key_manager.get_meaning_from_symbol(self.key, encoded[i + 1])
                            if next_meaning and next_meaning.startswith('SPACE_'):
                                # Sentence ending
                                result.append('. ')
                                i += 1  # Skip next space marker
                            else:
                                # Regular space
                                result.append(' ')
                        else:
                            # Regular space
                            result.append(' ')

                    elif meaning.startswith('NUM_NEG_'):
                        # Negative number (used in division)
                        digit = meaning.split('_')[-1]
                        result.append(digit)

                    elif meaning.startswith('NUM_'):
                        # Positive number
                        digit = meaning.split('_')[-1]
                        result.append(digit)

                    elif meaning == 'MULDIV':
                        # Multiply/divide indicator
                        # Look ahead to determine operation
                        if i + 1 < len(encoded):
                            next_meaning = self.key_manager.get_meaning_from_symbol(self.key, encoded[i + 1])
                            if next_meaning and next_meaning.startswith('NUM_NEG_'):
                                result.append(' / ')
                            else:
                                result.append(' * ')
                        else:
                            result.append(' * ')

                    elif meaning.startswith('SPECIAL_'):
                        # Special character
                        char = meaning.split('_', 1)[-1]
                        result.append(char)

                    elif meaning in self.key['meaning_to_symbol']:
                        # Regular bigram
                        result.append(meaning)

            i += 1

        return ''.join(result)

    def decode_with_symbols(self, encoded: List[int]) -> List[Dict]:
        """
        Decode message and return both plaintext and symbol information

        Args:
            encoded: List of symbol indices

        Returns:
            List of dictionaries with symbol info and decoded text
        """
        result = []
        i = 0

        while i < len(encoded):
            symbol_idx = encoded[i]
            actual_symbol = symbol_idx

            # Handle partial markers
            partial_before = False
            partial_after = False

            if symbol_idx < 0:
                partial_before = True
                actual_symbol = -(symbol_idx + 1)
            elif symbol_idx >= 10000:
                partial_after = True
                actual_symbol = symbol_idx - 10000

            meaning = self.key_manager.get_meaning_from_symbol(self.key, actual_symbol)
            svg = self.key_manager.get_svg_for_symbol(self.key, actual_symbol)

            decoded_text = ""

            if meaning:
                if partial_before and meaning in self.key['meaning_to_symbol']:
                    decoded_text = meaning[0]
                elif partial_after and meaning in self.key['meaning_to_symbol']:
                    decoded_text = meaning[1]
                elif meaning.startswith('SPACE_'):
                    if i + 1 < len(encoded):
                        next_meaning = self.key_manager.get_meaning_from_symbol(self.key, encoded[i + 1])
                        if next_meaning and next_meaning.startswith('SPACE_'):
                            decoded_text = ". "
                            i += 1
                        else:
                            decoded_text = " "
                    else:
                        decoded_text = " "
                elif meaning.startswith('NUM_NEG_'):
                    decoded_text = meaning.split('_')[-1]
                elif meaning.startswith('NUM_'):
                    decoded_text = meaning.split('_')[-1]
                elif meaning == 'MULDIV':
                    if i + 1 < len(encoded):
                        next_meaning = self.key_manager.get_meaning_from_symbol(self.key, encoded[i + 1])
                        if next_meaning and next_meaning.startswith('NUM_NEG_'):
                            decoded_text = " / "
                        else:
                            decoded_text = " * "
                    else:
                        decoded_text = " * "
                elif meaning.startswith('SPECIAL_'):
                    decoded_text = meaning.split('_', 1)[-1]
                else:
                    decoded_text = meaning

            result.append({
                'symbol_index': symbol_idx,
                'actual_symbol': actual_symbol,
                'meaning': meaning,
                'svg': svg,
                'decoded_text': decoded_text,
                'partial_before': partial_before,
                'partial_after': partial_after
            })

            i += 1

        return result

    def load_and_decode(self, filepath: str) -> str:
        """
        Load an encoded message file and decode it

        Args:
            filepath: Path to the encoded message file

        Returns:
            Decoded plaintext
        """
        with open(filepath, 'r') as f:
            content = f.read().strip()
            encoded = [int(x) for x in content.split(',') if x.strip()]

        return self.decode(encoded)
