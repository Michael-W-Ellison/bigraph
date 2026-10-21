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
- **Extension Angles**: 90° (perpendicular) or 45° (diagonal), with a
  diagonal slanting toward either end of the primary line
- **Extension Sides**: Left, right, or both (up, down, or both for horizontal),
  with at most one extension per side at each position
- **Extension Length**: About one third of the primary line. A diagonal at an
  end of the primary line that points away from the line is half length.
- **Touching**: Diagonals from neighbouring positions on the same side meet at
  their tips and form a closed triangle. Two diagonals at the same position
  that would form one straight line across the primary line are not used.

**Generation Process**:
1. All configurations are enumerated, grouped by number of extensions
2. Groups with fewer extensions are used first; when only part of a group is
   needed, that part is chosen at random using the key's symbol seed
3. Each symbol is uniquely identified by its configuration
4. Total symbols needed: 1,231 (676 bigrams + numbers + special chars + math
   operators + 150 common word symbols + 360 extra bigram symbols). This
   uses every shape with at most 4 extensions and part of the shapes with 5
   extensions.
5. Loading a saved key redraws its symbols from its symbol seed with the current
   generator, so keys saved by older versions do not use older symbols

### 2. Key Management

**File**: `src/bigraph/key_manager.py`

**Key Structure** (in memory):
```json
{
  "recipient": "Alice",
  "created": "2024-01-01T12:00:00",
  "seed": null,
  "symbol_seed": 283749027349872340987234098723409872341,
  "mac_key": "5f2c...",
  "symbol_to_meaning": {"0": "AA", "1": "WORD_THE_12", "2": "ALT_IN_3", ...},
  "meaning_to_symbol": {"AA": 0, ...},
  "symbols_svg": ["<svg>...</svg>", ...],
  "version": "2.0"
}
```

`meaning_to_symbol` and `symbols_svg` are rebuilt when a key is loaded, so
they are not stored. `mac_key` is a 256-bit secret for message check codes.

**Key Files**:

Key files are encrypted with a password (`src/bigraph/security.py`):

- AES-256-GCM, with the encryption key derived from the password by scrypt
  (N=2^15, r=8, p=1, random 16-byte salt). GCM also detects a wrong password
  or any change to the file, including its readable header.
- Only the format, version, creation date and encryption settings are
  readable without the password, so keys can be listed. The recipient and
  the symbol table are encrypted.
- Passwords must be at least 8 characters.
- Files get random names (`key_<16 hex digits>.key`), so the name reveals
  nothing about the recipient.
- The default folder is per-user: `~/.local/share/bigraph/keys` on Linux (or
  `$XDG_DATA_HOME/bigraph/keys`), `~/Library/Application Support/Bigraph/keys`
  on macOS, `%APPDATA%\Bigraph\keys` on Windows. It is created when the first
  key is saved, readable only by the current user (mode 700), and key files
  and exported copies are readable only by their owner (mode 600) on Linux and
  macOS.
- Older unencrypted key files still load; protect them by importing them
  again.

**Key Warnings**:

`KeyManager.key_warnings(key)` reports keys made before secure key
generation (from a 32-bit seed), keys made from a seed, keys made under an
older security version, keys stored without a password, and keys without a
check secret. The GUI shows these when a key is opened. The GUI no longer
offers seeded keys.

**Retired Keys (Decode Only)**:

A key is retired when it was made under an older security version
(`SECURITY_VERSION` in `constants.py`) or was loaded from a file without a
password. Retired keys still decode, so old messages stay readable, but
`BigramEncoder` refuses them with `RetiredKeyError`. Keys from before
security versions were recorded count as version 1 if they have a symbol
seed and a check secret, and version 0 otherwise.

**Security Updates**:

When a release changes how keys must be made, raise `SECURITY_VERSION`.
Each key file records its security version in the readable part of the
file, so outdated keys are found without their passwords:

