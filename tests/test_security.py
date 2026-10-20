"""
Tests for key file encryption, private storage, key warnings, and message check codes
"""

import sys
import os
import json
import stat
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from bigraph.key_manager import KeyManager
from bigraph.encoder import BigramEncoder
from bigraph.decoder import BigramDecoder
from bigraph.security import (PasswordRequiredError, WrongPasswordError, MessageIntegrityError,
                              default_keys_directory)

PASSWORD = 'correct horse battery'


@pytest.fixture
def km(tmp_path):
    return KeyManager(keys_directory=str(tmp_path / 'keys'))


@pytest.fixture
def key(km):
    return km.generate_key('Alice Example')


def test_key_file_is_encrypted(km, key):
    """The key file does not contain the recipient or the symbol table in readable form"""
    path = km.save_key(key, PASSWORD)
    text = open(path).read()
    data = json.loads(text)

    assert data['format'] == 'bigraph-key'
    assert 'Alice' not in text
    assert 'symbol_to_meaning' not in text
    assert 'WORD_THE' not in text
    assert set(data) == {'format', 'version', 'created', 'security_version', 'local_secret',
                         'key_id', 'creator_id', 'kdf', 'cipher', 'nonce', 'ciphertext'}


def test_round_trip(km, key):
    path = km.save_key(key, PASSWORD)
    loaded = km.load_key(path, PASSWORD)

    assert loaded['recipient'] == 'Alice Example'
    assert loaded['symbol_to_meaning'] == key['symbol_to_meaning']
    assert loaded['meaning_to_symbol'] == key['meaning_to_symbol']
    assert loaded['symbols_svg'] == key['symbols_svg']
    assert loaded['mac_key'] == key['mac_key']


def test_password_required(km, key):
    path = km.save_key(key, PASSWORD)
    with pytest.raises(PasswordRequiredError):
        km.load_key(path)


def test_wrong_password(km, key):
    path = km.save_key(key, PASSWORD)
    with pytest.raises(WrongPasswordError):
        km.load_key(path, 'wrong password')


def test_changed_key_file_is_detected(km, key):
    """Changing the encrypted data or the readable header makes the file fail to open"""
    path = km.save_key(key, PASSWORD)
    data = json.loads(open(path).read())

    changed = dict(data)
    ciphertext = bytearray(changed['ciphertext'].encode())
    ciphertext[10] = ord('A') if ciphertext[10] != ord('A') else ord('B')
    changed['ciphertext'] = ciphertext.decode()
    with open(path, 'w') as f:
        json.dump(changed, f)
    with pytest.raises(WrongPasswordError):
        km.load_key(path, PASSWORD)

    changed = dict(data, created='1999-01-01')
    with open(path, 'w') as f:
        json.dump(changed, f)
    with pytest.raises(WrongPasswordError):
        km.load_key(path, PASSWORD)


def test_short_password_rejected(km, key):
    with pytest.raises(ValueError):
        km.save_key(key, 'short')


@pytest.mark.skipif(os.name != 'posix', reason='file modes are POSIX-only')
def test_key_files_are_private(km, key, tmp_path):
    path = km.save_key(key, PASSWORD)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(km.keys_directory).st_mode) == 0o700

    export_path = str(tmp_path / 'shared.key')
    with open(export_path, 'w') as f:
        f.write('old')
    os.chmod(export_path, 0o644)
    km.export_key(key, export_path, PASSWORD)
    assert stat.S_IMODE(os.stat(export_path).st_mode) == 0o600


def test_file_name_does_not_reveal_recipient(km):
    key = km.generate_key('..\\..\\evil/../name')
    path = km.save_key(key, PASSWORD)

    assert os.path.dirname(path) == km.keys_directory
    assert os.path.basename(path).startswith('key_')
    assert 'evil' not in path


def test_default_directory_is_per_user_and_created_lazily(tmp_path, monkeypatch):
    monkeypatch.setenv('HOME', str(tmp_path))
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'data'))
    monkeypatch.setenv('APPDATA', str(tmp_path / 'appdata'))
    directory = default_keys_directory()
    assert str(tmp_path) in directory

    km = KeyManager()
    assert km.keys_directory == directory
    assert not os.path.exists(directory)
    assert km.list_keys() == []
    km.save_key(km.generate_key('Bob'), PASSWORD)
    assert os.path.isdir(directory)


def test_list_keys_without_password(km, key):
    km.save_key(key, PASSWORD)
    keys = km.list_keys()

    assert len(keys) == 1
    assert keys[0]['encrypted'] is True
    assert keys[0]['recipient'] is None
    assert keys[0]['created'] == key['created'][:10]


