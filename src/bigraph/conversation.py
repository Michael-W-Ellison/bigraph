"""
Conversations for the Bigraph Cryptography System

Ties keys, messages and deletion together:

- Sent and received messages are kept in an encrypted MessageStore until they
  expire. The sender sets how long the recipient keeps each message (30 days
  by default).
- Each person sends with their own key. When a key has written
  KEY_WORD_LIMIT words or is KEY_MAX_AGE_DAYS old, the next message replaces
  it: a new key is made and travels to the recipient inside the message's
  control block, which is encrypted with AES-GCM under a secret only the two
  key holders share (not with the symbol cipher).
- The sender controls deletion. When the sender deletes a sent message, or
  an old key of theirs is deleted, the next message tells the recipient's
  program to delete its copy. A program only accepts deletion instructions
  for messages and keys that belong to the sender of the message.
- A replaced key is deleted once no stored message uses it.
"""

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .constants import KEY_WORD_LIMIT, KEY_MAX_AGE_DAYS, DEFAULT_RETENTION_DAYS
from .decoder import BigramDecoder
from .encoder import BigramEncoder
from .key_manager import KeyManager
from .security import (format_message_v2, open_message_v2, message_fields, parse_message,
                       encrypt_blob, decrypt_blob, write_private_file, ensure_private_directory,
                       MESSAGE_HEADER_V2)
from .store import MessageStore

STATE_CONTEXT = b'bigraph-conversation-state'
STATE_SECRET = 'conversation-state'


class ConversationError(Exception):
    """A message cannot be sent or received"""


