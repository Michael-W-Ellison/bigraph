#!/usr/bin/env python3
"""
Basic functionality test without pytest
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder
from bigraph.symbols import SymbolGenerator


def test_symbol_generation():
    """Test symbol generation"""
    print("Testing symbol generation...")
    gen = SymbolGenerator(seed=42)
    symbols = gen.generate_all_symbols()
    print(f"  Generated {len(symbols)} symbols")
    print(f"  First symbol preview: {symbols[0][:50]}...")
    assert len(symbols) > 0
    print("  ✓ Symbol generation passed")


def test_key_generation():
    """Test key generation"""
    print("\nTesting key generation...")
    km = KeyManager()
    key = km.generate_key('TestUser', seed=42)
    print(f"  Created key for: {key['recipient']}")
    print(f"  Symbol mappings: {len(key['symbol_to_meaning'])}")
    print(f"  SVG symbols: {len(key['symbols_svg'])}")
    assert key is not None
    assert len(key['symbol_to_meaning']) > 0
    print("  ✓ Key generation passed")
    return key


def test_encoding_decoding(key):
    """Test encoding and decoding"""
    print("\nTesting encoding and decoding...")

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    # Test simple message
    plaintext = "HELLO WORLD"
    print(f"  Original: {plaintext}")

    encoded = encoder.encode(plaintext)
    print(f"  Encoded to {len(encoded)} symbols: {encoded[:10]}...")

    decoded = decoder.decode(encoded)
    print(f"  Decoded: {decoded}")

    assert 'HELLO' in decoded
    assert 'WORLD' in decoded
    print("  ✓ Basic encoding/decoding passed")


def test_single_letters(key):
    """Test single letter words"""
    print("\nTesting single letter words (A, I)...")

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "I AM A PERSON"
    print(f"  Original: {plaintext}")

    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)
    print(f"  Decoded: {decoded}")

    assert 'I' in decoded or 'A' in decoded
    print("  ✓ Single letter words passed")


def test_sentences(key):
    """Test sentences"""
    print("\nTesting sentences...")

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "THIS IS A TEST. THIS IS ONLY A TEST."
    print(f"  Original: {plaintext}")

    encoded = encoder.encode(plaintext)
    print(f"  Encoded to {len(encoded)} symbols")

    decoded = decoder.decode(encoded)
    print(f"  Decoded: {decoded}")

    assert 'THIS' in decoded
    assert 'TEST' in decoded
    print("  ✓ Sentence encoding passed")


def test_numbers(key):
    """Test number encoding"""
    print("\nTesting number encoding...")

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "THE YEAR IS 2024"
    print(f"  Original: {plaintext}")

    encoded = encoder.encode(plaintext)
    decoded = decoder.decode(encoded)
    print(f"  Decoded: {decoded}")

    assert 'YEAR' in decoded
    assert '2024' in decoded
    print("  ✓ Number encoding passed")


def test_math_expressions(key):
    """Test math expression encoding"""
    print("\nTesting math expressions...")

    encoder = BigramEncoder(key)

    # Test multiplication
    mult = encoder.encode_math_expression("2 * 3")
    print(f"  Multiplication '2 * 3': {len(mult)} symbols")

    # Test division
    div = encoder.encode_math_expression("6 / 2")
    print(f"  Division '6 / 2': {len(div)} symbols")

    assert len(mult) > 0
    assert len(div) > 0
    print("  ✓ Math expression encoding passed")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Bigraph Cryptography System - Basic Functionality Tests")
    print("=" * 60)

    try:
        test_symbol_generation()
        key = test_key_generation()
        test_encoding_decoding(key)
        test_single_letters(key)
        test_sentences(key)
        test_numbers(key)
        test_math_expressions(key)

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✓")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
