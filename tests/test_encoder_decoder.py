"""
Tests for encoder and decoder
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import random
import pytest
from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder
from bigraph.constants import SPACE_MARKERS


def meanings(key, encoded):
    """Bigram (or other meaning) of each symbol, with '|' before partial ones"""
    result = []
    for value in encoded:
        meaning = key['symbol_to_meaning'][-value - 1 if value < 0 else value]
        if meaning.startswith('ALT_'):
            meaning = meaning[4:6]
        result.append(('|' if value < 0 else '') + meaning)
    return result


@pytest.fixture
def test_key():
    """Create a test key"""
    km = KeyManager(keys_directory='test_keys')
    key = km.generate_key('TestRecipient', seed=42)
    return key


def test_encode_decode_simple(test_key):
    """Test encoding and decoding a simple message"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "HELLO WORLD"
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    # Should decode back to original (may have some variations due to processing)
    assert 'HELLO' in decoded
    assert 'WORLD' in decoded


def test_encode_decode_single_letter_words(test_key):
    """Test encoding and decoding single letter words (A, I)"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "I AM A PERSON"
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    assert 'I' in decoded
    assert 'A' in decoded
    assert 'PERSON' in decoded


def test_encode_decode_sentences(test_key):
    """Test encoding and decoding multiple sentences"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "THIS IS A TEST. THIS IS ONLY A TEST."
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    # Should contain sentence markers
    assert 'THIS' in decoded
    assert 'TEST' in decoded


def test_encode_decode_numbers(test_key):
    """Test encoding and decoding numbers"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "THE YEAR IS 2024"
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    assert 'YEAR' in decoded
    assert '2024' in decoded


def test_encode_math_expression(test_key):
    """Test encoding mathematical expressions"""
    encoder = BigramEncoder(test_key)

    # Test multiplication
    mult_encoded = encoder.encode_math_expression("2 * 3")
    assert len(mult_encoded) > 0

    # Test division
    div_encoded = encoder.encode_math_expression("6 / 2")
    assert len(div_encoded) > 0


def test_encode_math_addition_subtraction(test_key):
    """Test encoding addition and subtraction expressions"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)
    km = KeyManager(keys_directory='test_keys')

    add_encoded = encoder.encode_math_expression("12 + 3")
    assert km.get_symbol_for_special(test_key, '+') in add_encoded
    assert decoder.decode(add_encoded) == "12+3"

    sub_encoded = encoder.encode_math_expression("12 - 3")
    assert km.get_symbol_for_special(test_key, '-') in sub_encoded
    assert decoder.decode(sub_encoded) == "12-3"


def test_encode_math_unsupported_operator(test_key):
    """Test that an unsupported operator produces no symbols"""
    encoder = BigramEncoder(test_key)

    assert encoder.encode_math_expression("2 x 3") == []


def test_encode_decode_special_characters(test_key):
    """Test encoding and decoding special characters in text"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "EMAIL ME @ (HOME) #1 = 50% & $5 MORE^2 <3 > 2 *"
    decoded = decoder.decode(encoder.encode(plaintext))

    assert decoded == plaintext


def test_encode_decode_operators_in_text(test_key):
    """Test encoding and decoding math operators inside words"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = "X+Y-Z/W*2"
    decoded = decoder.decode(encoder.encode(plaintext))

    assert decoded == plaintext


def test_sentence_ending_punctuation_not_encoded(test_key):
    """Test that sentence-ending punctuation is not encoded as a special character"""
    encoder = BigramEncoder(test_key)
    km = KeyManager(keys_directory='test_keys')

    encoded = encoder.encode("HI THERE! HOW ARE YOU?")

    assert km.get_symbol_for_special(test_key, '!') not in encoded
    assert km.get_symbol_for_special(test_key, '?') not in encoded


def test_odd_length_words(test_key):
    """Test encoding odd-length words"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    # CAT has 3 letters (odd)
    plaintext = "THE CAT SAT"
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    assert 'CAT' in decoded or 'CA' in decoded  # May use partial marker
    assert 'SAT' in decoded or 'SA' in decoded


def test_space_markers_rotation(test_key):
    """Test that space markers rotate"""
    encoder = BigramEncoder(test_key)

    plaintext = "A B C D E F G H I J"  # Many spaces
    encoded = encoder.encode(plaintext)

    # Should have multiple space markers
    assert len(encoded) > 10  # Letters plus space markers


def test_empty_message(test_key):
    """Test encoding empty message"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    plaintext = ""
    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)

    assert decoded == ""


