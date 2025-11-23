import argparse
import ctypes
import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

try:
    from logipy import logi_led
except ImportError:
    print("Le module 'logipy' est requis. Installez-le avec: pip install logipy")
    sys.exit(1)

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("Le module 'paho-mqtt' est requis. Installez-le avec: pip install -r requirements.txt")
    sys.exit(1)


RGB = Tuple[int, int, int]
ALERT_PATTERN = [(255, 0, 0), (255, 255, 255), (0, 0, 0)]
WARNING_PATTERN = [(255, 140, 0), (0, 0, 0)]


def load_env_file(path: str = '.env') -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def ensure_logi_dll_loaded() -> bool:
    if getattr(logi_led, 'led_dll', None):
        return True

    candidates = []
    env_override = os.environ.get('LOGI_LED_DLL')
    if env_override:
        candidates.append(Path(env_override))

    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir / 'LogitechLed.dll')

    program_files = [os.environ.get('ProgramFiles'), os.environ.get('ProgramW6432')]
    ghub_rel = Path('LGHUB/SDK/LED/x64/LogitechLed.dll')
    lgs_rel = Path('Logitech Gaming Software/SDK/LED/x64/LogitechLed.dll')
    lgs_rel_x86 = Path('Logitech Gaming Software/SDK/LED/x86/LogitechLed.dll')
    for base in program_files:
        if not base:
            continue
        path_base = Path(base)
        candidates.append(path_base / ghub_rel)
        candidates.append(path_base / lgs_rel)
        candidates.append(path_base / lgs_rel_x86)

    for dll_path in candidates:
        if dll_path and dll_path.exists():
            logi_led.led_dll = ctypes.cdll.LoadLibrary(str(dll_path))
            return True
    return False


def clamp_channel(value: int) -> int:
    return max(0, min(255, int(value)))


def to_pct(value: int) -> int:
    return int(round((clamp_channel(value) / 255) * 100))


def parse_color_string(value: str) -> RGB:
    if not value:
        raise ValueError('Couleur vide')
    text = value.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return clamp_channel(data['r']), clamp_channel(data['g']), clamp_channel(data['b'])
        if isinstance(data, list) and len(data) == 3:
            r, g, b = data
            return clamp_channel(r), clamp_channel(g), clamp_channel(b)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    if text.startswith('#'):
        hex_value = text.lstrip('#')
        if len(hex_value) != 6:
            raise ValueError('Format hex attendu: #RRGGBB')
        return tuple(int(hex_value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]

    separators = ',' if ',' in text else ' '
    parts = [p for p in text.split(separators) if p]
    if len(parts) == 3:
        r, g, b = (int(part) for part in parts)
        return clamp_channel(r), clamp_channel(g), clamp_channel(b)

    raise ValueError("Impossible de lire la couleur (attendu #RRGGBB ou R,G,B)")


class LightingController:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.pattern_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.initialized = False
        self.released = False

    def start(self) -> None:
        if self.initialized:
            return
        if not ensure_logi_dll_loaded():
            raise RuntimeError("Impossible de trouver 'LogitechLed.dll'. Définissez LOGI_LED_DLL ou placez la DLL à la racine.")
        if not logi_led.logi_led_init():
            raise RuntimeError("Impossible d'initialiser le SDK Logitech. Vérifiez que G Hub / LGS est en cours d'exécution.")
        logi_led.logi_led_save_current_lighting()
        self.initialized = True
        self.released = False

    def shutdown(self) -> None:
        self.stop_pattern()
        if self.initialized:
            with self.lock:
                logi_led.logi_led_restore_lighting()
                logi_led.logi_led_shutdown()
        self.initialized = False

    def _set_color_now(self, rgb: RGB) -> None:
        r, g, b = (clamp_channel(channel) for channel in rgb)
        with self.lock:
            logi_led.logi_led_set_lighting(to_pct(r), to_pct(g), to_pct(b))

    def set_static_color(self, rgb: RGB) -> None:
        self.start()
        if self.released:
            with self.lock:
                logi_led.logi_led_save_current_lighting()
            self.released = False
        self.stop_pattern()
        self._set_color_now(rgb)

    def start_pattern(self, colors: Iterable[RGB], interval: float) -> None:
        self.start()
        self.stop_pattern()
        self.released = False
        self.stop_event = threading.Event()

        def worker() -> None:
            palette = list(colors)
            if not palette:
                return
            while not self.stop_event.is_set():
                for color in palette:
                    if self.stop_event.is_set():
                        break
                    self._set_color_now(color)
                    if self.stop_event.wait(interval):
                        break

        self.pattern_thread = threading.Thread(target=worker, daemon=True)
        self.pattern_thread.start()

    def stop_pattern(self) -> None:
        if self.pattern_thread and self.pattern_thread.is_alive():
            self.stop_event.set()
            self.pattern_thread.join()
        self.pattern_thread = None

    def release(self) -> None:
        if not self.initialized:
            return
        self.stop_pattern()
        with self.lock:
            logi_led.logi_led_restore_lighting()
        self.released = True


@dataclass
class ServiceConfig:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    client_id: str
    topic_color: str
    topic_alert: str
    topic_warning: str
    topic_auto: str
    default_color: Optional[RGB]


class MqttLightingService:
    def __init__(self, controller: LightingController, config: ServiceConfig) -> None:
        self.controller = controller
        self.config = config
        self.client = mqtt.Client(client_id=config.client_id, clean_session=True)
        if config.username:
            self.client.username_pw_set(config.username, config.password or None)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.stop_event = threading.Event()

    def start(self) -> None:
        self.controller.start()
        if self.config.default_color:
            self.controller.set_static_color(self.config.default_color)
        print(f"Connexion MQTT vers {self.config.host}:{self.config.port}…")
        self.client.connect(self.config.host, self.config.port, keepalive=60)
        self.client.loop_start()

    def stop(self) -> None:
        self.stop_event.set()

    def loop_forever(self) -> None:
        try:
            while not self.stop_event.is_set():
                time.sleep(0.5)
        finally:
            self.client.loop_stop()
            self.client.disconnect()
            self.controller.shutdown()

    def on_connect(self, client: mqtt.Client, _userdata, _flags, rc) -> None:
        if rc != 0:
            print(f"Connexion MQTT refusée (code {rc})")
            return
        topics = [
            self.config.topic_color,
            self.config.topic_alert,
            self.config.topic_warning,
            self.config.topic_auto,
        ]
        for topic in topics:
            client.subscribe(topic, qos=1)
        print(f"Connecté. Abonné aux topics: {', '.join(topics)}")

    def on_message(self, _client: mqtt.Client, _userdata, message) -> None:
        topic = message.topic
        payload = message.payload.decode('utf-8', errors='ignore').strip()
        try:
            if topic == self.config.topic_color:
                color = parse_color_string(payload) if payload else self.config.default_color
                if not color:
                    raise ValueError('Couleur manquante pour topic couleur')
                self.controller.set_static_color(color)
                print(f"[MQTT] Couleur appliquée {color}")
            elif topic == self.config.topic_alert:
                self.controller.start_pattern(ALERT_PATTERN, 0.2)
                print('[MQTT] Mode alerte actif')
            elif topic == self.config.topic_warning:
                self.controller.start_pattern(WARNING_PATTERN, 0.35)
                print('[MQTT] Mode warning actif')
            elif topic == self.config.topic_auto:
                self.controller.release()
                print('[MQTT] Rendu main automatique')
            else:
                print(f"[MQTT] Topic ignoré: {topic}")
        except Exception as exc:
            print(f"[MQTT] Erreur sur {topic}: {exc}")


def build_config_from_env() -> ServiceConfig:
    host = os.environ.get('MQTT_HOST', 'localhost')
    port = int(os.environ.get('MQTT_PORT', '1883'))
    username = os.environ.get('MQTT_USERNAME') or None
    password = os.environ.get('MQTT_PASSWORD') or None
    client_id = os.environ.get('MQTT_CLIENT_ID', 'logi-led-service')
    topic_color = os.environ.get('TOPIC_COLOR', 'lightspeed/color')
    topic_alert = os.environ.get('TOPIC_ALERT', 'lightspeed/alert')
    topic_warning = os.environ.get('TOPIC_WARNING', 'lightspeed/warning')
    topic_auto = os.environ.get('TOPIC_AUTO', 'lightspeed/auto')
    default_color_str = os.environ.get('DEFAULT_COLOR', '#00FF80')
    default_color = None
    try:
        if default_color_str:
            default_color = parse_color_string(default_color_str)
    except ValueError as exc:
        print(f"Couleur par défaut invalide ({exc}). Elle sera ignorée.")
    return ServiceConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        client_id=client_id,
        topic_color=topic_color,
        topic_alert=topic_alert,
        topic_warning=topic_warning,
        topic_auto=topic_auto,
        default_color=default_color,
    )


