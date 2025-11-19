"""
Encoder for Bigraph Cryptography System

Converts plaintext to encoded number lists using the bigram-based
substitution cipher with special rules for spaces, sentence endings,
and number handling.
"""

import re
from typing import List, Tuple, Dict, Optional
from .constants import (BIGRAMS, SPACE_MARKERS, PARTIAL_MARKER,
                       DEFAULT_FINAL_BIGRAM, LETTERS)
from .key_manager import KeyManager


class BigramEncoder:
    """Encodes plaintext messages using the bigram system"""

    def __init__(self, key: Dict):
        """
        Initialize the encoder with a key

        Args:
            key: Encryption key dictionary
        """
        self.key = key
        self.key_manager = KeyManager()

        # Track rotation counters
        self.space_marker_index = 0
        self.a_rotation_index = 0
        self.i_rotation_index = 0

    def encode(self, plaintext: str) -> List[int]:
        """
        Encode plaintext to a list of symbol indices

        Args:
            plaintext: Text to encode

        Returns:
            List of symbol indices representing the encoded message
        """
        # Reset rotation counters for each encoding
        self.space_marker_index = 0
        self.a_rotation_index = 0
        self.i_rotation_index = 0

        # Preprocess text
        processed = self._preprocess_text(plaintext)

        # Split into sentences
        sentences = self._split_sentences(processed)

        # Encode each sentence
        result = []
        for i, sentence in enumerate(sentences):
            encoded_sentence = self._encode_sentence(sentence)
            result.extend(encoded_sentence)

            # Add sentence ending marker (two consecutive space markers)
            if i < len(sentences) - 1:  # Not the last sentence
                result.extend(self._get_sentence_end_marker())

        return result

    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text before encoding

        Args:
            text: Raw input text

        Returns:
            Preprocessed text (uppercase, etc.)
        """
        # Convert to uppercase
        text = text.upper()

        # Keep letters, numbers, spaces, special characters, and punctuation
        # We'll handle these separately
        return text

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences

        Args:
            text: Preprocessed text

        Returns:
            List of sentences
        """
        # Split on period, exclamation, question mark followed by space or end
        sentences = re.split(r'([.!?])\s*', text)

        # Recombine sentences with their punctuation
        result = []
        i = 0
        while i < len(sentences):
            if sentences[i].strip():
                sent = sentences[i]
                # Check if next element is punctuation
                if i + 1 < len(sentences) and sentences[i + 1] in '.!?':
                    sent += sentences[i + 1]
                    i += 2
                else:
                    i += 1
                result.append(sent.strip())
            else:
                i += 1

        return result if result else [text]

    def _encode_sentence(self, sentence: str) -> List[int]:
        """
        Encode a single sentence

        Args:
            sentence: Sentence to encode

        Returns:
            List of symbol indices
        """
        result = []

        # Split into words and handle each word
        words = sentence.split()

        for i, word in enumerate(words):
            # Encode the word
            encoded_word = self._encode_word(word)
            result.extend(encoded_word)

            # Add space marker after each word except the last
            if i < len(words) - 1:
                result.append(self._get_space_marker())

        return result

    def _encode_word(self, word: str) -> List[int]:
        """
        Encode a single word

        Args:
            word: Word to encode

        Returns:
            List of symbol indices
        """
        # Remove punctuation and special characters for now (handle separately if needed)
        # Keep only letters and numbers
        clean_word = ''.join(c for c in word if c.isalnum())

        if not clean_word:
            return []

        # Handle standalone 'A' or 'I' with rotation
        if clean_word == 'A':
            return self._encode_standalone_a()
        elif clean_word == 'I':
            return self._encode_standalone_i()

        # Handle numbers
        if clean_word.isdigit():
            return self._encode_number_sequence(clean_word)

        # Handle regular words with letters
        result = []

        # Check if word has odd or even length
        if len(clean_word) % 2 == 0:
            # Even length - encode as bigrams
            for i in range(0, len(clean_word), 2):
                bigram = clean_word[i:i+2]
                symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
                if symbol is not None:
                    result.append(symbol)
        else:
            # Odd length - encode all but last letter, then handle last letter
            # Encode pairs
            for i in range(0, len(clean_word) - 1, 2):
                bigram = clean_word[i:i+2]
                symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
                if symbol is not None:
                    result.append(symbol)

            # Handle last letter
            last_letter = clean_word[-1]
            last_symbol = self._encode_final_letter(clean_word, last_letter)
            result.extend(last_symbol)

        return result

    def _encode_final_letter(self, word: str, last_letter: str) -> List[int]:
        """
        Encode the final letter of an odd-length word

        Rules:
        1. If the letter appears earlier in the word, reuse that bigram with partial marker
        2. Otherwise, use default bigram (SA) with partial marker

        Args:
            word: Full word
            last_letter: The final letter to encode

        Returns:
            List of symbol indices (partial marker + bigram or bigram + partial marker)
        """
        # Look for the letter earlier in the word
        for i in range(len(word) - 1):
            if word[i] == last_letter:
                # Found it! Determine which bigram it's part of
                # Find the bigram containing this occurrence
                bigram_index = i // 2
                start_idx = bigram_index * 2

                if start_idx + 1 < len(word):
                    bigram = word[start_idx:start_idx + 2]

                    # Determine if we use first or second letter
                    if i % 2 == 0:
                        # Last letter is the first letter of the bigram
                        # Use | before the symbol
                        symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
                        if symbol is not None:
                            # Return partial marker indicator (we'll use a special encoding)
                            # For now, we'll use negative symbol index to indicate partial-before
                            return [-symbol - 1]  # Negative indicates partial marker before
                    else:
                        # Last letter is the second letter of the bigram
                        # Use | after the symbol
                        symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
                        if symbol is not None:
                            # Positive but add offset to indicate partial-after
                            # We'll use a high offset that won't conflict
                            return [symbol + 10000]  # +10000 indicates partial marker after

        # Letter not found - create a bigram with this letter
        # Use the letter + A as the bigram, and mark to use only the first letter
        default_bigram = f"{last_letter}A"
        symbol = self.key_manager.get_symbol_for_bigram(self.key, default_bigram)

        if symbol is not None:
            # Use first letter of the bigram, so partial marker before
            return [-symbol - 1]

        return []

    def _encode_standalone_a(self) -> List[int]:
        """
        Encode standalone 'A' with rotation

        Uses AA, AB, AC, etc. in sequence
        """
        bigram_index = self.a_rotation_index % 26
        bigram = f"A{LETTERS[bigram_index]}"
        self.a_rotation_index += 1

        symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
        if symbol is not None:
            # Return with partial marker (only first letter used)
            return [-symbol - 1]
        return []

    def _encode_standalone_i(self) -> List[int]:
        """
        Encode standalone 'I' with rotation

        Uses IA, IB, IC, etc. in sequence
        """
        bigram_index = self.i_rotation_index % 26
        bigram = f"I{LETTERS[bigram_index]}"
        self.i_rotation_index += 1

        symbol = self.key_manager.get_symbol_for_bigram(self.key, bigram)
        if symbol is not None:
            # Return with partial marker (only first letter used)
            return [-symbol - 1]
        return []

    def _encode_number_sequence(self, number_str: str) -> List[int]:
        """
        Encode a sequence of digits

        Args:
            number_str: String of digits

        Returns:
            List of symbol indices
        """
        result = []
        for digit in number_str:
            symbol = self.key_manager.get_symbol_for_number(self.key, int(digit))
            if symbol is not None:
                result.append(symbol)
        return result

    def encode_math_expression(self, expression: str) -> List[int]:
        """
        Encode a mathematical expression

        Format: number [op] number
        Where op is * or /
        - Multiplication uses positive numbers
        - Division uses negative numbers
        - A special multiply/divide symbol separates operands

        Example: "2 * 3" -> [symbol(2), symbol(MULDIV), symbol(3)]
                 "6 / 2" -> [symbol(6), symbol(MULDIV), symbol(-2)]

        Args:
            expression: Math expression string

        Returns:
            List of symbol indices
        """
        result = []

        # Parse expression
        # Simple parser for "number op number"
        parts = expression.strip().split()

        if len(parts) < 3:
            return result

        num1 = parts[0]
        operator = parts[1]
        num2 = parts[2]

        # Encode first number (always positive)
        for digit in num1:
            if digit.isdigit():
                symbol = self.key_manager.get_symbol_for_number(self.key, int(digit))
                if symbol is not None:
                    result.append(symbol)

        # Add multiply/divide indicator
        muldiv_symbol = self.key_manager.get_muldiv_symbol(self.key)
        if muldiv_symbol is not None:
            result.append(muldiv_symbol)

        # Encode second number
        # If division, use negative; if multiplication, use positive
        for digit in num2:
            if digit.isdigit():
                if operator == '/':
                    # Use negative number
                    symbol = self.key_manager.get_symbol_for_number(self.key, -int(digit))
                else:  # multiplication
                    # Use positive number
                    symbol = self.key_manager.get_symbol_for_number(self.key, int(digit))

                if symbol is not None:
                    result.append(symbol)

        return result

    def _get_space_marker(self) -> int:
        """
        Get the next space marker symbol (rotating through the 7 rare bigrams)

        Returns:
            Symbol index for space marker
        """
        marker = SPACE_MARKERS[self.space_marker_index % len(SPACE_MARKERS)]
        self.space_marker_index += 1

        symbol = self.key_manager.get_symbol_for_space_marker(self.key, marker)
        return symbol if symbol is not None else 0

    def _get_sentence_end_marker(self) -> List[int]:
        """
        Get sentence ending markers (two consecutive space markers)

        Returns:
            List of two symbol indices
        """
        return [self._get_space_marker(), self._get_space_marker()]

    def save_encoded_message(self, encoded: List[int], filepath: str):
        """
        Save encoded message to a file

        Args:
            encoded: List of symbol indices
            filepath: Path to save the file
        """
        with open(filepath, 'w') as f:
            # Write as comma-separated numbers
            f.write(','.join(map(str, encoded)))

    def load_encoded_message(self, filepath: str) -> List[int]:
        """
        Load encoded message from a file

        Args:
            filepath: Path to the encoded message file

        Returns:
            List of symbol indices
        """
        with open(filepath, 'r') as f:
            content = f.read().strip()
            return [int(x) for x in content.split(',') if x.strip()]
