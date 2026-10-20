"""
Tests for stored conversations, automatic key replacement, and unrecoverable deletion
"""

import os
import shutil
import sys
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import bigraph.conversation as conversation
from bigraph.conversation import ConversationManager, ConversationError
from bigraph.key_manager import KeyManager
from bigraph.keystore import KeyStore, MemoryKeyStore, KeyStoreUnavailableError
from bigraph.security import KeyDestroyedError
from bigraph.store import MessageStore

PASSWORD = 'long password'
T0 = datetime(2026, 1, 1, 12, 0, 0)


class Person:
    """One user, with their own key store, keys, and messages"""

    def __init__(self, root, name):
        self.keystore = MemoryKeyStore()
        self.km = KeyManager(os.path.join(root, name, 'keys'), self.keystore)
        self.km.set_user_name(name)
        self.store = MessageStore(os.path.join(root, name, 'messages'), self.keystore)
        self.conv = ConversationManager(self.km, self.store)

    def new_key(self, recipient):
        key = self.km.generate_key(recipient)
        key['created'] = T0.isoformat()
        self.km.save_key(key, PASSWORD)
        key['_password'] = PASSWORD
        return key

    def give_copy(self, key, other, root):
        path = os.path.join(root, f"copy_{key['key_id']}.key")
        self.km.export_key(key, path, 'share password')
        copy = other.km.import_key(path, 'share password')
        other.km.save_key(copy, PASSWORD)
        copy['_password'] = PASSWORD
        os.remove(path)
        return copy


@pytest.fixture
def pair(tmp_path):
    alice, bob = Person(str(tmp_path), 'Alice'), Person(str(tmp_path), 'Bob')
    key = alice.new_key('Bob')
    copy = alice.give_copy(key, bob, str(tmp_path))
    return alice, bob, key, copy


def test_send_and_receive(pair):
    alice, bob, key, copy = pair
    sent = alice.conv.send(key, "Meet me at the bridge at noon.", now=T0)
    got = bob.conv.receive(sent['text'], copy, now=T0)

    assert got['plaintext'] == "MEET ME AT THE BRIDGE AT NOON"
    assert got['verified']
    assert [r['direction'] for r in alice.conv.records()] == ['sent']
    assert [r['plaintext'] for r in bob.conv.records()] == ["MEET ME AT THE BRIDGE AT NOON"]


def test_stored_messages_are_encrypted(pair):
    alice, _, key, _ = pair
    alice.conv.send(key, "Meet me at the bridge at noon.", now=T0)
    for name in os.listdir(alice.store.directory):
        with open(os.path.join(alice.store.directory, name), 'rb') as f:
            data = f.read()
        assert b'BRIDGE' not in data and b'Bob' not in data


def test_messages_expire_on_the_senders_schedule(pair):
    alice, bob, key, copy = pair
    sent = alice.conv.send(key, "This lasts a week.", retain_days=7, now=T0)
    bob.conv.receive(sent['text'], copy, now=T0)

    bob.conv.cleanup(T0 + timedelta(days=6))
    assert len(bob.conv.records()) == 1
    bob.conv.cleanup(T0 + timedelta(days=7))
    assert bob.conv.records() == []


def test_deleted_message_cannot_be_recovered_from_a_copy(pair, tmp_path):
    """After deletion, even a copy of the stored file cannot be opened"""
    alice, _, key, _ = pair
    alice.conv.send(key, "Secret plans.", now=T0)
    record = alice.conv.records()[0]
    path = os.path.join(alice.store.directory, f"{record['id']}.msg")
    backup = str(tmp_path / 'backup.msg')
    shutil.copy(path, backup)

    alice.conv.delete_message(record['id'])
    assert not os.path.exists(path)
    shutil.copy(backup, path)
    assert alice.store.get(record['id']) is None


def test_sender_deletion_reaches_the_recipient(pair):
    alice, bob, key, copy = pair
    first = alice.conv.send(key, "Delete this one.", now=T0)
    bob.conv.receive(first['text'], copy, now=T0)
    first_id = alice.conv.records()[0]['id']

    alice.conv.delete_message(first_id)
    second = alice.conv.send(key, "Keep this one.", now=T0)
    got = bob.conv.receive(second['text'], copy, now=T0)

    assert got['deleted_messages'] == [first_id]
    assert [r['plaintext'] for r in bob.conv.records()] == ["KEEP THIS ONE"]


def test_recipient_cannot_delete_the_senders_copy(pair, tmp_path):
    """Deletion instructions only cover the instructing sender's own messages"""
    alice, bob, key, copy = pair
    bob_key = bob.new_key('Alice')
    bob_copy = bob.give_copy(bob_key, alice, str(tmp_path))

    from_alice = alice.conv.send(key, "From Alice.", now=T0)
    bob.conv.receive(from_alice['text'], copy, now=T0)
    alice_message_id = alice.conv.records()[0]['id']

    # Bob tries to delete Alice's sent message from her store
    state = bob.conv.load_state()
    bob.conv._pending(state, 'Alice')['messages'].append(alice_message_id)
    bob.conv.save_state(state)
    got = alice.conv.receive(bob.conv.send(bob_key, "From Bob.", now=T0)['text'], bob_copy, now=T0)

    assert got['deleted_messages'] == []
    assert alice.store.get(alice_message_id) is not None


