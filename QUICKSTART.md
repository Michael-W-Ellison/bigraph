# Quick Start Guide - Bigraph Cryptography System

## Installation

Download the app for your system from the project's Releases page. No Python
is needed.

| System | File | To run |
|---|---|---|
| Windows (64-bit) | `Bigraph-windows-x86_64.zip` | Unzip, then double-click `Bigraph.exe` |
| macOS (Apple Silicon) | `Bigraph-macos-arm64.zip` | Unzip, then open `Bigraph.app` |
| Linux (x86-64) | `Bigraph-linux-x86_64.tar.gz` | `tar -xzf Bigraph-linux-x86_64.tar.gz` then `./Bigraph` |

The apps are not signed, so the first time you open one:

- **Windows** may show "Windows protected your PC": click **More info**, then **Run anyway**.
- **macOS** may say the app "cannot be opened": right-click (or Control-click) the app, choose **Open**, then **Open** again. Or open **System Settings > Privacy & Security** and click **Open Anyway**.
- **Linux**: if the file will not run, make it executable with `chmod +x Bigraph`.

The program keeps the secrets that make deleted messages unrecoverable in your
system's key store. Windows and macOS have one built in. On Linux you need a
desktop key store running, such as GNOME Keyring or KWallet; most desktop
installations include one.

To check that everything works without opening a window, run the app with
`--self-test`.

### Running from source

With Python 3.8 or newer (and Tkinter, which on Linux may be a separate
package such as `python3-tk`):

```bash
pip install -r requirements.txt
python main.py
```

To build the apps yourself, see `docs/BUILDING.md`.

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

# Generate a key and save it, encrypted with a password
km = KeyManager()
key = km.generate_key("Alice")
path = km.save_key(key, "a long password")
key = km.load_key(path, "a long password")

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
encoder.encode_math_expression("2 + 3")  # Addition
encoder.encode_math_expression("5 - 1")  # Subtraction
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

- **Keep keys safe**: The key is required to decode messages. Key files are encrypted with a password and readable only by your user account
- **Unique keys**: Generate a different key for each person. Each person sends with their own key and keeps a copy of their partner's key for reading
- **Keep each other's copies**: If you lose your keys, your partner can export copies of both keys back to you so you can read old messages
- **Replace outdated keys**: After a security update, outdated keys can only decode; load your own outdated key on the Encode tab to create its replacement and send the new copy to your partner
- **Share keys securely**: Export a copy with its own password, and give the file and the password through different channels (for example the password in person)
- **Change keys regularly**: An attacker who collects enough text written with one key, especially with guessable openings or signatures, can read much of it
- **Check messages**: Saved and copied messages include a check code; decoding reports a message that has been changed
- **Deletion is final**: Messages are kept for the time the sender chooses (30 days by default), then deleted so they cannot be recovered. Deleting a message you sent also deletes the recipient's copy when your next message reaches them. This needs an OS key store (Windows Credential Manager, macOS Keychain, or GNOME Keyring/KWallet on Linux), and cannot reach text you copy or save outside the program
- **Keys replace themselves**: After 1,000 words or 30 days, your next message carries a new key to your partner automatically
- **Backup keys**: Export keys to backup files
- **Don't use seeds for real keys**: A seed makes a key reproducible by anyone who knows or guesses it; use seeds only for testing

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
