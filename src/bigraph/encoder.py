"""
Encoder for Bigraph Cryptography System

Converts plaintext to encoded number lists using the bigram-based
substitution cipher with special rules for spaces, sentence endings,
and number handling.
"""

import re
import secrets
from collections import defaultdict
from typing import List, Dict, Optional
from .constants import SPACE_MARKERS, LETTERS, SPECIAL_CHARS, MATH_OPERATORS
from .key_manager import KeyManager, RetiredKeyError
from .security import format_message, parse_message


class BigramEncoder:
    """Encodes plaintext messages using the bigram system"""

    def __init__(self, key: Dict, rng=None):
        """
        Initialize the encoder with a key

        Args:
            key: Encryption key dictionary
            rng: Random source for choosing among symbols with the same
                meaning (default: the operating system's secure source)

        Raises:
            RetiredKeyError: the key may only decode (it was made under older
                security rules, or loaded from a file without a password)
        """
        if KeyManager.is_retired(key):
            raise RetiredKeyError("This key can only decode messages. Create a replacement key.")
        self.key = key
        self.key_manager = KeyManager()
        self.rng = rng if rng is not None else secrets.SystemRandom()

        # Symbols for each common word (keys made without word symbols have none)
        self.word_symbols = defaultdict(list)
        for meaning, symbol in key['meaning_to_symbol'].items():
            if meaning.startswith('WORD_'):
                word = meaning.split('_')[1]
                self.word_symbols[word].append(symbol)
        for symbols in self.word_symbols.values():
            symbols.sort()

        # Symbols for each bigram: its own, plus extra ones for common bigrams
        self.bigram_symbols = defaultdict(list)
        for meaning, symbol in key['meaning_to_symbol'].items():
            if meaning.startswith('ALT_'):
                self.bigram_symbols[meaning[4:6]].append(symbol)
            elif len(meaning) == 2 and meaning.isalpha():
                self.bigram_symbols[meaning].append(symbol)
        for symbols in self.bigram_symbols.values():
            symbols.sort()

        # Track rotation counters
        self.letter_rotation_index = {}

    def encode(self, plaintext: str) -> List[int]:
        """
        Encode plaintext to a list of symbol indices

        Args:
            plaintext: Text to encode

        Returns:
            List of symbol indices representing the encoded message
        """
        # Reset rotation counters for each encoding
        self.letter_rotation_index = {}

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

        # The sentence-ending punctuation is represented by the sentence end
        # marker, so it is not encoded as a special character
        if sentence and sentence[-1] in '.!?':
            sentence = sentence[:-1]

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

        Special characters and math operators split the word into segments.
        Each segment is encoded separately, and each special character or
        operator is encoded as its own symbol. Other characters are dropped.

        Args:
            word: Word to encode

        Returns:
            List of symbol indices
        """
        result = []
        segment = ''

        for c in word:
            if c.isalnum():
                segment += c
            elif c in SPECIAL_CHARS or c in MATH_OPERATORS:
                result.extend(self._encode_segment(segment))
                segment = ''

                symbol = self.key_manager.get_symbol_for_special(self.key, c)
                if symbol is not None:
                    result.append(symbol)

        result.extend(self._encode_segment(segment))

        return result

    def _encode_segment(self, segment: str) -> List[int]:
        """
        Encode a run of letters and digits

        Args:
            segment: Characters of a word between special characters

        Returns:
            List of symbol indices
        """
        clean_word = segment

        if not clean_word:
            return []

        # Common words have their own symbols; pick one at random
        if clean_word in self.word_symbols:
            return [self.rng.choice(self.word_symbols[clean_word])]

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
                symbol = self._bigram_symbol(bigram)
                if symbol is not None:
                    result.append(symbol)
        else:
            # Odd length - encode all but last letter, then handle last letter
            # Encode pairs
            for i in range(0, len(clean_word) - 1, 2):
                bigram = clean_word[i:i+2]
                symbol = self._bigram_symbol(bigram)
                if symbol is not None:
                    result.append(symbol)

            # Handle last letter
            result.extend(self._encode_single_letter(clean_word[-1]))

        return result

    def _bigram_symbol(self, bigram: str) -> Optional[int]:
        """
        Get a symbol for a bigram

        Common bigrams have several symbols; one is chosen at random.

        Args:
            bigram: Two-letter bigram

        Returns:
            Symbol index or None if the bigram has no symbol
        """
        symbols = self.bigram_symbols.get(bigram)
        return self.rng.choice(symbols) if symbols else None

    def _encode_single_letter(self, letter: str) -> List[int]:
        """
        Encode a single letter with rotation

        Used for the final letter of an odd-length word and for single-letter
        words such as 'A' and 'I'. Each letter cycles through its own bigrams:
        the first single 'E' uses EA, the next EB, then EC, and so on.
        Only the first letter of the bigram is used, so the partial marker
        comes before the symbol.

        Args:
            letter: Letter to encode

        Returns:
            List containing the partial-before symbol index
        """
        if not letter.isalpha():
            return []

        rotation = self.letter_rotation_index.get(letter, 0)
        self.letter_rotation_index[letter] = rotation + 1

        bigram = f"{letter}{LETTERS[rotation % len(LETTERS)]}"
        symbol = self._bigram_symbol(bigram)
        if symbol is not None:
            # Negative indicates partial marker before (only first letter used)
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
        Where op is +, -, * or /
        - Addition and subtraction use the + and - operator symbols
        - Multiplication uses positive numbers
        - Division uses negative numbers
        - A special multiply/divide symbol separates operands

        Example: "2 + 3" -> [symbol(2), symbol(+), symbol(3)]
                 "5 - 1" -> [symbol(5), symbol(-), symbol(1)]
                 "2 * 3" -> [symbol(2), symbol(MULDIV), symbol(3)]
                 "6 / 2" -> [symbol(6), symbol(MULDIV), symbol(-2)]

        Args:
            expression: Math expression string

        Returns:
            List of symbol indices (empty if the operator is not supported)
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

        if operator not in ('+', '-', '*', '/'):
            return result

        # Encode first number (always positive)
        for digit in num1:
            if digit.isdigit():
                symbol = self.key_manager.get_symbol_for_number(self.key, int(digit))
                if symbol is not None:
                    result.append(symbol)

        if operator in ('+', '-'):
            # Add the operator symbol
            op_symbol = self.key_manager.get_symbol_for_special(self.key, operator)
            if op_symbol is not None:
                result.append(op_symbol)
        else:
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
                else:  # addition, subtraction, or multiplication
                    # Use positive number
                    symbol = self.key_manager.get_symbol_for_number(self.key, int(digit))

                if symbol is not None:
                    result.append(symbol)

        return result

    def _get_space_marker(self) -> int:
        """
        Get a space marker symbol, chosen at random from the 7 rare bigrams

        A fixed rotation would let an attacker find the markers, because
        markers used in a strict cycle always alternate with each other.

        Returns:
            Symbol index for space marker
        """
        marker = self.rng.choice(SPACE_MARKERS)

        symbol = self.key_manager.get_symbol_for_space_marker(self.key, marker)
        return symbol if symbol is not None else 0

    def _get_sentence_end_marker(self) -> List[int]:
        """
        Get sentence ending markers (two consecutive space markers)

        Returns:
            List of two symbol indices
        """
        return [self._get_space_marker(), self._get_space_marker()]

    def format_message(self, encoded: List[int]) -> str:
        """
        Text of an encoded message, with a check code that detects changes

        Args:
            encoded: List of symbol indices

        Returns:
            Message text (see security.format_message)
        """
        return format_message(encoded, self.key)

    def save_encoded_message(self, encoded: List[int], filepath: str):
        """
        Save encoded message to a file, with its check code

        Args:
            encoded: List of symbol indices
            filepath: Path to save the file
        """
        with open(filepath, 'w') as f:
            f.write(self.format_message(encoded))

    def load_encoded_message(self, filepath: str) -> List[int]:
        """
        Load encoded message from a file and verify its check code

        Args:
            filepath: Path to the encoded message file

        Returns:
            List of symbol indices

        Raises:
            MessageIntegrityError: the message was changed
        """
        with open(filepath, 'r') as f:
            encoded, _ = parse_message(f.read(), self.key)
        return encoded
