# Two-user sandbox test (Linux)

Tests the installed app with two separate users, `alice` and `bob`, each with
their own home folder, D-Bus session and GNOME Keyring, exchanging keys and
messages through a shared folder. It uses real OS key stores, unlike the unit
tests, and exercises key exchange, messages both ways, rejections, sender
deletion, automatic key replacement, expiry, and recovery from a partner's
copies.

The steps run the program's own code (`/srv/bigraph-src`) as each user, since
the installed app has only a GUI. `gui_shot.sh` opens the installed app's
window on a virtual display and takes a screenshot.

## Setup (as root, on Debian or Ubuntu)

```bash
apt-get install -y gnome-keyring dbus dbus-x11 libsecret-tools xvfb x11-utils xdotool imagemagick
useradd -m -s /bin/bash alice; useradd -m -s /bin/bash bob
mkdir -p /srv/mailbox && chmod 1777 /srv/mailbox
mkdir -p /srv/bigraph-src && cp -r src /srv/bigraph-src/ && chmod -R a+rX /srv/bigraph-src
python3 -m venv /srv/bigraph-venv && /srv/bigraph-venv/bin/pip install cryptography keyring
mkdir -p /srv/bigraph-scenario && cp tests/sandbox/step.py /srv/bigraph-scenario/
cp tests/sandbox/run_as.sh tests/sandbox/s.sh tests/sandbox/gui_shot.sh /srv/
dpkg -i bigraph_<version>_amd64.deb
```

## Running

`s.sh USER STEP ARGS` runs one step as a user in a fresh session; numbers are
simulated days. The sequence used:

```bash
/srv/s.sh alice setup Alice;          /srv/s.sh bob setup Bob
/srv/s.sh alice create Bob;           /srv/s.sh bob create Alice
/srv/s.sh bob import-from alice-key;  /srv/s.sh alice import-from bob-key
/srv/s.sh alice send hello 0;         /srv/s.sh bob receive hello 0
/srv/s.sh bob send reply 0;           /srv/s.sh alice receive reply 0
/srv/s.sh bob expect-rejections hello
/srv/s.sh alice send delete-me 1;     /srv/s.sh bob receive delete-me 1
/srv/s.sh alice delete-sent delete-me; /srv/s.sh alice check-backup delete-me
/srv/s.sh alice send after-delete 2;  /srv/s.sh bob receive after-delete 2
/srv/s.sh alice send long 3;          /srv/s.sh bob receive long 3
/srv/s.sh alice send with-new-key 20; /srv/s.sh bob receive with-new-key 20
/srv/s.sh alice cleanup 34
/srv/s.sh alice send later 34;        /srv/s.sh bob receive later 34
/srv/s.sh alice lose-keys;            /srv/s.sh bob export-all
/srv/s.sh alice import-from recovery-bob
/srv/s.sh alice send after-recovery 35; /srv/s.sh bob receive after-recovery 35
/srv/s.sh alice status;               /srv/s.sh bob status
/srv/run_as.sh alice /srv/gui_shot.sh /home/alice/gui.png 4
```

New keys get their creation time from the real clock while the steps use
simulated days, so after a time jump every new key counts as more than 30 days
old and the next message replaces it again. That is an effect of the
simulation, not of the program.
