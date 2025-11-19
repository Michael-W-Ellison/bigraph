# Quick Start Guide - Bigraph Cryptography System

## Installation

No installation required! Just Python 3.7+ with Tkinter (included in most Python installations).

## Running the Application

```bash
python main.py
```

This launches the GUI application.

## 5-Minute Tutorial

### Step 1: Generate a Key

1. Click the **Key Management** tab
2. Enter a recipient name (e.g., "Alice")
3. Click **Generate Key**
4. Your key is automatically saved!

### Step 2: Encode a Message

1. Click the **Encode Message** tab
2. Select your key from the dropdown and click **Load Key**
3. Type your message in the input box:
   ```
   HELLO WORLD THIS IS A SECRET MESSAGE
   ```
4. Click **Encode Message**
5. The encoded message appears as a list of numbers
6. Click **Save Encoded Message** to save to a file

### Step 3: Decode a Message

1. Click the **Decode Message** tab
2. Select the same key and click **Load Key**
3. Paste the encoded number list or click **Load Encoded File**
4. Click **Decode Message**
5. The original message appears!

### Step 4: View Symbols

1. Click the **Symbol Viewer** tab
2. Select a key and click **Load Key**
3. View the symbol mappings

## Command Line Usage

```python
from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder

# Generate key
km = KeyManager()
key = km.generate_key("Alice", seed=42)

# Encode
encoder = BigramEncoder(key)
encoded = encoder.encode("HELLO WORLD")
print(encoded)

# Decode
decoder = BigramDecoder(key)
decoded = decoder.decode(encoded)
print(decoded)  # HELLO WORLD
```

## Key Features to Try

### 1. Mathematical Expressions
```python
encoder.encode_math_expression("2 * 3")  # Multiplication
encoder.encode_math_expression("6 / 2")  # Division
```

### 2. Multiple Sentences
Messages with periods are split into sentences with special markers.

### 3. Single Letters
'A' and 'I' use rotating symbols to prevent patterns.

### 4. Odd-Length Words
Words with odd numbers of letters use special partial markers.

## Tips

- **Keep keys safe**: The key is required to decode messages
- **Unique keys**: Generate a different key for each person
- **Share keys securely**: Send keys through a different channel than messages
- **Backup keys**: Export keys to backup files
- **Use seeds**: Reproducible keys with the same seed

## Examples

See `examples/example_usage.py` for comprehensive examples:
```bash
python examples/example_usage.py
```

## Testing

Verify everything works:
```bash
python test_basic.py
```

## Need Help?

- **README.md**: Complete documentation
- **docs/TECHNICAL.md**: Technical details and algorithms
- **examples/**: Working code examples

## Common Issues

**GUI won't start**: Make sure Tkinter is installed
```bash
python -m tkinter  # Should open a test window
```

**Keys not showing**: Check that the `keys/` directory exists

**Decoding fails**: Make sure you're using the same key that was used to encode

## Next Steps

1. Generate keys for different people
2. Try encoding various types of messages
3. Experiment with mathematical expressions
4. Export and import keys
5. Save and load encoded messages

Enjoy using the Bigraph Cryptography System!
