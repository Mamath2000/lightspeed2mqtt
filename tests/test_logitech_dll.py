import os
import pytest

def test_logitech_dll_present():
    """Vérifie que la DLL LogitechLed.dll est bien présente dans le dossier lib/ du projet."""
    dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'LogitechLed.dll'))
    assert os.path.exists(dll_path), f"DLL LogitechLed.dll absente : {dll_path}"
