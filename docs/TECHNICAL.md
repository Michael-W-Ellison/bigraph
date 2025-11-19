# Technical Documentation - Bigraph Cryptography System

## Algorithm Overview

The Bigraph Cryptography System is a substitution cipher that operates on bigrams (two-letter combinations) rather than individual letters, providing 676 possible combinations (26×26) compared to 26 in a simple substitution cipher.

## Core Components

### 1. Symbol Generation

**File**: `src/bigraph/symbols.py`

Symbols are generated as SVG graphics with the following structure:

- **Primary Line**: Either vertical or horizontal (100x100 viewBox)
- **Extensions**: Lines extending from the primary line at:
  - Start position (top for vertical, left for horizontal)
  - Middle position
  - End position (bottom for vertical, right for horizontal)
- **Extension Angles**: 90° (perpendicular) or ±45° (diagonal)
- **Extension Sides**: Left, right, or both

**Generation Process**:
1. Systematic generation of configurations
2. Random variations if more symbols needed
3. Each symbol is uniquely identified by its configuration
4. Total symbols needed: ~718 (676 bigrams + numbers + special chars)

### 2. Key Management

**File**: `src/bigraph/key_manager.py`

**Key Structure**:
```json
{
  "recipient": "Alice",
  "created": "2024-01-01T12:00:00",
  "seed": 42,
  "symbol_to_meaning": {
    "0": "AA",
    "1": "AB",
    "2": "AC",
    ...
  },
  "meaning_to_symbol": {
    "AA": 0,
    "AB": 1,
    "AC": 2,
    ...
  },
  "symbols_svg": [
    "<svg>...</svg>",
    ...
  ],
  "version": "1.0"
}
```

**Key Components**:
- **Bigrams**: AA-ZZ (676 total)
- **Numbers**: 0-9 (positive for multiplication)
- **Negative Numbers**: -0 through -9 (for division)
- **Special Characters**: !@#$%^&*()=<>?
- **Space Markers**: JQ, QG, QK, QY, QZ, WQ, WZ
- **MULDIV Marker**: Separates operands in math expressions

**Random Mapping**:
- Uses Python's `random.shuffle()` with optional seed
- Seed enables reproducible key generation
- Each recipient should have unique seed/key

### 3. Encoding Engine

**File**: `src/bigraph/encoder.py`

**Encoding Rules**:

#### 3.1 Text Preprocessing
```python
text → UPPERCASE → words
```

#### 3.2 Word Encoding

**Even-length words**:
```
HELLO → HE, LL, O (odd, so special handling)
WORLD → WO, RL, D (odd, so special handling)
TEST → TE, ST (even, straightforward)
```

**Odd-length words**:
- Encode all complete bigrams
- For final letter:
  1. Search earlier in word for same letter
  2. If found: Reuse that bigram with partial marker
  3. If not found: Create bigram `{letter}A` with partial marker

**Partial Markers**:
- Encoded as offset from symbol index
- Negative index (-symbol - 1): Use first letter of bigram
- High offset (+10000): Use second letter of bigram

#### 3.3 Single Letter Words

**'A' Rotation**:
```
1st A → |AA (first letter only)
2nd A → |AB (first letter only)
3rd A → |AC (first letter only)
...
```

**'I' Rotation**:
```
1st I → |IA (first letter only)
2nd I → |IB (first letter only)
3rd I → |IC (first letter only)
...
```

#### 3.4 Space Markers

Uses rare bigrams in rotation:
```
Space 1 → JQ
Space 2 → QG
Space 3 → QK
Space 4 → QY
Space 5 → QZ
Space 6 → WQ
Space 7 → WZ
Space 8 → JQ (wraps around)
...
```

#### 3.5 Sentence Endings

Two consecutive space markers:
```
Sentence end → [space_marker, space_marker]
Example: [JQ, QG]
```

#### 3.6 Number Encoding

**Integers**:
```
2024 → [symbol(2), symbol(0), symbol(2), symbol(4)]
```

**Mathematical Expressions**:
```
Multiplication: 2 * 3 → [symbol(2), symbol(MULDIV), symbol(3)]
Division: 6 / 2 → [symbol(6), symbol(MULDIV), symbol(-2)]
```

- Positive numbers after MULDIV = multiplication
- Negative numbers after MULDIV = division

### 4. Decoding Engine

**File**: `src/bigraph/decoder.py`

**Decoding Process**:

