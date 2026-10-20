"""
Security helpers for the Bigraph Cryptography System

- Key files are encrypted with a password: AES-256-GCM with a key derived from
  the password by scrypt. GCM also detects a wrong password or a changed file.
- Key files and their folder are created so only the current user can read
  them, in a per-user data folder rather than the current directory.
- Saved messages carry an HMAC-SHA256 check code made with a secret in the
  key, so a changed message is detected when it is read.
- Key files kept on this computer have a second layer of encryption whose key
  is held only in the OS key store, so deleting that secret makes the file
  (and any old copy of it) unreadable even with the password.
- Messages can carry an encrypted control block (a replacement key and
  deletion instructions), encrypted with a key derived from the shared check
  secret rather than with the symbol cipher.
"""

import base64
import hashlib
import hmac
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

KEY_FILE_FORMAT = 'bigraph-key'
KEY_FILE_VERSION = 2

# scrypt cost: about 32 MB of memory and a fraction of a second per password
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1

MIN_PASSWORD_LENGTH = 8

MESSAGE_HEADER = 'BIGRAPH-MESSAGE 1'
MESSAGE_HEADER_V2 = 'BIGRAPH-MESSAGE 2'


class KeyFileError(Exception):
    """A key file cannot be read"""


class PasswordRequiredError(KeyFileError):
    """The key file is encrypted and no password was given"""


class WrongPasswordError(KeyFileError):
    """The password is wrong, or the key file was changed"""


class KeyDestroyedError(KeyFileError):
    """The key file's secret in the OS key store has been deleted, so the key is gone"""


class MessageIntegrityError(Exception):
    """A message's check code does not match, so the message was changed"""


# ---------------------------------------------------------------------------
# Private files
# ---------------------------------------------------------------------------

def default_keys_directory() -> str:
    """Per-user folder for key files"""
    home = os.path.expanduser('~')
    if sys.platform.startswith('win'):
        base = os.environ.get('APPDATA') or os.path.join(home, 'AppData', 'Roaming')
        return os.path.join(base, 'Bigraph', 'keys')
    if sys.platform == 'darwin':
        return os.path.join(home, 'Library', 'Application Support', 'Bigraph', 'keys')
    base = os.environ.get('XDG_DATA_HOME') or os.path.join(home, '.local', 'share')
    return os.path.join(base, 'bigraph', 'keys')


def ensure_private_directory(path: str):
    """Create a folder that only the current user can open"""
    os.makedirs(path, mode=0o700, exist_ok=True)
    if os.name == 'posix':
        os.chmod(path, 0o700)


def shred_file(path: str):
    """
    Overwrite a file with random data, then remove it

    This is best effort: solid-state drives, copy-on-write file systems and
    backups can keep old copies. Data that must be unrecoverable is encrypted
    with a secret in the OS key store, and that secret is deleted first.
    """
    try:
        size = os.path.getsize(path)
        with open(path, 'r+b') as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    if os.path.exists(path):
        os.remove(path)


def write_private_file(path: str, text: str):
    """Write a file that only the current user can read"""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    if os.name == 'posix':
        # The mode above only applies to new files
        os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(text)


# ---------------------------------------------------------------------------
# Encrypted key files
# ---------------------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode('ascii'))


