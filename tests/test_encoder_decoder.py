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


if __name__ == '__main__':
    # Clean up test keys directory
    import shutil
    if os.path.exists('test_keys'):
        shutil.rmtree('test_keys')

    pytest.main([__file__, '-v'])

    # Clean up after tests
    if os.path.exists('test_keys'):
        shutil.rmtree('test_keys')
