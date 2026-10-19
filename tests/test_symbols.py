"""
Tests for symbol generation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
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

    assert len(set(symbols)) == len(symbols)


def test_reproducible_symbols():
    """Test that symbols are reproducible with same seed"""
    gen1 = SymbolGenerator(seed=123)
    symbols1 = gen1.generate_all_symbols()

    gen2 = SymbolGenerator(seed=123)
    symbols2 = gen2.generate_all_symbols()

    assert symbols1 == symbols2


def test_symbol_count():
    """Test that exactly TOTAL_SYMBOLS symbols are generated"""
    gen = SymbolGenerator(seed=42)

    assert len(gen.generate_all_symbols()) == TOTAL_SYMBOLS


def test_extension_rules():
    """Test that extensions follow the design rules"""
    gen = SymbolGenerator(seed=42)
    configs = gen._generate_symbol_configurations(TOTAL_SYMBOLS)

    for config in configs:
        slots = [(e['position'], e['side']) for e in config['extensions']]
        # At most one extension per side at each position
        assert len(slots) == len(set(slots))

        for ext in config['extensions']:
            assert ext['position'] in ('start', 'middle', 'end')
            assert ext['type'] in ('perpendicular', 'toward_start', 'toward_end')

        assert not gen._has_crossing_diagonals(config['extensions'])


def test_extension_lengths():
    """Test extension lengths and angles"""
    gen = SymbolGenerator(seed=42)
    full = gen.extension_length

    def length(ext):
        (a1, c1), (a2, c2) = gen._extension_segment('vertical', ext)
        return math.hypot(a2 - a1, c2 - c1)

    perpendicular = {'position': 'middle', 'side': 'left', 'type': 'perpendicular'}
    diagonal = {'position': 'middle', 'side': 'left', 'type': 'toward_end'}
    end_inward = {'position': 'end', 'side': 'left', 'type': 'toward_start'}
    end_outward = {'position': 'end', 'side': 'left', 'type': 'toward_end'}
    start_outward = {'position': 'start', 'side': 'right', 'type': 'toward_start'}

    assert length(perpendicular) == pytest.approx(full)
    assert length(diagonal) == pytest.approx(full)
    assert length(end_inward) == pytest.approx(full)
    assert length(end_outward) == pytest.approx(full / 2)
    assert length(start_outward) == pytest.approx(full / 2)

    # Diagonals are at 45 degrees
    (a1, c1), (a2, c2) = gen._extension_segment('vertical', diagonal)
    assert abs(a2 - a1) == pytest.approx(abs(c2 - c1))


def test_diagonal_tips_meet():
    """Test that diagonals from neighbouring positions meet at their tips"""
    gen = SymbolGenerator(seed=42)

    _, tip1 = gen._extension_segment(
        'vertical', {'position': 'start', 'side': 'left', 'type': 'toward_end'})
    _, tip2 = gen._extension_segment(
        'vertical', {'position': 'middle', 'side': 'left', 'type': 'toward_start'})

    assert tip1 == pytest.approx(tip2)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
