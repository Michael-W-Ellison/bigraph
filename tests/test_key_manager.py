"""
Tests for key manager
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from bigraph.key_manager import KeyManager
import tempfile
import shutil


@pytest.fixture
def temp_keys_dir():
    """Create a temporary directory for keys"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_generate_key(temp_keys_dir):
    """Test key generation"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('TestUser', seed=42)

    assert key is not None
    assert key['recipient'] == 'TestUser'
    assert 'symbol_to_meaning' in key
    assert 'meaning_to_symbol' in key
    assert 'symbols_svg' in key
    assert len(key['symbol_to_meaning']) > 0


def test_save_load_key(temp_keys_dir):
    """Test saving and loading keys"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('TestUser', seed=42)

    # Save key
    filepath = km.save_key(key)
    assert os.path.exists(filepath)

    # Load key
    loaded_key = km.load_key(filepath)
    assert loaded_key['recipient'] == key['recipient']
    assert loaded_key['seed'] == key['seed']


def test_list_keys(temp_keys_dir):
    """Test listing keys"""
    km = KeyManager(keys_directory=temp_keys_dir)

    # Generate and save some keys
    key1 = km.generate_key('User1', seed=1)
    key2 = km.generate_key('User2', seed=2)

    km.save_key(key1)
    km.save_key(key2)

    # List keys
    keys = km.list_keys()
    assert len(keys) >= 2

    recipients = [k['recipient'] for k in keys]
    assert 'User1' in recipients
    assert 'User2' in recipients


def test_reproducible_keys():
    """Test that keys are reproducible with same seed"""
    km = KeyManager()

    key1 = km.generate_key('User1', seed=123)
    key2 = km.generate_key('User1', seed=123)

    # Should have same mappings
    assert key1['symbol_to_meaning'] == key2['symbol_to_meaning']
    assert key1['meaning_to_symbol'] == key2['meaning_to_symbol']


def test_different_keys():
    """Test that different seeds produce different keys"""
    km = KeyManager()

    key1 = km.generate_key('User1', seed=123)
    key2 = km.generate_key('User1', seed=456)

    # Should have different mappings
    assert key1['symbol_to_meaning'] != key2['symbol_to_meaning']
    assert key1['meaning_to_symbol'] != key2['meaning_to_symbol']


def test_get_symbol_for_bigram():
    """Test getting symbol for bigram"""
    km = KeyManager()
    key = km.generate_key('TestUser', seed=42)

    # Should be able to get symbol for any bigram
    symbol_aa = km.get_symbol_for_bigram(key, 'AA')
    assert symbol_aa is not None

    symbol_zz = km.get_symbol_for_bigram(key, 'ZZ')
    assert symbol_zz is not None

    # Different bigrams should have different symbols
    assert symbol_aa != symbol_zz


def test_get_symbol_for_number():
    """Test getting symbol for numbers"""
    km = KeyManager()
    key = km.generate_key('TestUser', seed=42)

    # Positive numbers
    symbol_5 = km.get_symbol_for_number(key, 5)
    assert symbol_5 is not None

    # Negative numbers (for division)
    symbol_neg_5 = km.get_symbol_for_number(key, -5)
    assert symbol_neg_5 is not None

    # Should be different
    assert symbol_5 != symbol_neg_5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