def wait_loop(duration: float) -> None:
    if duration > 0:
        time.sleep(duration)
    else:
        print('Ctrl+C pour arrêter…')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def run_cli_color(value: str, duration: float) -> None:
    controller = LightingController()
    try:
        controller.set_static_color(parse_color_string(value))
        wait_loop(duration)
    finally:
        controller.shutdown()


def run_cli_pattern(pattern: Iterable[RGB], interval: float, duration: float) -> None:
    controller = LightingController()
    try:
        controller.start_pattern(pattern, interval)
        wait_loop(duration)
    finally:
        controller.shutdown()


def run_cli_auto() -> None:
    controller = LightingController()
    try:
        controller.start()
        controller.release()
    finally:
        controller.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description='Middleware Logitech LED contrôlé par MQTT')
    parser.add_argument('--env-file', default='.env', help='Chemin du fichier .env (défaut: .env)')
    subparsers = parser.add_subparsers(dest='command')

    subparsers.add_parser('serve', help='Lance le service MQTT (par défaut)')

    color_parser = subparsers.add_parser('color', help='Applique une couleur et garde le contrôle')
    color_parser.add_argument('value', help='#RRGGBB ou R,G,B')
    color_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    alert_parser = subparsers.add_parser('alert', help='Pattern alerte (rouge/blanc/noir rapide)')
    alert_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    warning_parser = subparsers.add_parser('warning', help='Pattern warning (ambre flash)')
    warning_parser.add_argument('--duration', type=float, default=0, help='Durée en secondes (0 = jusqu\'à Ctrl+C)')

    subparsers.add_parser('auto', help='Rend la main immédiatement')

    args = parser.parse_args()
    load_env_file(args.env_file)
    command = args.command or 'serve'

    if command == 'serve':
        config = build_config_from_env()
        service = MqttLightingService(LightingController(), config)
        try:
            service.start()
            service.loop_forever()
        except KeyboardInterrupt:
            print('Arrêt demandé par l\'utilisateur.')
        finally:
            service.stop()
    elif command == 'color':
        run_cli_color(args.value, args.duration)
    elif command == 'alert':
        run_cli_pattern(ALERT_PATTERN, 0.2, args.duration)
    elif command == 'warning':
        run_cli_pattern(WARNING_PATTERN, 0.35, args.duration)
    elif command == 'auto':
        run_cli_auto()
    else:
        parser.error(f'Commande inconnue: {command}')


if __name__ == '__main__':
    main()