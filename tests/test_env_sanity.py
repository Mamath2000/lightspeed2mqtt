import os
import importlib.metadata

def test_logitech_dll_and_logipy_version():
    """Vérifie la présence de la DLL et la version de logipy installée."""
    dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib', 'LogitechLed.dll'))
    assert os.path.exists(dll_path), f"DLL LogitechLed.dll absente : {dll_path}"
    version = importlib.metadata.version("logipy")
    assert version == "1.2.1", f"logipy version attendue 1.2.1, trouvée : {version}"
