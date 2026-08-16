import sys
from pathlib import Path

import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.config import RobotContext
from raspberry.main import RobotApp
from raspberry.ultrasonic import UltrasonicMonitor


class FakeSerial:
    def __init__(self, connected: bool = True) -> None:
        self.commands = []
        self.inbox = []
        self.connected = connected

    def send_command(self, command: str) -> None:
        self.commands.append(command)

    def is_connected(self) -> bool:
        return self.connected

    def read_messages(self):
        messages, self.inbox = self.inbox, []
        return messages


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def make_app(ultrasonic_enabled: bool = True) -> RobotApp:
    app = RobotApp.__new__(RobotApp)
    app.serial = FakeSerial()
    app.context = RobotContext()
    app.ultrasonic = UltrasonicMonitor() if ultrasonic_enabled else None
    app._sensor_arm_sent_at = None
    app._last_distance_at = None
    app._now = FakeClock()
    return app


ARM = "SENSOR,ULTRASONIC,ON"


class SensorArmingTests(unittest.TestCase):
    def test_ready_arms_the_ultrasonic(self) -> None:
        app = make_app()
        app.serial.inbox = ["READY"]

        app._process_messages()

        self.assertEqual(app.serial.commands, [ARM])

    def test_ready_resets_the_reading_history(self) -> None:
        app = make_app()
        app.ultrasonic.update(app.context, 12.0)
        app.serial.inbox = ["READY"]

        app._process_messages()
        # Sem o reset, esta leitura seria a segunda da sequência e confirmaria.
        app.ultrasonic.update(app.context, 11.5)

        self.assertFalse(app.context.has_recent_temporal_flag("obstacle_detected", ttl=0.25))

    def test_arming_is_retried_while_no_reading_arrives(self) -> None:
        app = make_app()

        app._ensure_sensors_armed()
        app._ensure_sensors_armed()  # Dentro do intervalo: não repete
        self.assertEqual(app.serial.commands, [ARM])

        app._now.advance(3.5)
        app._ensure_sensors_armed()
        self.assertEqual(app.serial.commands, [ARM, ARM])

    def test_arming_stops_once_readings_arrive(self) -> None:
        app = make_app()
        app._ensure_sensors_armed()
        app.serial.inbox = ["DIST,80.0"]
        app._process_messages()

        app._now.advance(1.0)
        app._ensure_sensors_armed()

        self.assertEqual(app.serial.commands, [ARM])

    def test_arming_resumes_if_readings_stop(self) -> None:
        app = make_app()
        app.serial.inbox = ["DIST,80.0"]
        app._process_messages()

        app._now.advance(4.0)
        app._ensure_sensors_armed()

        self.assertEqual(app.serial.commands, [ARM])

    def test_nothing_is_sent_while_serial_is_down(self) -> None:
        app = make_app()
        app.serial.connected = False

        app._ensure_sensors_armed()

        self.assertEqual(app.serial.commands, [])

    def test_disabled_sensor_is_never_armed(self) -> None:
        app = make_app(ultrasonic_enabled=False)
        app.serial.inbox = ["READY"]

        app._process_messages()
        app._ensure_sensors_armed()

        self.assertEqual(app.serial.commands, [])


if __name__ == "__main__":
    unittest.main()