- At startup the GUI lists how many keys are outdated.
- Loading one of your own outdated keys for encoding offers to create its
  replacement (`KeyManager.rotate_key`, same sender and recipient, with
  `replaces` set to the old key's ID) and to export the copy for the
  recipient. The old key is kept for decoding.
- A partner's outdated key can only decode; the partner has to send a
  replacement.

**Partner Copies (Escrow) and Recovery**:

Each person sends with their own key, and both people keep copies of both
keys:

1. Alice creates a key for messages she sends to Bob, and exports a
   password-protected copy for him (the GUI offers this right after the key
   is created). Bob imports it and uses it to read Alice's messages.
2. Bob does the same with his key for messages he sends to Alice.
3. If either loses their keys, the other exports copies of both keys back,
   and old messages can be read again.

Each key records `sender` (the creator's name), `recipient`, `key_id`, and
`creator_id`, the random ID in the local profile (`profile.json` in the keys
folder, readable only by the user). `KeyManager.is_own_key` compares
`creator_id` with the profile, so a recovered key is recognised as the user's
own if the profile still exists. `KeyManager.can_encode` allows encoding only
with the user's own, current keys; a partner's key can only decode. Keys from
before creators were recorded count as the user's own.

Because both people hold both keys, either one could write a message that
passes the check code of the other's key: check codes show a message was not
changed by an outsider, not which of the two wrote it.

**Stored Conversations and Deletion** (`conversation.py`, `store.py`, `keystore.py`):

- **OS key store.** Secrets that must be destroyable live only in the OS key
  store (Windows Credential Manager, macOS Keychain, or a Linux Secret
  Service such as GNOME Keyring or KWallet), through the `keyring` package.
  Without one, keys and messages are not saved at all
  (`KeyStoreUnavailableError`).
- **Key files** kept on this computer are encrypted with the password and
  with a second secret held only in the OS key store. `KeyManager.delete_key`
  deletes that secret first, so the file and any leftover copy of it cannot
  be opened even with the password (`KeyDestroyedError`), then overwrites and
  removes the file. Copies exported for a partner are password-only.
- **Messages.** `ConversationManager.send` and `receive` keep each sent and
  received message in a `MessageStore` file encrypted with its own secret in
  the OS key store. Deleting a message deletes its secret, then overwrites and
  removes the file.
- **Retention.** The sender sets how long the recipient keeps each message
  (`RETAIN` line, 30 days by default, `DEFAULT_RETENTION_DAYS`). Expired
  messages are deleted at startup and every hour while the GUI is open.
- **Automatic key replacement.** A key is replaced when it has written
  `KEY_WORD_LIMIT` (1,000) words or is `KEY_MAX_AGE_DAYS` (30) days old. The
  next message carries the new key in its control block, encrypted with
  AES-256-GCM under a key derived from the old key's check secret, so the
  symbol cipher never carries key material. The recipient's program saves the
  new key and uses it for the sender's later messages. A replacement key is
  accepted only if it has the same creator as the key that sent it.
- **Sender-controlled deletion.** When the sender deletes a message they sent,
  or one of their old keys is deleted, the next message to that recipient
  lists it in the control block, and the recipient's program deletes its
  copy. A program accepts these instructions only for messages and keys
  created by the sender of the message.
- **Unused keys.** A replaced key is deleted once no stored message uses it.
- **State.** Word counts per key, replacements and pending deletion
  instructions are kept in `state.enc` in the messages folder, encrypted with
  a secret in the OS key store.

Messages use format 2:
```
BIGRAPH-MESSAGE 2
ID <message ID>
KEY <key ID>
SENT <time sent>
RETAIN <days>
SYMBOLS 12,-40,977,...
CONTROL <encrypted control block>   (when there is one)
CHECK <HMAC-SHA256 of all lines above>
```

**Limits of deletion.** Deletion is final for data held by this program,
provided the OS key store really erases deleted secrets (key stores backed by
hardware, such as the macOS Secure Enclave or a TPM, are the most reliable).
It cannot reach:
- copies made outside the program: message text copied to the clipboard or
  saved to files, screenshots, printouts, or symbols written out by hand;
- the recipient's copy if the recipient never receives a later message from
  the sender, or uses a modified program that ignores deletion instructions;
- anyone who has captured the messages in transit and can break the symbol
  cipher, or who obtained a key before it was deleted.

**Message Check Codes**:

Saved and copied messages use this format:
```
BIGRAPH-MESSAGE 1
12,-40,977,...
CHECK <HMAC-SHA256 of the first two lines, using the key's mac_key>
```
Reading a message verifies the check code and raises `MessageIntegrityError`
if it does not match, or if it is missing from a message made with a key
that has a check secret. A bare list of numbers (the older format) still
reads, reported as unverified. A message written out by hand as symbols has
no check code.

**Key Components**:
- **Bigrams**: AA-ZZ (676 total)
- **Numbers**: 0-9 (positive for multiplication)
- **Negative Numbers**: -0 through -9 (for division)
- **Special Characters**: !@#$%^&*()=<>?
- **Math Operators**: + - / (`*` is a special character)
- **Space Markers**: JQ, QG, QK, QY, QZ, WQ, WZ
- **MULDIV Marker**: Separates operands in math expressions

**Random Mapping**:
- Without a seed, the mapping is shuffled with `secrets.SystemRandom`
  (the operating system's secure random source), and `symbol_seed` is a
  128-bit value from the same source that chooses the symbol drawings
- With a seed, the key is reproducible with `random.Random(seed)`; anyone who
  knows or guesses the seed can recreate the key, so seeds are for testing
  and examples only
- Keys saved before `symbol_seed` was added were created from a 32-bit seed
  and should be replaced

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
- Encode the final letter as a single letter (see 3.3)

**Partial Markers**:
- Drawn as a plain vertical line, which is reserved for this and is not a symbol
- Encoded as offset from symbol index
- Negative index (-symbol - 1): Use first letter of bigram
- High offset (+10000): Use second letter of bigram

#### 3.3 Common Words

The 100 most common English words (`COMMON_WORDS` in `constants.py`) have
their own symbols. Each word gets several, in proportion to how often it is
used: THE has 6, AND and OF 4 each, and the least common words 1. Each time a
common word appears, one of its symbols is chosen at random with the secure
random source, so each symbol is used about equally often and a word does not
look the same each time.

```
THE  → one of its 6 symbols
A    → one of its 3 symbols
```

`generate_key(word_symbol_budget=...)` sets the total number of word symbols
(default 150). A budget of 0 gives a key without word symbols, which spells
every word with bigrams.

#### 3.3.1 Common Bigrams

The 200 most frequent bigrams in spelled words (`COMMON_BIGRAMS` in
`constants.py`) get extra symbols, in proportion to how often they are used:
IN has 11 symbols in total, ER 9, TH 6. Each time a bigram is written, one of
its symbols is chosen at random with the secure random source, so a repeated
word does not look the same each time.

`generate_key(bigram_symbol_budget=...)` sets the number of extra symbols
(default 360). A budget of 0 gives every bigram one symbol.

The defaults (150 word symbols and 360 extra bigram symbols) keep keys to the
1,231 shapes with at most 3 extensions. `cryptanalysis/RESULTS.md` compares
this with larger budgets, which use busier shapes and resist the attacks for
longer; the shorter `KEY_WORD_LIMIT` makes up the difference.

#### 3.3.2 Single Letters

The final letter of an odd-length word that is not a common word, and
single-letter words that are not common words, are written as one letter of a
bigram, with the partial marker before it. Each letter cycles through its own
bigrams, so a repeated word keeps its pairs but changes its single letter:

```
CAT  → CA, |TA
CAT  → CA, |TB
CAT  → CA, |TC
X    → |XA
```

- Each letter has its own counter, shared by final letters and single-letter
  words, and the counters reset for each message
- After |EZ the cycle returns to |EA
- Even-length words have no single letters, so they are always written the
  same way (ROAD → RO, AD)

#### 3.4 Space Markers

Each space is one of 7 rare bigrams (JQ, QG, QK, QY, QZ, WQ, WZ), chosen at
random with the secure random source. A fixed rotation is not used, because
markers used in a strict cycle always alternate with each other, which lets
an attacker find them.

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
Addition: 2 + 3 → [symbol(2), symbol(+), symbol(3)]
Subtraction: 5 - 1 → [symbol(5), symbol(-), symbol(1)]
Multiplication: 2 * 3 → [symbol(2), symbol(MULDIV), symbol(3)]
Division: 6 / 2 → [symbol(6), symbol(MULDIV), symbol(-2)]
```

- Positive numbers after MULDIV = multiplication
- Negative numbers after MULDIV = division
- Other operators produce no symbols

#### 3.7 Special Characters

Special characters and math operators in text are encoded as their own
symbols. They split a word into segments, and each segment is encoded with
the normal word rules:
```
$5 → [symbol($), symbol(5)]
X+Y → [|XA, symbol(+), |YA]
```

- Sentence-ending `.`, `!` and `?` are represented by the sentence end marker
  and are not encoded as special characters
- Characters that are not letters, digits, special characters or math
  operators (for example `,` and `'`) are dropped

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
generate_key(recipient: str, seed: int = None, word_symbol_budget: int = 150,
             bigram_symbol_budget: int = 360) -> Dict
generate_key(..., sender_name: str = None) -> Dict
save_key(key: Dict, password: str) -> str
load_key(filepath: str, password: str = None) -> Dict
list_keys() -> List[Dict]
export_key(key: Dict, filepath: str, password: str)
import_key(filepath: str, password: str = None) -> Dict
key_warnings(key: Dict) -> List[str]
security_version(key: Dict) -> int
is_retired(key: Dict) -> bool
is_own_key(key: Dict) -> bool
can_encode(key: Dict) -> Tuple[bool, str]
rotate_key(old_key: Dict) -> Dict
load_profile() -> Dict
set_user_name(name: str) -> Dict
delete_key(filepath: str)
key_from_data(data: Dict) -> Dict
```

### ConversationManager

```python
__init__(key_manager: KeyManager, store: MessageStore = None)
send(key: Dict, plaintext: str, retain_days: int = 30) -> Dict
receive(text: str, key: Dict) -> Dict
message_key_id(text: str) -> Optional[str]
delete_message(message_id: str)
delete_conversation(partner: str)
cleanup() -> Dict
records(partner: str = None) -> List[Dict]
get_symbol_for_bigram(key: Dict, bigram: str) -> Optional[int]
get_symbol_for_number(key: Dict, number: int) -> Optional[int]
```

### BigramEncoder

```python
__init__(key: Dict)
encode(plaintext: str) -> List[int]
encode_math_expression(expression: str) -> List[int]
format_message(encoded: List[int]) -> str
save_encoded_message(encoded: List[int], filepath: str)
load_encoded_message(filepath: str) -> List[int]
```

### BigramDecoder

```python
__init__(key: Dict)
decode(encoded: List[int]) -> str
decode_with_symbols(encoded: List[int]) -> List[Dict]
read_message(text: str) -> Tuple[List[int], bool]
load_and_decode(filepath: str) -> str
```

### SymbolGenerator

```python
__init__(seed: int = None)
generate_all_symbols(count: int = TOTAL_SYMBOLS) -> List[str]
create_partial_marker_svg() -> str
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
