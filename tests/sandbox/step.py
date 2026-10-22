#!/usr/bin/env python3
"""
One step of a two-user Bigraph test, run as a sandbox user (alice or bob)
in that user's own session and GNOME Keyring. Keys and messages are stored in
the user's home folder exactly as the app stores them; files between users go
through /srv/mailbox. Each step stops with an error if something is wrong.
"""

import getpass
import os
import random
import shutil
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/srv/bigraph-src/src')

import secretstorage  # noqa: E402
from bigraph.conversation import ConversationManager, ConversationError  # noqa: E402
from bigraph.key_manager import KeyManager  # noqa: E402
from bigraph.security import MessageIntegrityError  # noqa: E402

MAILBOX = '/srv/mailbox'
BASE = datetime(2026, 10, 22, 12, 0, 0)
USER = getpass.getuser()
PASSWORD = {'alice': 'alice-local-password', 'bob': 'bob-local-password'}[USER]
SHARE_PASSWORD = 'shared-copy-password'

km = KeyManager()
conv = ConversationManager(km)


def fail(message):
    print(f"FAIL: {message}")
    sys.exit(1)


def day(args):
    return BASE + timedelta(days=int(args[0])) if args else BASE


def keys():
    """Every stored key, opened with this user's password"""
    loaded = []
    for info in km.list_keys():
        key = km.load_key(info['filepath'], PASSWORD)
        key['_password'] = PASSWORD
        loaded.append(key)
    return loaded


def current(own):
    replaced = conv.load_state()['replaced']
    found = [k for k in keys() if km.is_own_key(k) == own and k['key_id'] not in replaced]
    if len(found) != 1:
        fail(f"expected one current {'own' if own else 'partner'} key, found {len(found)}")
    return found[0]


def keyring_items():
    bus = secretstorage.dbus_init()
    return len(list(secretstorage.get_default_collection(bus).search_items({'service': 'bigraph'})))


def long_text(words):
    vocabulary = ("river stone lantern harbor morning quiet bridge garden letter window "
                  "silver orchard meadow candle journey valley shadow evening winter forest "
                  "north road field cloud signal answer travel market tower season").split()
    rng = random.Random(7)
    sentences, count = [], 0
    while count < words:
        n = rng.randint(6, 12)
        sentences.append(' '.join(rng.choice(vocabulary) for _ in range(n)).capitalize() + '.')
        count += n
    return ' '.join(sentences)


# -- steps ---------------------------------------------------------------------

def setup(name):
    km.set_user_name(name)
    print(f"{USER}: profile name {name}")


def create(partner):
    key = km.generate_key(partner)
    km.save_key(key, PASSWORD)
    path = os.path.join(MAILBOX, f"{USER}-key-{key['key_id']}.key")
    km.export_key(key, path, SHARE_PASSWORD)
    os.chmod(path, 0o644)  # the mailbox stands in for handing over the file
    print(f"{USER}: created key {key['key_id']} for {partner}; copy in {os.path.basename(path)}")


def import_from(prefix):
    files = [f for f in os.listdir(MAILBOX) if f.startswith(prefix) and f.endswith('.key')]
    for name in sorted(files):
        key = km.import_key(os.path.join(MAILBOX, name), SHARE_PASSWORD)
        if any(k['key_id'] == key['key_id'] for k in km.list_keys()):
            continue
        km.save_key(key, PASSWORD)
        print(f"{USER}: imported {key['key_id']} from {key['sender']} "
              f"({'own key' if km.is_own_key(key) else 'partner key, decode only'})")


def send(name, *args):
    text = {'hello': "Meet me at the north bridge at noon tomorrow.",
            'reply': "I will be there. Bring the map of the valley.",
            'delete-me': "This plan is cancelled; I will delete this message.",
            'after-delete': "New plan: the old harbor tower at dusk.",
            'long': long_text(1100),
            'with-new-key': "This message uses my new key.",
            'later': "Checking in after a month.",
            'after-recovery': "My keys are back, thanks to your copies."}[name]
    sent = conv.send(current(own=True), text, now=day(args))
    with open(os.path.join(MAILBOX, f"{name}.msg"), 'w') as f:
        f.write(sent['text'])
    os.chmod(os.path.join(MAILBOX, f"{name}.msg"), 0o644)
    extra = f"; carries new key {sent['new_key']['key_id']}" if sent['new_key'] else ''
    print(f"{USER}: sent '{name}' ({len(text.split())} words) with key {conv.message_key_id(sent['text'])}{extra}")


