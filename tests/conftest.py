"""
Shared test setup

There is no OS key store in the test environment, so every KeyManager in a
test shares one in-memory key store, as they would share the OS key store.
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
import bigraph.key_manager
from bigraph.keystore import MemoryKeyStore


@pytest.fixture(autouse=True)
def memory_keystore(monkeypatch):
    store = MemoryKeyStore()
    monkeypatch.setattr(bigraph.key_manager, 'KeyStore', lambda: store)
    return store