def test_old_unencrypted_key_loads_with_warning(km, key):
    """Older plain JSON key files still open, and are reported"""
    os.makedirs(km.keys_directory, exist_ok=True)
    path = os.path.join(km.keys_directory, 'old.key')
    data = {k: v for k, v in key.items() if k not in ('symbols_svg', 'meaning_to_symbol')}
    with open(path, 'w') as f:
        json.dump(data, f)

    loaded = km.load_key(path)
    assert loaded['symbol_to_meaning'] == key['symbol_to_meaning']
    assert any('not protected by a password' in w for w in km.key_warnings(loaded))
    assert km.list_keys()[0]['recipient'] == 'Alice Example'
    assert km.list_keys()[0]['encrypted'] is False

    # Saving it again protects it, and the warning goes away
    resaved = km.load_key(km.save_key(loaded, PASSWORD), PASSWORD)
    assert km.key_warnings(resaved) == []


def test_key_warnings(km):
    assert km.key_warnings(km.generate_key('Secure')) == []

    seeded = km.generate_key('Seeded', seed=42)
    assert any('made from a seed' in w for w in km.key_warnings(seeded))

    old = km.generate_key('Old', seed=42)
    del old['symbol_seed']
    del old['mac_key']
    warnings = km.key_warnings(old)
    assert any('32-bit seed' in w for w in warnings)
    assert any('no check secret' in w for w in warnings)


def test_message_check_code(key, tmp_path):
    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)
    encoded = encoder.encode("Meet me at the old bridge at noon.")

    text = encoder.format_message(encoded)
    assert text.splitlines()[0] == 'BIGRAPH-MESSAGE 1'
    assert text.splitlines()[2].startswith('CHECK ')
    assert decoder.read_message(text) == (encoded, True)

    path = str(tmp_path / 'message.enc')
    encoder.save_encoded_message(encoded, path)
    assert encoder.load_encoded_message(path) == encoded
    assert decoder.load_and_decode(path) == "MEET ME AT THE OLD BRIDGE AT NOON"


def test_changed_message_is_detected(key):
    encoder = BigramEncoder(key)
    decoder = BigramDecoder(key)
    encoded = encoder.encode("Meet me at noon.")
    lines = encoder.format_message(encoded).splitlines()

    changed = list(encoded)
    changed[0], changed[1] = changed[1], changed[0]
    tampered = '\n'.join([lines[0], ','.join(map(str, changed)), lines[2]])
    with pytest.raises(MessageIntegrityError):
        decoder.read_message(tampered)

    # Removing the check code is also detected
    with pytest.raises(MessageIntegrityError):
        decoder.read_message('\n'.join(lines[:2]))


def test_message_from_another_key_is_detected(km, key):
    other = km.generate_key('Other')
    text = BigramEncoder(other).format_message(BigramEncoder(other).encode("Hello there."))
    with pytest.raises(MessageIntegrityError):
        BigramDecoder(key).read_message(text)


def test_old_message_format_still_reads(key):
    """Bare number lists from before check codes still decode, reported as unverified"""
    encoded = BigramEncoder(key).encode("Hello there.")
    assert BigramDecoder(key).read_message(','.join(map(str, encoded))) == (encoded, False)


def test_encoder_does_not_create_directories(tmp_path, monkeypatch, key):
    workdir = tmp_path / 'work'
    workdir.mkdir()
    monkeypatch.chdir(workdir)
    BigramEncoder(key)
    BigramDecoder(key)
    assert os.listdir(workdir) == []


# ---------------------------------------------------------------------------
# Retired keys, security versions, ownership and replacement
# ---------------------------------------------------------------------------

from bigraph.key_manager import RetiredKeyError
from bigraph.constants import SECURITY_VERSION


def write_plain_key(km, key, name='old.key'):
    os.makedirs(km.keys_directory, exist_ok=True)
    path = os.path.join(km.keys_directory, name)
    data = {k: v for k, v in key.items() if k not in ('symbols_svg', 'meaning_to_symbol')}
    with open(path, 'w') as f:
        json.dump(data, f)
    return path


def test_new_keys_record_security_version_and_creator(km, key):
    assert key['security_version'] == SECURITY_VERSION
    assert key['creator_id'] == km.load_profile()['user_id']
    assert km.can_encode(key) == (True, '')


def test_old_32_bit_key_can_only_decode(km):
    old = km.generate_key('Old', seed=42)
    del old['symbol_seed'], old['mac_key'], old['security_version']
    encoded = BigramEncoder(km.generate_key('Old', seed=42)).encode("Hello there.")

    assert km.is_retired(old)
    assert km.can_encode(old)[0] is False
    with pytest.raises(RetiredKeyError):
        BigramEncoder(old)
    assert BigramDecoder(old).decode(encoded) == "HELLO THERE"


def test_unencrypted_key_file_can_only_decode_until_protected(km, key):
    loaded = km.load_key(write_plain_key(km, key))
    with pytest.raises(RetiredKeyError):
        BigramEncoder(loaded)

    protected = km.load_key(km.save_key(loaded, PASSWORD), PASSWORD)
    assert not km.is_retired(protected)
    BigramEncoder(protected)


