#!/usr/bin/env python3
"""
Generate a visual reference sheet of symbols
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bigraph.symbols import SymbolGenerator
from bigraph.key_manager import KeyManager


def generate_symbol_reference_html():
    """Generate an HTML file showing symbol examples"""

    # Generate symbols with a fixed seed for reproducibility
    gen = SymbolGenerator(seed=12345)
    symbols = gen.generate_all_symbols()

    # Also generate a key to show bigram mappings
    km = KeyManager()
    key = km.generate_key("SymbolReference", seed=12345)

    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Bigraph Symbol Reference</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        .intro {
            max-width: 800px;
            margin: 0 auto 30px auto;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section {
            margin-bottom: 40px;
        }
        .section-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 5px;
        }
        .symbol-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 15px;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .symbol-card {
            border: 2px solid #ddd;
            border-radius: 8px;
            padding: 10px;
            text-align: center;
            background-color: #fafafa;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .symbol-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            border-color: #4CAF50;
        }
        .symbol-card svg {
            width: 100px;
            height: 100px;
            margin: 10px 0;
        }
        .symbol-label {
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }
        .symbol-meaning {
            font-size: 12px;
            color: #666;
            margin-top: 3px;
        }
        .legend {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .legend h3 {
            margin-top: 0;
            color: #1976d2;
        }
    </style>
</head>
<body>
    <h1>Bigraph Cryptography System - Symbol Reference</h1>

    <div class="intro">
        <p>This reference sheet shows examples of the geometric line-based symbols used in the Bigraph Cryptography System.</p>
        <p>Each symbol is generated from a primary line (vertical or horizontal) with optional extensions at different positions and angles.</p>
    </div>

    <div class="legend">
        <h3>Symbol Components</h3>
        <ul>
            <li><strong>Primary Line:</strong> Vertical (|) or Horizontal (—)</li>
            <li><strong>Extensions:</strong> Lines extending at start, middle, or end positions</li>
            <li><strong>Angles:</strong> 90° (perpendicular) or ±45° (diagonal)</li>
            <li><strong>Sides:</strong> Left, right, or both sides of the primary line</li>
        </ul>
    </div>
"""

    # Show first 50 bigrams as examples
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Sample Bigram Symbols (First 50)</div>\n'
    html += '        <div class="symbol-grid">\n'

    bigram_count = 0
    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning in key['meaning_to_symbol'] and not meaning.startswith('NUM_') and not meaning.startswith('SPECIAL_') and not meaning.startswith('SPACE_') and meaning != 'MULDIV':
            if bigram_count < 50:
                svg = key['symbols_svg'][idx]
                html += f'            <div class="symbol-card">\n'
                html += f'                {svg}\n'
                html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
                html += f'                <div class="symbol-meaning">Bigram: {meaning}</div>\n'
                html += f'            </div>\n'
                bigram_count += 1
            else:
                break

    html += '        </div>\n'
    html += '    </div>\n'

    # Show number symbols
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Number Symbols (0-9)</div>\n'
    html += '        <div class="symbol-grid">\n'

    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning.startswith('NUM_') and not meaning.startswith('NUM_NEG_'):
            svg = key['symbols_svg'][idx]
            digit = meaning.split('_')[-1]
            html += f'            <div class="symbol-card">\n'
            html += f'                {svg}\n'
            html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
            html += f'                <div class="symbol-meaning">Number: {digit}</div>\n'
            html += f'            </div>\n'

    html += '        </div>\n'
    html += '    </div>\n'

    # Show negative number symbols
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Negative Number Symbols (for Division)</div>\n'
    html += '        <div class="symbol-grid">\n'

    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning.startswith('NUM_NEG_'):
            svg = key['symbols_svg'][idx]
            digit = meaning.split('_')[-1]
            html += f'            <div class="symbol-card">\n'
            html += f'                {svg}\n'
            html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
            html += f'                <div class="symbol-meaning">Negative: -{digit}</div>\n'
            html += f'            </div>\n'

    html += '        </div>\n'
    html += '    </div>\n'

    # Show space markers
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Space Markers (Rare Bigrams)</div>\n'
    html += '        <div class="symbol-grid">\n'

    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning.startswith('SPACE_'):
            svg = key['symbols_svg'][idx]
            marker = meaning.split('_')[-1]
            html += f'            <div class="symbol-card">\n'
            html += f'                {svg}\n'
            html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
            html += f'                <div class="symbol-meaning">Space: {marker}</div>\n'
            html += f'            </div>\n'

    html += '        </div>\n'
    html += '    </div>\n'

    # Show multiply/divide symbol
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Mathematical Operator</div>\n'
    html += '        <div class="symbol-grid">\n'

    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning == 'MULDIV':
            svg = key['symbols_svg'][idx]
            html += f'            <div class="symbol-card">\n'
            html += f'                {svg}\n'
            html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
            html += f'                <div class="symbol-meaning">Multiply/Divide Indicator</div>\n'
            html += f'            </div>\n'

    html += '        </div>\n'
    html += '    </div>\n'

    # Show special characters
    html += '    <div class="section">\n'
    html += '        <div class="section-title">Special Character Symbols</div>\n'
    html += '        <div class="symbol-grid">\n'

    for idx, meaning in sorted(key['symbol_to_meaning'].items(), key=lambda x: x[0]):
        if meaning.startswith('SPECIAL_'):
            svg = key['symbols_svg'][idx]
            char = meaning.split('_', 1)[-1]
            html += f'            <div class="symbol-card">\n'
            html += f'                {svg}\n'
            html += f'                <div class="symbol-label">Symbol #{idx}</div>\n'
            html += f'                <div class="symbol-meaning">Character: {char}</div>\n'
            html += f'            </div>\n'

    html += '        </div>\n'
    html += '    </div>\n'

    html += """
    <div class="intro" style="margin-top: 40px;">
        <h3>Symbol Variations</h3>
        <p>Notice how each symbol is unique due to different combinations of:</p>
        <ul>
            <li>Primary line orientation (vertical vs horizontal)</li>
            <li>Number and position of extensions (start, middle, end)</li>
            <li>Extension angles (perpendicular 90° or diagonal ±45°)</li>
            <li>Extension sides (left, right, or both)</li>
        </ul>
        <p>This creates 676+ unique geometric patterns for the complete bigram alphabet.</p>
    </div>

</body>
</html>
"""

    # Write to file
    output_file = "symbol_reference.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Symbol reference created: {output_file}")
    print(f"Total symbols generated: {len(symbols)}")
    print(f"Open {output_file} in your web browser to view the symbols")

    return output_file


if __name__ == '__main__':
    generate_symbol_reference_html()
