#!/usr/bin/env python3
"""
Example Usage of Bigraph Cryptography System

Demonstrates various features of the system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder


def example_basic_encoding():
    """Example 1: Basic message encoding and decoding"""
    print("=" * 60)
    print("Example 1: Basic Message Encoding")
    print("=" * 60)

    # Generate a key
    km = KeyManager()
    key = km.generate_key("Alice", seed=12345)

    # Create encoder and decoder
    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    # Encode a message
    plaintext = "HELLO WORLD"
    encoded = encoder.encode(plaintext)

    print(f"Original message: {plaintext}")
    print(f"Encoded message: {encoded}")
    print(f"Number of symbols: {len(encoded)}")

    # Decode the message
    decoded = decoder.decode(encoded)
    print(f"Decoded message: {decoded}")
    print()


def example_single_letters():
    """Example 2: Single letter words with rotation"""
    print("=" * 60)
    print("Example 2: Single Letter Words (A, I) with Rotation")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("Bob", seed=54321)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "I AM A PERSON"
    encoded = encoder.encode(plaintext)

    print(f"Original: {plaintext}")
    print(f"Encoded: {encoded}")
    print(f"Decoded: {decoder.decode(encoded)}")
    print("\nNote: Each 'A' and 'I' uses a different symbol (rotation)")
    print()


def example_sentences():
    """Example 3: Multiple sentences with sentence markers"""
    print("=" * 60)
    print("Example 3: Multiple Sentences")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("Charlie", seed=99999)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "THIS IS A TEST. THIS IS ONLY A TEST. DO NOT PANIC."
    encoded = encoder.encode(plaintext)

    print(f"Original: {plaintext}")
    print(f"Encoded ({len(encoded)} symbols): {encoded[:20]}...")
    print(f"Decoded: {decoder.decode(encoded)}")
    print("\nNote: Sentence endings use two consecutive space markers")
    print()


def example_numbers():
    """Example 4: Numbers in text"""
    print("=" * 60)
    print("Example 4: Numbers in Text")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("Diana", seed=11111)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    plaintext = "THE YEAR IS 2024 AND THE CODE IS 12345"
    encoded = encoder.encode(plaintext)

    print(f"Original: {plaintext}")
    print(f"Encoded: {encoded}")
    print(f"Decoded: {decoder.decode(encoded)}")
    print()


def example_math_expressions():
    """Example 5: Mathematical expressions"""
    print("=" * 60)
    print("Example 5: Mathematical Expressions")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("Eve", seed=77777)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    # Multiplication
    mult_expr = "2 * 3"
    mult_encoded = encoder.encode_math_expression(mult_expr)

    print(f"Multiplication: {mult_expr}")
    print(f"Encoded: {mult_encoded}")

    # Division
    div_expr = "6 / 2"
    div_encoded = encoder.encode_math_expression(div_expr)

    print(f"\nDivision: {div_expr}")
    print(f"Encoded: {div_encoded}")

    # Decode them
    print(f"\nDecoded multiplication: {decoder.decode(mult_encoded)}")
    print(f"Decoded division: {decoder.decode(div_encoded)}")

    print("\nNote: Positive numbers = multiply, Negative numbers = divide")
    print()


def example_odd_length_words():
    """Example 6: Odd-length words with final letter optimization"""
    print("=" * 60)
    print("Example 6: Odd-Length Words")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("Frank", seed=33333)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    # Words with odd lengths
    plaintext = "CAT DOG ELEPHANT"
    encoded = encoder.encode(plaintext)

    print(f"Original: {plaintext}")
    print(f"  CAT (3 letters, odd)")
    print(f"  DOG (3 letters, odd)")
    print(f"  ELEPHANT (8 letters, even)")
    print(f"\nEncoded: {encoded}")
    print(f"Decoded: {decoder.decode(encoded)}")
    print("\nNote: Final letters in odd-length words use partial markers")
    print()


def example_key_management():
    """Example 7: Key management operations"""
    print("=" * 60)
    print("Example 7: Key Management")
    print("=" * 60)

    km = KeyManager(keys_directory="example_keys")

    # Generate multiple keys
    key1 = km.generate_key("Alice", seed=111)
    key2 = km.generate_key("Bob", seed=222)
    key3 = km.generate_key("Charlie", seed=333)

    # Save keys
    path1 = km.save_key(key1)
    path2 = km.save_key(key2)
    path3 = km.save_key(key3)

    print(f"Generated and saved 3 keys:")
    print(f"  {path1}")
    print(f"  {path2}")
    print(f"  {path3}")

    # List keys
    keys = km.list_keys()
    print(f"\nAvailable keys: {len(keys)}")
    for k in keys:
        print(f"  {k['recipient']} - Created: {k['created'][:10]}")

    # Load a key
    loaded_key = km.load_key(path1)
    print(f"\nLoaded key for: {loaded_key['recipient']}")

    # Clean up
    import shutil
    if os.path.exists("example_keys"):
        shutil.rmtree("example_keys")
    print("\nCleaned up example keys")
    print()


def example_file_operations():
    """Example 8: Save and load encoded messages"""
    print("=" * 60)
    print("Example 8: File Operations")
    print("=" * 60)

    km = KeyManager()
    key = km.generate_key("George", seed=44444)

    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)

    # Encode and save
    plaintext = "THIS IS A SECRET MESSAGE"
    encoded = encoder.encode(plaintext)

    message_file = "example_message.enc"
    encoder.save_encoded_message(encoded, message_file)
    print(f"Saved encoded message to: {message_file}")

    # Load and decode
    loaded_encoded = encoder.load_encoded_message(message_file)
    decoded = decoder.decode(loaded_encoded)

    print(f"Loaded and decoded: {decoded}")

    # Clean up
    if os.path.exists(message_file):
        os.remove(message_file)
    print(f"Cleaned up {message_file}")
    print()


def main():
    """Run all examples"""
    print("\n")
    print("*" * 60)
    print("Bigraph Cryptography System - Example Usage")
    print("*" * 60)
    print("\n")

    example_basic_encoding()
    example_single_letters()
    example_sentences()
    example_numbers()
    example_math_expressions()
    example_odd_length_words()
    example_key_management()
    example_file_operations()

    print("*" * 60)
    print("All examples completed!")
    print("*" * 60)


if __name__ == '__main__':
    main()