def test_outdated_security_version(km, key, monkeypatch):
    """Raising SECURITY_VERSION retires keys made under the previous version"""
    import bigraph.key_manager as key_manager
    path = km.save_key(key, PASSWORD)
    monkeypatch.setattr(key_manager, 'SECURITY_VERSION', SECURITY_VERSION + 1)

    assert km.list_keys()[0]['outdated'] is True
    loaded = km.load_key(path, PASSWORD)
    assert km.is_retired(loaded)
    assert any('older security rules' in w for w in km.key_warnings(loaded))

    new_key = km.rotate_key(loaded)
    assert new_key['security_version'] == SECURITY_VERSION + 1
    assert not km.is_retired(new_key)


def test_list_keys_reports_security_version(km, key):
    km.save_key(key, PASSWORD)
    write_plain_key(km, key)
    listed = {k['filename']: k for k in km.list_keys()}

    assert listed['old.key']['security_version'] == 0
    assert listed['old.key']['outdated'] is True
    encrypted = [k for k in listed.values() if k['encrypted']][0]
    assert encrypted['security_version'] == SECURITY_VERSION
    assert encrypted['outdated'] is False


def test_rotate_key_keeps_sender_and_recipient(km):
    km.set_user_name('Alice')
    old = km.generate_key('Bob')
    new = km.rotate_key(old)

    assert (new['sender'], new['recipient']) == ('Alice', 'Bob')
    assert new['replaces'] == old['key_id']
    assert new['key_id'] != old['key_id']
    assert new['symbol_to_meaning'] != old['symbol_to_meaning']


# ---------------------------------------------------------------------------
# Partner copies (escrow) and recovery
# ---------------------------------------------------------------------------

def test_partner_key_decodes_but_cannot_encode(tmp_path):
    """Each person sends with their own key; the partner's copy only decodes"""
    alice = KeyManager(keys_directory=str(tmp_path / 'alice'))
    bob = KeyManager(keys_directory=str(tmp_path / 'bob'))
    alice.set_user_name('Alice')
    bob.set_user_name('Bob')

    alice_key = alice.generate_key('Bob')
    shared = str(tmp_path / 'for_bob.key')
    alice.export_key(alice_key, shared, 'share password')
    at_bob = bob.import_key(shared, 'share password')

    assert at_bob['sender'] == 'Alice'
    assert not bob.is_own_key(at_bob)
    allowed, reason = bob.can_encode(at_bob)
    assert not allowed and "belongs to Alice" in reason

    message = BigramEncoder(alice_key).format_message(BigramEncoder(alice_key).encode("See you soon."))
    encoded, verified = BigramDecoder(at_bob).read_message(message)
    assert verified and BigramDecoder(at_bob).decode(encoded) == "SEE YOU SOON"


def test_recovery_from_partner(tmp_path):
    """If Alice loses her keys, Bob's copies let her read old messages again"""
    alice = KeyManager(keys_directory=str(tmp_path / 'alice'))
    bob = KeyManager(keys_directory=str(tmp_path / 'bob'))
    alice.set_user_name('Alice')
    bob.set_user_name('Bob')

    alice_key = alice.generate_key('Bob')
    bob_key = bob.generate_key('Alice')
    # Exchange copies
    alice.export_key(alice_key, str(tmp_path / 'a.key'), 'share password')
    bob.export_key(bob_key, str(tmp_path / 'b.key'), 'share password')
    bob.save_key(bob.import_key(str(tmp_path / 'a.key'), 'share password'), PASSWORD)
    alice.save_key(alice.import_key(str(tmp_path / 'b.key'), 'share password'), PASSWORD)

    sent = BigramEncoder(alice_key).encode("The meeting is at nine.")
    received = BigramEncoder(bob_key).encode("I will be there.")

    # Alice's keys are lost, but her profile remains
    for k in alice.list_keys():
        os.remove(k['filepath'])

    # Bob exports his copies of both keys back to Alice
    for k in bob.list_keys():
        copy = bob.load_key(k['filepath'], PASSWORD)
        bob.export_key(copy, str(tmp_path / f"back_{copy['key_id']}.key"), 'recovery password')
        restored = alice.import_key(str(tmp_path / f"back_{copy['key_id']}.key"), 'recovery password')
        if restored['sender'] == 'Alice':
            assert alice.is_own_key(restored)
            assert BigramDecoder(restored).decode(sent) == "THE MEETING IS AT NINE"
        else:
            assert not alice.is_own_key(restored)
            assert BigramDecoder(restored).decode(received) == "I WILL BE THERE"


def test_seeded_keys_do_not_touch_profile(km):
    km.generate_key('Test', seed=1)
    assert not os.path.exists(km.profile_path)


@pytest.mark.skipif(os.name != 'posix', reason='file modes are POSIX-only')
def test_profile_is_private(km):
    km.set_user_name('Alice')
    assert stat.S_IMODE(os.stat(km.profile_path).st_mode) == 0o600
    assert km.list_keys() == []