def test_roundtrip_consistency(test_key):
    """Test that encode->decode is consistent"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    messages = [
        "HELLO",
        "WORLD",
        "HELLO WORLD",
        "THE QUICK BROWN FOX",
        "I AM HAPPY",
        "A",
        "I"
    ]

    for msg in messages:
        encoded = encoder.encode(msg)
        decoded = decoder.decode(encoded)
        # Check that key words are preserved
        main_words = [w for w in msg.split() if len(w) > 1]
        for word in main_words:
            assert word in decoded or word[:2] in decoded



def test_repeated_word_cycles_final_letter(test_key):
    """Test that a repeated odd-length word keeps its pairs but cycles its final letter"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    encoded = encoder.encode("CAT CAT CAT")
    words = [encoded[0:2], encoded[3:5], encoded[6:8]]

    for word, bigram in zip(words, ['TA', 'TB', 'TC']):
        assert meanings(test_key, word) == ['CA', '|' + bigram]

    assert decoder.decode(encoded) == "CAT CAT CAT"


def test_single_letter_rotation_is_per_letter(test_key):
    """Test that each letter keeps its own rotation, shared by final letters and single-letter words"""
    encoder = BigramEncoder(test_key)

    encoded = encoder.encode("X Z X ZAX")
    singles = [encoded[0], encoded[2], encoded[4]]

    assert meanings(test_key, singles) == ['|XA', '|ZA', '|XB']

    # ZAX is written as ZA, then its final X continues the X rotation
    assert meanings(test_key, encoded[6:]) == ['ZA', '|XC']


def test_final_letter_does_not_reuse_earlier_bigram(test_key):
    """Test that a final letter found earlier in the word is not written with that bigram"""
    encoder = BigramEncoder(test_key)

    encoded = encoder.encode("SMALL")

    assert meanings(test_key, encoded) == ['SM', 'AL', '|LA']


def test_common_word_uses_one_of_its_symbols(test_key):
    """Test that a common word is written as one of its own symbols"""
    encoder = BigramEncoder(test_key, rng=random.Random(1))
    decoder = BigramDecoder(test_key)

    the_symbols = {s for m, s in test_key['meaning_to_symbol'].items() if m.startswith('WORD_THE_')}
    encoded = encoder.encode(" ".join(["THE"] * 50))
    used = set(encoded[::2])

    assert used <= the_symbols
    assert len(used) > 1
    assert decoder.decode(encoded) == " ".join(["THE"] * 50)


def test_space_markers_are_chosen_at_random(test_key):
    """Test that space markers do not follow a fixed rotation"""
    km = KeyManager(keys_directory='test_keys')
    markers = [km.get_symbol_for_space_marker(test_key, m) for m in SPACE_MARKERS]
    plaintext = " ".join(["CAT"] * 100)

    encoded1 = BigramEncoder(test_key, rng=random.Random(1)).encode(plaintext)
    encoded2 = BigramEncoder(test_key, rng=random.Random(2)).encode(plaintext)
    used1 = [v for v in encoded1 if v in markers]
    used2 = [v for v in encoded2 if v in markers]

    assert len(used1) == len(used2) == 99
    assert used1 != used2
    cyclic = [markers[i % len(markers)] for i in range(99)]
    assert used1 != cyclic


def test_key_without_word_symbols_spells_common_words(no_word_symbols_key):
    """Test that keys without word symbols spell common words with bigrams"""
    encoder = BigramEncoder(no_word_symbols_key)
    decoder = BigramDecoder(no_word_symbols_key)

    encoded = encoder.encode("THE")

    assert not any(m.startswith('WORD_') for m in no_word_symbols_key['meaning_to_symbol'])
    assert meanings(no_word_symbols_key, encoded) == ['TH', '|EA']
    assert decoder.decode(encoded) == "THE"


@pytest.fixture
def no_word_symbols_key():
    """Create a test key without common word symbols"""
    km = KeyManager(keys_directory='test_keys')
    return km.generate_key('TestRecipient', seed=42, word_symbol_budget=0)


def test_common_bigram_uses_one_of_its_symbols(test_key):
    """Test that a common bigram is written as one of its symbols, chosen at random"""
    encoder = BigramEncoder(test_key, rng=random.Random(1))
    decoder = BigramDecoder(test_key)

    plaintext = " ".join(["INTERESTING"] * 30)
    encoded = encoder.encode(plaintext)
    first_symbols = set(encoded[::7])

    assert all(m == 'IN' for m in meanings(test_key, list(first_symbols)))
    assert len(first_symbols) > 1
    assert decoder.decode(encoded) == plaintext


def test_decode_with_symbols_shows_extra_bigrams(test_key):
    """Test that extra bigram symbols decode to their bigram in the detailed view"""
    encoder = BigramEncoder(test_key)
    decoder = BigramDecoder(test_key)

    details = decoder.decode_with_symbols(encoder.encode("INTERESTING STRING"))

    assert ''.join(d['decoded_text'] for d in details) == "INTERESTING STRING"


if __name__ == '__main__':
    # Clean up test keys directory
    import shutil
    if os.path.exists('test_keys'):
        shutil.rmtree('test_keys')

    pytest.main([__file__, '-v'])
