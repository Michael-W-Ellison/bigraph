#!/usr/bin/env python3
"""
Save individual SVG symbol files for inspection
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bigraph.symbols import SymbolGenerator

# Create output directory
os.makedirs('sample_symbols', exist_ok=True)

# Generate symbols
gen = SymbolGenerator(seed=12345)
symbols = gen.generate_all_symbols()

# Save first 20 symbols as individual SVG files
print("Saving sample symbol files...")
for i in range(min(20, len(symbols))):
    filename = f'sample_symbols/symbol_{i:03d}.svg'
    with open(filename, 'w') as f:
        f.write(symbols[i])
    print(f"  Saved: {filename}")

print(f"\nSaved {min(20, len(symbols))} sample SVG files to sample_symbols/")
print("You can open these files in a web browser or image viewer to see the symbols.")

# Also print one symbol to show the structure
print("\n" + "="*60)
print("Example symbol SVG code (Symbol #0):")
print("="*60)
print(symbols[0])
print("="*60)