def receive(name, *args):
    with open(os.path.join(MAILBOX, f"{name}.msg")) as f:
        text = f.read()
    needed = conv.message_key_id(text)
    key = next((k for k in keys() if k['key_id'] == needed), None)
    if key is None:
        fail(f"no key {needed} for '{name}'")
    got = conv.receive(text, key, now=day(args))
    print(f"{USER}: received '{name}': {got['plaintext'][:70]!r} verified={got['verified']}")
    if got['new_key']:
        print(f"{USER}:   installed sender's new key {got['new_key']['key_id']}")
    if got['deleted_messages'] or got['deleted_keys']:
        print(f"{USER}:   sender deleted messages {got['deleted_messages']} keys {got['deleted_keys']}")


def expect_rejections(name):
    with open(os.path.join(MAILBOX, f"{name}.msg")) as f:
        text = f.read()
    needed = conv.message_key_id(text)
    partner = next(k for k in keys() if k['key_id'] == needed)

    # A changed message
    lines = text.splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith('SYMBOLS '))
    symbols = lines[i][len('SYMBOLS '):].split(',')
    symbols[0], symbols[1] = symbols[1], symbols[0]
    lines[i] = 'SYMBOLS ' + ','.join(symbols)
    try:
        conv.receive('\n'.join(lines) + '\n', partner, now=BASE)
        fail("a changed message was accepted")
    except MessageIntegrityError:
        print(f"{USER}: changed message rejected")

    # The wrong key
    try:
        conv.receive(text, current(own=True), now=BASE)
        fail("a message was read with the wrong key")
    except (ConversationError, MessageIntegrityError) as e:
        print(f"{USER}: wrong key rejected ({type(e).__name__})")

    # Sending with the partner's copy
    try:
        conv.send(current(own=False), "Pretending to be my partner.", now=BASE)
        fail("sent a message with the partner's key")
    except ConversationError:
        print(f"{USER}: sending with the partner's key refused")


def delete_sent(name):
    with open(os.path.join(MAILBOX, f"{name}.msg")) as f:
        message_id = next(line[3:] for line in f.read().splitlines() if line.startswith('ID '))
    shutil.copy(os.path.join(conv.store.directory, f"{message_id}.msg"),
                os.path.expanduser('~/backup-of-deleted.msg'))
    conv.delete_message(message_id)
    print(f"{USER}: deleted sent message '{name}' (kept a raw backup of its file)")


def check_backup(name):
    """Put the raw backup back: without its keyring secret it must not open"""
    with open(os.path.join(MAILBOX, f"{name}.msg")) as f:
        message_id = next(line[3:] for line in f.read().splitlines() if line.startswith('ID '))
    path = os.path.join(conv.store.directory, f"{message_id}.msg")
    shutil.copy(os.path.expanduser('~/backup-of-deleted.msg'), path)
    if conv.store.get(message_id) is not None:
        fail("the deleted message could be read from its backup")
    os.remove(path)
    print(f"{USER}: backup of the deleted message cannot be decrypted")


def cleanup(*args):
    result = conv.cleanup(day(args))
    print(f"{USER}: cleanup deleted {len(result['messages'])} messages, keys {result['keys']}")


def lose_keys():
    for info in km.list_keys():
        os.remove(info['filepath'])
    print(f"{USER}: lost all key files (profile kept)")


def export_all():
    for key in keys():
        path = os.path.join(MAILBOX, f"recovery-{USER}-{key['key_id']}.key")
        km.export_key(key, path, SHARE_PASSWORD)
        os.chmod(path, 0o644)
    print(f"{USER}: exported copies of all {len(km.list_keys())} keys for recovery")


def status():
    replaced = conv.load_state()['replaced']
    print(f"{USER}: keys:")
    for k in keys():
        print(f"    {k['key_id']}  {k['sender'] or '?'} -> {k['recipient']}  "
              f"{'own' if km.is_own_key(k) else 'partner'}"
              f"{'  (replaced)' if k['key_id'] in replaced else ''}")
    print(f"{USER}: messages:")
    for r in conv.records():
        print(f"    {r['direction']:8} {r['partner']:6} key {r['key_id']}  expires {r['expires'][:10]}  "
              f"{r['plaintext'][:40]!r}")
    print(f"{USER}: bigraph secrets in keyring: {keyring_items()}")


if __name__ == '__main__':
    command, *rest = sys.argv[1:]
    globals()[command.replace('-', '_')](*rest)
