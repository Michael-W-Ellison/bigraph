"""
Security helpers for the Bigraph Cryptography System

- Key files are encrypted with a password: AES-256-GCM with a key derived from
  the password by scrypt. GCM also detects a wrong password or a changed file.
- Key files and their folder are created so only the current user can read
  them, in a per-user data folder rather than the current directory.
- Saved messages carry an HMAC-SHA256 check code made with a secret in the
  key, so a changed message is detected when it is read.
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

KEY_FILE_FORMAT = 'bigraph-key'
KEY_FILE_VERSION = 2

# scrypt cost: about 32 MB of memory and a fraction of a second per password
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1

MIN_PASSWORD_LENGTH = 8

MESSAGE_HEADER = 'BIGRAPH-MESSAGE 1'


class KeyFileError(Exception):
    """A key file cannot be read"""


class PasswordRequiredError(KeyFileError):
    """The key file is encrypted and no password was given"""


class WrongPasswordError(KeyFileError):
    """The password is wrong, or the key file was changed"""


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


def encrypt_key_file(data: Dict, password: str, created: str, security_version: int) -> str:
    """
    Encrypt key data with a password

    Args:
        data: Key data to protect
        password: Password for the key file
        created: Creation date, which stays readable so keys can be listed
        security_version: The key's security version, which stays readable so
            outdated keys can be found without their passwords

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
        'kdf': {'name': 'scrypt', 'n': SCRYPT_N, 'r': SCRYPT_R, 'p': SCRYPT_P, 'salt': _b64(salt)},
        'cipher': 'AES-256-GCM',
    }
    secret = _derive_key(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    plaintext = json.dumps(data).encode('utf-8')
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


def decrypt_key_file(text: str, password: Optional[str]) -> Dict:
    """
    Decrypt the key data in an encrypted key file

    Raises:
        PasswordRequiredError: no password was given
        WrongPasswordError: the password is wrong or the file was changed
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
    return json.loads(plaintext)


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
