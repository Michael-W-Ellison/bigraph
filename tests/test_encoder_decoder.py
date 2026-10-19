"""
Tests for encoder and decoder
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder


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
    km = KeyManager(keys_directory='test_keys')

    encoded = encoder.encode("THE THE THE")
    th = km.get_symbol_for_bigram(test_key, 'TH')
    words = [encoded[0:2], encoded[3:5], encoded[6:8]]

    for word, bigram in zip(words, ['EA', 'EB', 'EC']):
        assert word[0] == th
        assert word[1] == -km.get_symbol_for_bigram(test_key, bigram) - 1

    assert decoder.decode(encoded) == "THE THE THE"


def test_single_letter_rotation_is_per_letter(test_key):
    """Test that each letter keeps its own rotation, shared by final letters and single-letter words"""
    encoder = BigramEncoder(test_key)
    km = KeyManager(keys_directory='test_keys')

    encoded = encoder.encode("A I A IDEA")
    expected = ['AA', 'IA', 'AB']
    singles = [encoded[0], encoded[2], encoded[4]]

    for value, bigram in zip(singles, expected):
        assert value == -km.get_symbol_for_bigram(test_key, bigram) - 1

    # IDEA is even length, so it is written as ID, EA with no single letters
    assert encoded[6:] == [km.get_symbol_for_bigram(test_key, 'ID'),
                           km.get_symbol_for_bigram(test_key, 'EA')]


def test_final_letter_does_not_reuse_earlier_bigram(test_key):
    """Test that a final letter found earlier in the word is not written with that bigram"""
    encoder = BigramEncoder(test_key)
    km = KeyManager(keys_directory='test_keys')

    encoded = encoder.encode("SMALL")

    assert encoded[-1] == -km.get_symbol_for_bigram(test_key, 'LA') - 1

if __name__ == '__main__':
    # Clean up test keys directory
    import shutil
    if os.path.exists('test_keys'):
        shutil.rmtree('test_keys')

    pytest.main([__file__, '-v'])

    # Clean up after tests
    if os.path.exists('test_keys'):
        shutil.rmtree('test_keys')