1. **Read symbol index**
2. **Check for partial markers**:
   - If index < 0: Extract first letter of bigram
   - If index >= 10000: Extract second letter of bigram
   - Otherwise: Use full bigram
3. **Check for space markers**:
   - If SPACE_* type: Check next symbol
   - If next is also SPACE_*: Sentence ending (". ")
   - Otherwise: Regular space (" ")
4. **Check for numbers**:
   - NUM_X: Regular digit
   - NUM_NEG_X: Digit for division
5. **Check for MULDIV**:
   - Look ahead to determine operation
   - If next is negative: " / "
   - Otherwise: " * "
6. **Regular bigrams**: Output as-is

## File Formats

### Encoded Message Format

Simple comma-separated integers:
```
298,115,-344,614,111,253,-127
```

- Positive numbers: Symbol indices or high-offset partial markers
- Negative numbers: Partial marker indices (decode as: symbol = -n - 1)
- High numbers (>10000): Partial marker after (decode as: symbol = n - 10000)

### Key File Format

JSON with specific structure:
- UTF-8 encoding
- Pretty-printed with 2-space indent
- All SVG symbols embedded as strings

## Security Analysis

### Strengths
1. **Large keyspace**: 676 bigrams vs 26 letters
2. **Random symbol mapping**: Each key is unique
3. **Pattern obfuscation**:
   - Rotating space markers
   - Rotating single letters
   - Final letter optimization

### Weaknesses
1. **Substitution cipher**: Vulnerable to frequency analysis
2. **No key exchange protocol**: Keys must be shared out-of-band
3. **Deterministic encoding**: Same plaintext with same key produces same ciphertext
4. **Pattern leakage**:
   - Word boundaries visible (space markers)
   - Sentence structure preserved
   - Number sequences recognizable

### Recommended Use
- Educational purposes
- Puzzle creation
- Non-sensitive communications
- **NOT for**: Banking, passwords, sensitive data

## Performance Characteristics

### Time Complexity
- **Key Generation**: O(n log n) where n = number of symbols (shuffling)
- **Encoding**: O(m) where m = message length
- **Decoding**: O(k) where k = encoded length

### Space Complexity
- **Key Storage**: ~500KB per key (SVG symbols)
- **Encoded Message**: ~5-7 bytes per character (varies with compression)

## Extension Points

### Adding New Symbol Types

1. Update `constants.py` with new mappings
2. Modify `key_manager.py` to include in key generation
3. Update encoder/decoder to handle new types

### Custom Symbol Generation

Modify `SymbolGenerator._create_svg_symbol()` to implement custom designs.

### Alternative Encoding Schemes

Create new encoder class inheriting from `BigramEncoder` and override:
- `_encode_word()`
- `_encode_final_letter()`
- Space marker logic

## API Reference

### KeyManager

```python
generate_key(recipient: str, seed: int = None) -> Dict
save_key(key: Dict) -> str
load_key(filepath: str) -> Dict
list_keys() -> List[Dict]
get_symbol_for_bigram(key: Dict, bigram: str) -> Optional[int]
get_symbol_for_number(key: Dict, number: int) -> Optional[int]
```

### BigramEncoder

```python
__init__(key: Dict)
encode(plaintext: str) -> List[int]
encode_math_expression(expression: str) -> List[int]
save_encoded_message(encoded: List[int], filepath: str)
```

### BigramDecoder

```python
__init__(key: Dict)
decode(encoded: List[int]) -> str
decode_with_symbols(encoded: List[int]) -> List[Dict]
load_and_decode(filepath: str) -> str
```

### SymbolGenerator

```python
__init__(seed: int = None)
generate_all_symbols() -> List[str]
save_symbol_to_file(svg_content: str, filename: str)
```

## Testing Strategy

### Unit Tests
- Symbol generation uniqueness
- Key generation reproducibility
- Bigram mapping correctness
- Encoding rule compliance
- Decoding accuracy

### Integration Tests
- Full encode/decode cycle
- File I/O operations
- Key import/export

### Edge Cases
- Empty messages
- Single-letter words
- Odd/even length words
- Numbers and math expressions
- Special characters

## Future Improvements

1. **Compression**: Reduce encoded message size
2. **Error Detection**: Add checksums
3. **Encryption**: Add actual cryptographic layer
4. **Symbol Fonts**: Generate TTF/OTF fonts
5. **Image Export**: Render symbols as images
6. **Batch Processing**: Encode/decode multiple files
7. **Key Derivation**: Generate keys from passphrases
