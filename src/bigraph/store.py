"""
Encrypted message store for the Bigraph Cryptography System

Each stored message is a file encrypted with its own random secret, which is
held only in the OS key store. Deleting a message deletes that secret first,
so the file and any copy of it left on disk (by a backup, a solid-state
drive, or a copy-on-write file system) can no longer be decrypted. The file is
then overwritten and removed.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from cryptography.exceptions import InvalidTag

from .keystore import KeyStore
from .security import (default_keys_directory, ensure_private_directory, write_private_file,
                       encrypt_blob, decrypt_blob, shred_file)

RECORD_CONTEXT = b'bigraph-message-record'


def default_messages_directory() -> str:
    """Per-user folder for stored messages, next to the keys folder"""
    return os.path.join(os.path.dirname(default_keys_directory()), 'messages')


class MessageStore:
    """
    Stored messages, each encrypted with its own secret

    A record is a dictionary with:
        id         message ID (from the message)
        direction  'sent' or 'received'
        partner    the other person's name
        sender_id  creator ID of the key the message was written with
        key_id     ID of that key
        sent       time sent (ISO 8601)
        expires    time the message is deleted (ISO 8601)
        message    the message text as sent
        plaintext  the decoded text
    """

    def __init__(self, directory: Optional[str] = None, keystore: Optional[KeyStore] = None):
        self.directory = directory or default_messages_directory()
        self.keystore = keystore or KeyStore()

    def _path(self, message_id: str) -> str:
        if not message_id or not all(c in '0123456789abcdef' for c in message_id):
            raise ValueError("Invalid message ID")
        return os.path.join(self.directory, f'{message_id}.msg')

    @staticmethod
    def _secret_name(message_id: str) -> str:
        return f'message:{message_id}'

    def add(self, record: Dict):
        """Store a message, replacing any stored message with the same ID"""
        self.keystore.check_available()
        path = self._path(record['id'])
        if os.path.exists(path):
            self.delete(record['id'])
        ensure_private_directory(self.directory)
        secret = self.keystore.create_secret(self._secret_name(record['id']))
        write_private_file(path, encrypt_blob(secret, json.dumps(record).encode('utf-8'), RECORD_CONTEXT))

    def get(self, message_id: str) -> Optional[Dict]:
        """A stored message, or None if it does not exist or has been deleted"""
        path = self._path(message_id)
        if not os.path.exists(path):
            return None
        secret = self.keystore.get_secret(self._secret_name(message_id))
        if secret is None:
            return None
        with open(path, 'r') as f:
            try:
                return json.loads(decrypt_blob(secret, f.read(), RECORD_CONTEXT))
            except (InvalidTag, ValueError):
                return None

    def records(self) -> List[Dict]:
        """All stored messages that can still be opened, oldest first"""
        if not os.path.isdir(self.directory):
            return []
        records = []
        for filename in os.listdir(self.directory):
            if filename.endswith('.msg'):
                record = self.get(filename[:-4])
                if record is not None:
                    records.append(record)
        return sorted(records, key=lambda r: r['sent'])

    def delete(self, message_id: str):
        """Delete a message so it cannot be recovered"""
        self.keystore.delete_secret(self._secret_name(message_id))
        path = self._path(message_id)
        if os.path.exists(path):
            shred_file(path)

    def purge_expired(self, now: Optional[datetime] = None) -> List[str]:
        """
        Delete messages past their expiry time, and files whose secret is gone

        Returns:
            IDs of the deleted messages
        """
        now = now or datetime.now()
        deleted = []
        if not os.path.isdir(self.directory):
            return deleted
        for filename in os.listdir(self.directory):
            if not filename.endswith('.msg'):
                continue
            message_id = filename[:-4]
            record = self.get(message_id)
            if record is None or datetime.fromisoformat(record['expires']) <= now:
                self.delete(message_id)
                deleted.append(message_id)
        return deleted
