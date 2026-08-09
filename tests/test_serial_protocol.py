import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.communication import SerialTransport


class SerialProtocolTests(unittest.TestCase):
    def test_heartbeat_is_sent_immediately(self) -> None:
        transport = SerialTransport(heartbeat_interval=1.0)

        with patch("raspberry.communication.time.monotonic", return_value=0.0):
            transport.send_heartbeat()

        self.assertEqual(transport._command_queue.get_nowait(), "HEARTBEAT")

    def test_watchdog_event_is_raised_on_silence_and_stops_on_activity(self) -> None:
        transport = SerialTransport(heartbeat_timeout=0.2)
        transport._set_connected(True)

        with patch("raspberry.communication.time.monotonic", return_value=1.0):
            transport._last_message_received = 0.0
            transport._check_watchdog()

        self.assertEqual(transport.read_events(), ["WATCHDOG"])
        self.assertEqual(transport._command_queue.get_nowait(), "STOP")

        with patch("raspberry.communication.time.monotonic", return_value=1.1):
            transport._last_message_received = 1.1
            transport._check_watchdog()

        self.assertEqual(transport.read_events(), [])

    def test_recovery_clears_watchdog_state_after_activity(self) -> None:
        transport = SerialTransport(heartbeat_timeout=0.2)
        transport._set_connected(True)

        with patch("raspberry.communication.time.monotonic", return_value=1.0):
            transport._last_message_received = 0.0
            transport._check_watchdog()

        self.assertTrue(transport._watchdog_triggered)

        with patch("raspberry.communication.time.monotonic", return_value=1.1):
            transport._last_message_received = 1.1
            transport._check_watchdog()

        with patch("raspberry.communication.time.monotonic", return_value=1.2):
            transport._last_message_received = 1.2
            transport._check_watchdog()

        self.assertFalse(transport._watchdog_warned)


if __name__ == "__main__":
    unittest.main()