class ConversationManager:
    """Sends and receives stored messages, and replaces and deletes keys"""

    def __init__(self, key_manager: KeyManager, store: Optional[MessageStore] = None):
        self.km = key_manager
        self.store = store or MessageStore(keystore=key_manager.keystore)
        self.state_path = os.path.join(self.store.directory, 'state.enc')

    # -- state -------------------------------------------------------------

    def _empty_state(self) -> Dict:
        return {
            'usage': {},      # key ID -> words written with it
            'replaced': {},   # old key ID -> new key ID
            'recipient': {},  # own key ID -> recipient name
            'pending': {},    # recipient name -> {'messages': [...], 'keys': [...]}
        }

    def load_state(self) -> Dict:
        """Local state, encrypted with a secret in the OS key store"""
        if not os.path.exists(self.state_path):
            return self._empty_state()
        secret = self.km.keystore.get_secret(STATE_SECRET)
        if secret is None:
            return self._empty_state()
        with open(self.state_path, 'r') as f:
            return json.loads(decrypt_blob(secret, f.read(), STATE_CONTEXT))

    def save_state(self, state: Dict):
        ensure_private_directory(self.store.directory)
        secret = self.km.keystore.get_secret(STATE_SECRET) or self.km.keystore.create_secret(STATE_SECRET)
        write_private_file(self.state_path, encrypt_blob(secret, json.dumps(state).encode('utf-8'),
                                                         STATE_CONTEXT))

    @staticmethod
    def _pending(state: Dict, recipient: str) -> Dict:
        return state['pending'].setdefault(recipient, {'messages': [], 'keys': []})

    # -- key replacement ---------------------------------------------------

    def needs_replacement(self, key: Dict, words: int = 0, now: Optional[datetime] = None) -> bool:
        """True if writing `words` more words would make the key too risky to keep using"""
        now = now or datetime.now()
        used = self.load_state()['usage'].get(key['key_id'], 0)
        created = datetime.fromisoformat(key['created'])
        return used + words > KEY_WORD_LIMIT or now - created > timedelta(days=KEY_MAX_AGE_DAYS)

    # -- sending -----------------------------------------------------------

    def send(self, key: Dict, plaintext: str, retain_days: int = DEFAULT_RETENTION_DAYS,
             now: Optional[datetime] = None) -> Dict:
        """
        Encode and store a message

        If the key is due for replacement, a new key is made, saved with the
        old key's password, and carried in this message's control block. Use
        the returned 'key' for the next message.

        Args:
            key: The sender's own key, loaded with its password
            plaintext: Message to send
            retain_days: Days the recipient keeps the message
            now: Current time (for tests)

        Returns:
            {'text': message text, 'key': key to use next, 'new_key': new key or None}
        """
        now = now or datetime.now()
        allowed, reason = self.km.can_encode(key)
        if not allowed:
            raise ConversationError(reason)
        if not key.get('mac_key') or not key.get('key_id'):
            raise ConversationError("This key cannot carry stored messages; create a new key.")

        state = self.load_state()
        recipient = key.get('recipient', '')
        state['recipient'][key['key_id']] = recipient
        pending = self._pending(state, recipient)

        control = {}
        if pending['messages']:
            control['delete_messages'] = list(pending['messages'])
        if pending['keys']:
            control['delete_keys'] = list(pending['keys'])

        words = len(plaintext.split())
        new_key = None
        if self.needs_replacement(key, words, now):
            password = key.get('_password')
            if not password:
                raise ConversationError("The key's password is needed to save its replacement.")
            new_key = self.km.rotate_key(key)
            self.km.save_key(new_key, password)
            new_key['_password'] = password
            control['new_key'] = self.km._key_data(new_key)
            state['replaced'][key['key_id']] = new_key['key_id']
            state['recipient'][new_key['key_id']] = recipient

        encoded = BigramEncoder(key).encode(plaintext)
        message_id = secrets.token_hex(16)
        sent = now.isoformat(timespec='seconds')
        text = format_message_v2(encoded, key, message_id, sent, retain_days, control or None)

        state['usage'][key['key_id']] = state['usage'].get(key['key_id'], 0) + words
        state['pending'][recipient] = {'messages': [], 'keys': []}
        self.save_state(state)

        self.store.add({
            'id': message_id, 'direction': 'sent', 'partner': recipient,
            'sender_id': key.get('creator_id'), 'key_id': key['key_id'], 'sent': sent,
            'expires': (now + timedelta(days=retain_days)).isoformat(timespec='seconds'),
            'message': text, 'plaintext': BigramDecoder(key).decode(encoded),
        })
        self.cleanup(now)
        return {'text': text, 'key': new_key or key, 'new_key': new_key}

    # -- receiving ---------------------------------------------------------

    @staticmethod
    def message_key_id(text: str) -> Optional[str]:
        """ID of the key a message needs, or None for older formats without one"""
        try:
            return message_fields(text)['KEY']
        except ValueError:
            return None

    def receive(self, text: str, key: Dict, now: Optional[datetime] = None) -> Dict:
        """
        Read and store a message, and apply its control block

        Args:
            text: Message text
            key: The sender's key (the copy the recipient holds), loaded with its password
            now: Current time (for tests)

        Returns:
            {'plaintext', 'verified', 'new_key' (or None), 'deleted_messages', 'deleted_keys'}
        """
        now = now or datetime.now()
        if not text.strip().startswith(MESSAGE_HEADER_V2):
            encoded, verified = parse_message(text, key)
            return {'plaintext': BigramDecoder(key).decode(encoded), 'verified': verified,
                    'new_key': None, 'deleted_messages': [], 'deleted_keys': []}

        # Check the key first, so a message for another key is not reported as changed
        if self.message_key_id(text) != key.get('key_id'):
            raise ConversationError("This message was written with a different key.")
        message = open_message_v2(text, key)
        plaintext = BigramDecoder(key).decode(message['encoded'])
        sender_id = key.get('creator_id')
        control = message['control'] or {}
        state = self.load_state()

        new_key = None
        if 'new_key' in control:
            new_key = self.km.key_from_data(dict(control['new_key']))
            if new_key.get('creator_id') != sender_id:
                raise ConversationError("The message carries a replacement key from someone else.")
            password = key.get('_password')
            if not password:
                raise ConversationError("The key's password is needed to save the sender's new key.")
            if not any(k['key_id'] == new_key['key_id'] for k in self.km.list_keys()):
                self.km.save_key(new_key, password)
            new_key['_password'] = password
            state['replaced'][key['key_id']] = new_key['key_id']

        # The sender controls deletion of their own messages and keys
        deleted_messages = []
        for message_id in control.get('delete_messages', []):
            record = self.store.get(message_id)
            if record and record['direction'] == 'received' and record['sender_id'] == sender_id:
                self.store.delete(message_id)
                deleted_messages.append(message_id)
        deleted_keys = []
        for info in self.km.list_keys():
            if (info['key_id'] in control.get('delete_keys', []) and info['key_id'] != key['key_id']
                    and info['creator_id'] == sender_id):
                self.km.delete_key(info['filepath'])
                deleted_keys.append(info['key_id'])
        self.save_state(state)

        sent = datetime.fromisoformat(message['sent'])
        self.store.add({
            'id': message['id'], 'direction': 'received', 'partner': key.get('sender', ''),
            'sender_id': sender_id, 'key_id': key['key_id'], 'sent': message['sent'],
            'expires': (sent + timedelta(days=message['retain_days'])).isoformat(timespec='seconds'),
            'message': text, 'plaintext': plaintext,
        })
        self.cleanup(now)
        return {'plaintext': plaintext, 'verified': True, 'new_key': new_key,
                'deleted_messages': deleted_messages, 'deleted_keys': deleted_keys}

    # -- deletion ----------------------------------------------------------

    def delete_message(self, message_id: str):
        """
        Delete a stored message

        For a message this user sent, the next message to that recipient also
        tells the recipient's program to delete its copy.
        """
        record = self.store.get(message_id)
        self.store.delete(message_id)
        if record and record['direction'] == 'sent':
            state = self.load_state()
            self._pending(state, record['partner'])['messages'].append(message_id)
            self.save_state(state)
        self.cleanup()

    def delete_conversation(self, partner: str):
        """Delete every stored message with a partner (sent messages also from the partner)"""
        for record in self.store.records():
            if record['partner'] == partner:
                self.delete_message(record['id'])

    def cleanup(self, now: Optional[datetime] = None) -> Dict:
        """
        Delete expired messages, and replaced keys that no stored message uses

        When one of this user's own keys is deleted, the next message to its
        recipient tells the recipient's program to delete its copy.

        Returns:
            {'messages': deleted message IDs, 'keys': deleted key IDs}
        """
        deleted_messages = self.store.purge_expired(now)
        in_use = {r['key_id'] for r in self.store.records()}
        state = self.load_state()
        own_id = self.km.load_profile()['user_id']
        deleted_keys = []
        for info in self.km.list_keys():
            key_id = info['key_id']
            if key_id and key_id in state['replaced'] and key_id not in in_use:
                self.km.delete_key(info['filepath'])
                deleted_keys.append(key_id)
                if info['creator_id'] == own_id and key_id in state['recipient']:
                    self._pending(state, state['recipient'][key_id])['keys'].append(key_id)
        if deleted_keys or deleted_messages:
            for key_id in deleted_keys:
                state['usage'].pop(key_id, None)
            self.save_state(state)
        return {'messages': deleted_messages, 'keys': deleted_keys}

    def records(self, partner: Optional[str] = None) -> List[Dict]:
        """Stored messages, optionally only those with one partner"""
        return [r for r in self.store.records() if partner is None or r['partner'] == partner]
