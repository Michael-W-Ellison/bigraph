"""
OS key store access for the Bigraph Cryptography System

Secrets that must be destroyable are kept here instead of in files: the key
for each stored message, the inner encryption key of each key file, and the
key for the local state file. Deleting a secret from the OS key store
(Windows Credential Manager, macOS Keychain, Linux Secret Service) makes the
data it protects unreadable, including any copies of that data left on disk,
even to someone who knows the user's password.
"""

import base64
import os

import keyring
import keyring.errors

SERVICE = 'bigraph'


class KeyStoreUnavailableError(Exception):
    """No usable OS key store is installed"""


class KeyStore:
    """Named 256-bit secrets in the OS key store"""

    def __init__(self, service: str = SERVICE):
        self.service = service

    def check_available(self):
        """Raise KeyStoreUnavailableError if there is no usable OS key store"""
        backend = keyring.get_keyring()
        priority = getattr(backend, 'priority', 0)
        module = type(backend).__module__
        if priority <= 0 or module.startswith(('keyring.backends.fail', 'keyring.backends.null')):
            raise KeyStoreUnavailableError(
                "No OS key store is available. Messages and keys are only kept when one is: "
                "Windows Credential Manager, macOS Keychain, or a Secret Service such as "
                "GNOME Keyring or KWallet on Linux.")

    def create_secret(self, name: str) -> bytes:
        """Make a new random 256-bit secret and store it"""
        self.check_available()
        secret = os.urandom(32)
        keyring.set_password(self.service, name, base64.b64encode(secret).decode('ascii'))
        return secret

    def get_secret(self, name: str):
        """The stored secret, or None if it does not exist (for example, was deleted)"""
        self.check_available()
        value = keyring.get_password(self.service, name)
        return base64.b64decode(value) if value else None

    def delete_secret(self, name: str):
        """Delete a secret; deleting one that does not exist is not an error"""
        self.check_available()
        try:
            keyring.delete_password(self.service, name)
        except keyring.errors.PasswordDeleteError:
            pass


class MemoryKeyStore(KeyStore):
    """
    Secrets kept in memory, for tests and demonstrations

    Secrets are lost when the program exits, so keys and messages saved with
    it cannot be opened later, and it gives no guarantee about deletion.
    """

    def __init__(self):
        super().__init__()
        self.secrets = {}

    def check_available(self):
        pass

    def create_secret(self, name: str) -> bytes:
        self.secrets[name] = os.urandom(32)
        return self.secrets[name]

    def get_secret(self, name: str):
        return self.secrets.get(name)

    def delete_secret(self, name: str):
        self.secrets.pop(name, None)
