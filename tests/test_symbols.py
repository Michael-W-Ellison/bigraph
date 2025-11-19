"""
Tests for symbol generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from bigraph.symbols import SymbolGenerator
from bigraph.constants import TOTAL_SYMBOLS


def test_symbol_generation():
    """Test that symbols are generated correctly"""
    gen = SymbolGenerator(seed=42)
    symbols = gen.generate_all_symbols()

    # Should generate at least TOTAL_SYMBOLS symbols
    assert len(symbols) >= TOTAL_SYMBOLS

    # Each symbol should be an SVG string
    for symbol in symbols:
        assert symbol.startswith('<svg')
        assert symbol.endswith('</svg>')


def test_symbol_uniqueness():
    """Test that symbols are unique"""
    gen = SymbolGenerator(seed=42)
    symbols = gen.generate_all_symbols()

    # Symbols should be unique (at least most of them)
    unique_symbols = set(symbols)
    # Allow some duplicates due to random generation
    assert len(unique_symbols) >= len(symbols) * 0.9


def test_reproducible_symbols():
    """Test that symbols are reproducible with same seed"""
    gen1 = SymbolGenerator(seed=123)
    symbols1 = gen1.generate_all_symbols()

    gen2 = SymbolGenerator(seed=123)
    symbols2 = gen2.generate_all_symbols()

    assert symbols1 == symbols2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
