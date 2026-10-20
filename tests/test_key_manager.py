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



def test_load_key_redraws_symbols(temp_keys_dir):
    """Test that loading a key replaces stored symbols with current ones"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test', seed=42)
    expected = key['symbols_svg']

    key['symbols_svg'] = ['<svg>old</svg>'] * len(expected)
    filepath = km.save_key(key)

    loaded = km.load_key(filepath)
    assert loaded['symbols_svg'] == expected


def test_unseeded_keys_use_secure_randomness(temp_keys_dir):
    """Test that keys without a seed are not reproducible and use a 128-bit symbol seed"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key1 = km.generate_key('User1')
    key2 = km.generate_key('User1')

    assert key1['seed'] is None
    assert key1['symbol_to_meaning'] != key2['symbol_to_meaning']
    assert key1['symbol_seed'] != key2['symbol_seed']
    assert 0 <= key1['symbol_seed'] < 2**128


def test_generate_key_does_not_change_global_random_state(temp_keys_dir):
    """Test that key generation does not reseed the global random module"""
    import random
    km = KeyManager(keys_directory=temp_keys_dir)

    random.seed(7)
    expected = random.random()
    random.seed(7)
    km.generate_key('User1', seed=42)
    km.generate_key('User2')

    assert random.random() == expected


def test_unseeded_key_redraws_same_symbols_on_load(temp_keys_dir):
    """Test that a secure key's symbols are redrawn identically from its symbol seed"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test')
    filepath = km.save_key(key)

    loaded = km.load_key(filepath)

    assert loaded['symbols_svg'] == key['symbols_svg']


def test_load_key_without_symbol_seed(temp_keys_dir):
    """Test that keys saved before symbol_seed was added redraw from their seed"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test', seed=42)
    expected = key['symbols_svg']
    del key['symbol_seed']
    key['symbols_svg'] = ['<svg>old</svg>'] * len(expected)
    filepath = km.save_key(key)

    loaded = km.load_key(filepath)

    assert loaded['symbols_svg'] == expected


def test_word_symbols_in_key(temp_keys_dir):
    """Test that keys include the common word symbols"""
    from bigraph.constants import word_symbol_counts, WORD_SYMBOL_BUDGET, TOTAL_SYMBOLS
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test', seed=42)

    word_meanings = [m for m in key['meaning_to_symbol'] if m.startswith('WORD_')]
    counts = word_symbol_counts()

    assert len(word_meanings) == WORD_SYMBOL_BUDGET == sum(counts.values())
    assert len(counts) == 100
    assert len(key['symbols_svg']) == len(key['symbol_to_meaning']) == TOTAL_SYMBOLS
    assert len(set(key['symbols_svg'])) == TOTAL_SYMBOLS
    # More frequent words get more symbols
    assert counts['THE'] > counts['AND'] > counts['WITH'] >= 1


def test_larger_word_symbol_budget(temp_keys_dir):
    """Test that a larger budget adds more symbols, using more complex shapes"""
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test', seed=42, word_symbol_budget=2500)

    assert len(key['symbol_to_meaning']) == len(set(key['symbols_svg'])) == 721 + 2500 + 1500

def test_extra_bigram_symbols_in_key(temp_keys_dir):
    """Test that common bigrams get extra symbols in proportion to their use"""
    from bigraph.constants import bigram_symbol_counts, BIGRAM_SYMBOL_BUDGET
    km = KeyManager(keys_directory=temp_keys_dir)
    key = km.generate_key('Test', seed=42)
    counts = bigram_symbol_counts()

    alt_meanings = [m for m in key['meaning_to_symbol'] if m.startswith('ALT_')]
    assert len(alt_meanings) == BIGRAM_SYMBOL_BUDGET == sum(counts.values())
    assert counts['IN'] > counts['TH'] > counts.get('EW', 0)

    no_extra = km.generate_key('Test', seed=42, bigram_symbol_budget=0)
    assert not any(m.startswith('ALT_') for m in no_extra['meaning_to_symbol'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