def _derive_key(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(password.encode('utf-8'))


def _header_bytes(header: Dict) -> bytes:
    """The unencrypted part of a key file, which the encryption also protects"""
    return json.dumps(header, sort_keys=True, separators=(',', ':')).encode('utf-8')


def check_password(password: str):
    """Raise ValueError if a password is too short to protect a key"""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")


def encrypt_blob(secret: bytes, data: bytes, context: bytes) -> str:
    """AES-256-GCM encrypt data; the result is base64 text holding the nonce and ciphertext"""
    nonce = os.urandom(12)
    return _b64(nonce + AESGCM(secret).encrypt(nonce, data, context))


def decrypt_blob(secret: bytes, text: str, context: bytes) -> bytes:
    """Decrypt encrypt_blob output; raises InvalidTag if the secret or data is wrong"""
    raw = _unb64(text)
    return AESGCM(secret).decrypt(raw[:12], raw[12:], context)


def encrypt_key_file(data: Dict, password: str, created: str, security_version: int,
                     local_secret: Optional[bytes] = None, local_name: Optional[str] = None,
                     key_id: Optional[str] = None, creator_id: Optional[str] = None) -> str:
    """
    Encrypt key data with a password

    Args:
        data: Key data to protect
        password: Password for the key file
        created: Creation date, which stays readable so keys can be listed
        security_version: The key's security version, which stays readable so
            outdated keys can be found without their passwords
        local_secret: For keys kept on this computer, a secret held in the OS
            key store; the key data is also encrypted with it
        local_name: Name of local_secret in the OS key store
        key_id, creator_id: The key's random ID and its creator's random ID,
            which stay readable so old keys can be found and deleted without
            their passwords

    Returns:
        Text of the key file
    """
    check_password(password)
    salt = os.urandom(16)
    nonce = os.urandom(12)
    header = {
        'format': KEY_FILE_FORMAT,
        'version': KEY_FILE_VERSION,
        'created': created,
        'security_version': security_version,
        'local_secret': local_name,
        'key_id': key_id,
        'creator_id': creator_id,
        'kdf': {'name': 'scrypt', 'n': SCRYPT_N, 'r': SCRYPT_R, 'p': SCRYPT_P, 'salt': _b64(salt)},
        'cipher': 'AES-256-GCM',
    }
    secret = _derive_key(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    plaintext = json.dumps(data).encode('utf-8')
    if local_secret is not None:
        plaintext = json.dumps({'inner': encrypt_blob(local_secret, plaintext, b'bigraph-key-inner')}
                               ).encode('utf-8')
    ciphertext = AESGCM(secret).encrypt(nonce, plaintext, _header_bytes(header))
    return json.dumps({**header, 'nonce': _b64(nonce), 'ciphertext': _b64(ciphertext)}, indent=2)


def read_key_file_header(text: str) -> Optional[Dict]:
    """The readable header of an encrypted key file, or None for an older unencrypted file"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise KeyFileError(f"Not a key file: {e}") from e
    if isinstance(data, dict) and data.get('format') == KEY_FILE_FORMAT:
        return data
    return None


def decrypt_key_file(text: str, password: Optional[str], keystore=None) -> Dict:
    """
    Decrypt the key data in an encrypted key file

    Args:
        text: Key file text
        password: The file's password
        keystore: KeyStore holding the inner secret of keys kept on this computer

    Raises:
        PasswordRequiredError: no password was given
        WrongPasswordError: the password is wrong or the file was changed
        KeyDestroyedError: the file's secret in the OS key store was deleted
    """
    data = read_key_file_header(text)
    if data is None:
        raise KeyFileError("Not an encrypted key file")
    if data.get('version') != KEY_FILE_VERSION or data.get('cipher') != 'AES-256-GCM':
        raise KeyFileError("Unsupported key file version")
    if not password:
        raise PasswordRequiredError("This key file is protected by a password")

    header = {k: v for k, v in data.items() if k not in ('nonce', 'ciphertext')}
    kdf = header['kdf']
    secret = _derive_key(password, _unb64(kdf['salt']), kdf['n'], kdf['r'], kdf['p'])
    try:
        plaintext = AESGCM(secret).decrypt(_unb64(data['nonce']), _unb64(data['ciphertext']),
                                           _header_bytes(header))
    except InvalidTag as e:
        raise WrongPasswordError("Wrong password, or the key file has been changed") from e
    data = json.loads(plaintext)

    if header.get('local_secret'):
        if keystore is None:
            raise KeyFileError("This key file needs the OS key store to open")
        local_secret = keystore.get_secret(header['local_secret'])
        if local_secret is None:
            raise KeyDestroyedError("This key has been deleted; it can no longer be opened")
        try:
            data = json.loads(decrypt_blob(local_secret, data['inner'], b'bigraph-key-inner'))
        except InvalidTag as e:
            raise KeyFileError("The key file does not match its secret in the OS key store") from e
    return data


# ---------------------------------------------------------------------------
# Message check codes
# ---------------------------------------------------------------------------

def message_check_code(encoded: List[int], mac_key: str) -> str:
    """HMAC-SHA256 of an encoded message, using the key's check secret"""
    body = (MESSAGE_HEADER + '\n' + ','.join(map(str, encoded))).encode('utf-8')
    return hmac.new(bytes.fromhex(mac_key), body, hashlib.sha256).hexdigest()


def format_message(encoded: List[int], key: Dict) -> str:
    """
    Text of an encoded message, with a check code when the key has a check secret

    Format:
        BIGRAPH-MESSAGE 1
        12,-40,977,...
        CHECK 5f2c...
    """
    lines = [MESSAGE_HEADER, ','.join(map(str, encoded))]
    if key.get('mac_key'):
        lines.append('CHECK ' + message_check_code(encoded, key['mac_key']))
    return '\n'.join(lines) + '\n'


def parse_message(text: str, key: Dict) -> Tuple[List[int], bool]:
    """
    Read an encoded message and verify its check code

    Also reads the older format, a bare comma-separated list, which has no
    check code.

    Returns:
        (encoded symbol list, True if the check code was verified)

    Raises:
        MessageIntegrityError: the check code does not match, or a check code
            is missing from a message made with a key that has a check secret
        ValueError: the text is not an encoded message
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty message")

    if lines[0] == MESSAGE_HEADER_V2:
        if not key.get('mac_key'):
            raise MessageIntegrityError("This key has no check secret, so it cannot read this message")
        return open_message_v2(text, key)['encoded'], True

    if lines[0] != MESSAGE_HEADER:
        # Older format: numbers only
        numbers = ''.join(lines)
        return [int(x) for x in numbers.split(',') if x.strip()], False

    if len(lines) < 2:
        raise ValueError("Message has no symbols")
    encoded = [int(x) for x in lines[1].split(',') if x.strip()]
    check = next((line[len('CHECK '):] for line in lines[2:] if line.startswith('CHECK ')), None)

    if check is None:
        if key.get('mac_key'):
            raise MessageIntegrityError("The message has no check code, so it may have been changed")
        return encoded, False
    if not key.get('mac_key'):
        return encoded, False
    if not hmac.compare_digest(check, message_check_code(encoded, key['mac_key'])):
        raise MessageIntegrityError("The message's check code does not match; it has been changed "
                                    "or was made with a different key")
    return encoded, True


# ---------------------------------------------------------------------------
# Messages with an ID, retention and a control block (format 2)
# ---------------------------------------------------------------------------

def control_key(mac_key: str) -> bytes:
    """Key for control blocks, derived from a key's check secret"""
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                info=b'bigraph-control').derive(bytes.fromhex(mac_key))


def format_message_v2(encoded: List[int], key: Dict, message_id: str, sent: str,
                      retain_days: int, control: Optional[Dict] = None) -> str:
    """
    Text of a message with its ID, sending time, retention and control block

    Format:
        BIGRAPH-MESSAGE 2
        ID <message ID>
        KEY <key ID>
        SENT <time sent, ISO 8601>
        RETAIN <days the recipient keeps it>
        SYMBOLS 12,-40,977,...
        CONTROL <encrypted control block>   (when there is one)
        CHECK <HMAC-SHA256 of all lines above>
    """
    lines = [MESSAGE_HEADER_V2, f'ID {message_id}', f"KEY {key['key_id']}", f'SENT {sent}',
             f'RETAIN {int(retain_days)}', 'SYMBOLS ' + ','.join(map(str, encoded))]
    if control:
        context = ('\n'.join(lines)).encode('utf-8')
        lines.append('CONTROL ' + encrypt_blob(control_key(key['mac_key']),
                                               json.dumps(control).encode('utf-8'), context))
    body = '\n'.join(lines).encode('utf-8')
    lines.append('CHECK ' + hmac.new(bytes.fromhex(key['mac_key']), body, hashlib.sha256).hexdigest())
    return '\n'.join(lines) + '\n'


def message_fields(text: str) -> Dict:
    """
    The readable fields of a format 2 message, without checking it

    Used to find which key a message needs. Raises ValueError if the text is
    not a format 2 message.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines or lines[0] != MESSAGE_HEADER_V2:
        raise ValueError("Not a format 2 message")
    fields = {}
    for line in lines[1:]:
        name, _, value = line.partition(' ')
        fields[name] = value
    for name in ('ID', 'KEY', 'SENT', 'RETAIN', 'SYMBOLS', 'CHECK'):
        if name not in fields:
            raise MessageIntegrityError(f"The message has no {name} line, so it may have been changed")
    return fields


def open_message_v2(text: str, key: Dict) -> Dict:
    """
    Verify a format 2 message and decrypt its control block

    Returns:
        {'id', 'key_id', 'sent', 'retain_days', 'encoded', 'control'}

    Raises:
        MessageIntegrityError: the check code does not match
    """
    fields = message_fields(text)
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    body_lines = [line for line in lines if not line.startswith('CHECK ')]
    body = '\n'.join(body_lines).encode('utf-8')
    expected = hmac.new(bytes.fromhex(key['mac_key']), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(fields['CHECK'], expected):
        raise MessageIntegrityError("The message's check code does not match; it has been changed "
                                    "or was made with a different key")
    control = None
    if 'CONTROL' in fields:
        context = '\n'.join(line for line in body_lines if not line.startswith('CONTROL ')).encode('utf-8')
        control = json.loads(decrypt_blob(control_key(key['mac_key']), fields['CONTROL'], context))
    return {
        'id': fields['ID'],
        'key_id': fields['KEY'],
        'sent': fields['SENT'],
        'retain_days': int(fields['RETAIN']),
        'encoded': [int(x) for x in fields['SYMBOLS'].split(',') if x.strip()],
        'control': control,
    }
