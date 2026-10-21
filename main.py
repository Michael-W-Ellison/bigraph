#!/usr/bin/env python3
"""
Bigraph Cryptography System
Main entry point for the GUI application

Run with --self-test to check that everything the program needs is present
(the GUI toolkit, encryption, the OS key store) without opening a window. It
exits with 0 if everything works, 2 if only the OS key store is missing (as
on build servers), and 1 for any other problem. --self-test-report FILE also
writes the results to FILE, since windowed apps on Windows have no console.
"""

import sys
import os

# Add src directory to path (a PyInstaller build already contains the modules)
if not getattr(sys, 'frozen', False):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def self_test() -> int:
    """
    Check the program's parts without opening a window

    Returns:
        0 if everything works, 2 if only the OS key store is missing, 1 otherwise
    """
    import tempfile
    failures = []
    key_store_missing = False

    try:
        import tkinter
        tkinter.Tcl().eval('info patchlevel')
        print(f"GUI toolkit: Tk {tkinter.TkVersion}")
    except Exception as e:
        failures.append(f"GUI toolkit: {e}")

    try:
        from bigraph.key_manager import KeyManager
        from bigraph.keystore import KeyStore, MemoryKeyStore, KeyStoreUnavailableError
        from bigraph.encoder import BigramEncoder
        from bigraph.decoder import BigramDecoder
        import keyring

        with tempfile.TemporaryDirectory() as directory:
            km = KeyManager(os.path.join(directory, 'keys'), MemoryKeyStore())
            key = km.generate_key('Self test')
            path = km.save_key(key, 'self test password')
            key = km.load_key(path, 'self test password')
            text = BigramEncoder(key).format_message(BigramEncoder(key).encode("Self test passed."))
            encoded, verified = BigramDecoder(key).read_message(text)
            decoded = BigramDecoder(key).decode(encoded)
            if decoded != "SELF TEST PASSED" or not verified:
                failures.append(f"Encoding: got {decoded!r}")
            else:
                print("Encryption, keys and encoding: working")

        # Each OS's key store support must be packaged, even where it cannot run
        import importlib
        included = []
        for name in ('Windows', 'macOS', 'SecretService', 'kwallet'):
            try:
                importlib.import_module(f'keyring.backends.{name}')
                included.append(name)
            except ImportError as e:
                failures.append(f"Key store support for {name} is missing: {e}")
        print(f"Key store support included: {', '.join(included)}")

        backend = keyring.get_keyring()
        try:
            KeyStore().check_available()
            print(f"OS key store: {type(backend).__module__}.{type(backend).__name__}")
        except KeyStoreUnavailableError as e:
            print(f"Problem - OS key store: {e}")
            key_store_missing = True
    except Exception as e:
        failures.append(f"Program modules: {type(e).__name__}: {e}")

    for failure in failures:
        print(f"Problem - {failure}")
    if failures:
        print("Self test found problems")
        return 1
    if key_store_missing:
        print("Self test passed, but there is no OS key store, so keys and messages cannot be saved")
        return 2
    print("Self test passed")
    return 0


def main():
    """Main entry point for the application"""
    if '--self-test-report' in sys.argv:
        import contextlib
        report = sys.argv[sys.argv.index('--self-test-report') + 1]
        with open(report, 'w') as f, contextlib.redirect_stdout(f):
            code = self_test()
        sys.exit(code)
    if '--self-test' in sys.argv:
        sys.exit(self_test())

    import tkinter as tk
    from gui.main_window import BigramCryptoGUI

    root = tk.Tk()
    BigramCryptoGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