def test_key_is_replaced_after_word_limit(pair, monkeypatch):
    monkeypatch.setattr(conversation, 'KEY_WORD_LIMIT', 10)
    alice, bob, key, copy = pair

    first = alice.conv.send(key, "Six words in this first message.", now=T0)
    assert first['new_key'] is None
    bob.conv.receive(first['text'], copy, now=T0)

    second = alice.conv.send(key, "Another six words in this one.", now=T0)
    new_key = second['new_key']
    assert new_key is not None and second['key'] is new_key
    assert new_key['replaces'] == key['key_id']

    got = bob.conv.receive(second['text'], copy, now=T0)
    assert got['new_key']['key_id'] == new_key['key_id']
    assert not bob.km.is_own_key(got['new_key'])

    third = alice.conv.send(new_key, "Now using the new key.", now=T0)
    assert bob.conv.receive(third['text'], got['new_key'], now=T0)['plaintext'] == "NOW USING THE NEW KEY"


def test_key_is_replaced_after_max_age(pair):
    alice, _, key, _ = pair
    assert alice.conv.send(key, "Fresh.", now=T0)['new_key'] is None
    later = T0 + timedelta(days=conversation.KEY_MAX_AGE_DAYS + 1)
    assert alice.conv.send(key, "Old key now.", now=later)['new_key'] is not None


def test_replaced_keys_are_deleted_on_both_sides(pair, monkeypatch):
    """Once no stored message uses a replaced key, both copies of it are deleted"""
    monkeypatch.setattr(conversation, 'KEY_WORD_LIMIT', 5)
    alice, bob, key, copy = pair
    old_id = key['key_id']

    sent = alice.conv.send(key, "Eight words to go past the limit here.", now=T0)
    new_key = sent['key']
    bob_new = bob.conv.receive(sent['text'], copy, now=T0)['new_key']
    old_file = [k['filepath'] for k in alice.km.list_keys() if k['key_id'] == old_id][0]

    # The message written with the old key expires, so the old key is deleted
    later = T0 + timedelta(days=31)
    assert old_id in alice.conv.cleanup(later)['keys']
    assert not os.path.exists(old_file)

    # Alice's next message tells Bob's program to delete his copy too
    monkeypatch.setattr(conversation, 'KEY_WORD_LIMIT', 2000)
    new_key['created'] = later.isoformat()
    bob_new['created'] = later.isoformat()
    got = bob.conv.receive(alice.conv.send(new_key, "Hi.", now=later)['text'], bob_new, now=later)
    assert got['deleted_keys'] == [old_id]
    assert old_id not in [k['key_id'] for k in bob.km.list_keys()]


def test_deleted_key_cannot_be_recovered_from_a_copy(tmp_path):
    keystore = MemoryKeyStore()
    km = KeyManager(str(tmp_path / 'keys'), keystore)
    path = km.save_key(km.generate_key('Bob'), PASSWORD)
    backup = str(tmp_path / 'backup.key')
    shutil.copy(path, backup)

    km.delete_key(path)
    assert not os.path.exists(path)
    with pytest.raises(KeyDestroyedError):
        km.load_key(backup, PASSWORD)


def test_retired_key_cannot_send(pair):
    alice, _, key, _ = pair
    key['_stored_unencrypted'] = True
    with pytest.raises(ConversationError):
        alice.conv.send(key, "Hello.", now=T0)


def test_partner_copy_cannot_send(pair):
    _, bob, _, copy = pair
    with pytest.raises(ConversationError):
        bob.conv.send(copy, "Pretending to be Alice.", now=T0)


def test_changed_message_is_rejected(pair):
    alice, bob, key, copy = pair
    text = alice.conv.send(key, "Pay ten.", now=T0)['text']
    tampered = text.replace('RETAIN 30', 'RETAIN 3000')
    from bigraph.security import MessageIntegrityError
    with pytest.raises(MessageIntegrityError):
        bob.conv.receive(tampered, copy, now=T0)


def test_no_os_key_store_means_nothing_is_stored(tmp_path, monkeypatch):
    """Without an OS key store, keys and messages are not stored at all"""
    import keyring
    from keyring.backends import fail
    monkeypatch.setattr(keyring, 'get_keyring', lambda: fail.Keyring())
    km = KeyManager(str(tmp_path / 'keys'), KeyStore())

    with pytest.raises(KeyStoreUnavailableError):
        km.save_key(km.generate_key('Bob'), PASSWORD)
    with pytest.raises(KeyStoreUnavailableError):
        MessageStore(str(tmp_path / 'messages'), KeyStore()).add(
            {'id': 'ab' * 16, 'expires': T0.isoformat(), 'sent': T0.isoformat()})
    assert not os.path.exists(str(tmp_path / 'messages'))
