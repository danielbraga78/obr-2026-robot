from pathlib import Path
import re

from raspberry.config import MOTOR_MAX_PWM, MOTOR_MIN_PWM, MOTOR_PWM_GAINS
from raspberry.motion import _firmware_wheel_pwms, normalize_motor_command

def _read_firmware(path: str) -> str:
    return Path(__file__).resolve().parents[2].joinpath(path).read_text(encoding="utf-8")


FIRMWARES = (
    "arduino/firmware/robot_mega/robot_mega.ino",
    "arduino/firmware/robot_mega_pcb/robot_mega_pcb.ino",
)
MATRIX = (
    "const float motor1 = vx + vy + wz;",
    "const float motor2 = vx - vy - wz;",
    "const float motor3 = vx - vy + wz;",
    "const float motor4 = vx + vy - wz;",
)


def _firmware_motor_profile(source: str):
    maximum = int(re.search(r"kMaxMotorSpeed\s*=\s*(\d+)", source).group(1))
    minimum_array = re.search(r"kMotorMinDuty\[4\]\s*=\s*\{([^}]+)\}", source)
    gain_array = re.search(r"kMotorGain\[4\]\s*=\s*\{([^}]+)\}", source)
    if minimum_array:
        minima = tuple(int(value.strip()) for value in minimum_array.group(1).split(","))
        gains = tuple(float(value.strip().rstrip("f")) for value in gain_array.group(1).split(","))
    else:
        minima = (int(re.search(r"kMinMotorSpeed\s*=\s*(\d+)", source).group(1)),) * 4
        gains = (1.0,) * 4
    return maximum, minima, gains


def test_robot_mega_uses_explicit_omni_motor_matrix():
    source = _read_firmware("arduino/firmware/robot_mega/robot_mega.ino")

    assert all(matrix_line in source for matrix_line in MATRIX)
    assert "setMotorSpeed(0, m1);" in source
    assert "setMotorSpeed(1, m2);" in source
    assert "setMotorSpeed(2, m3);" in source
    assert "setMotorSpeed(3, m4);" in source


def test_supported_firmware_profiles_match_raspberry_motion_model():
    for path in FIRMWARES:
        source = _read_firmware(path)
        with_context = f"{path}"
        assert all(matrix_line in source for matrix_line in MATRIX), with_context
        maximum, minima, gains = _firmware_motor_profile(source)
        assert maximum == MOTOR_MAX_PWM, with_context
        assert minima == MOTOR_MIN_PWM, with_context
        assert gains == MOTOR_PWM_GAINS, with_context
        assert "pulseIn(" not in source, with_context
        assert "processSerialPort(Serial, g_usbLine, g_usbLineLength);" in source, with_context
        assert "processSerialPort(Serial1, g_uartLine, g_uartLineLength);" in source, with_context
        assert "handleCommand(String(line), port);" in source, with_context
        assert "if (nowUs - g_ultrasonicTriggerUs >= kUltrasonicTimeoutUs)" in source, with_context
        assert "const bool echoHigh = digitalRead(kUltrasonicEchoPin) == HIGH;" in source, with_context
        if "robot_mega_pcb" in path:
            assert "long duty = lround(magnitude * kMotorGain[motorIndex]);" in source, with_context
            assert "if (duty < kMotorMinDuty[motorIndex])" in source, with_context
            assert "setMotorSpeed(0, static_cast<int>(motor1 * scale));" in source, with_context
        else:
            assert "if (abs(speed) < kMinMotorSpeed)" in source, with_context
            assert "const int m1 = static_cast<int>(motor1 * scale);" in source, with_context
            assert "setMotorSpeed(0, m1);" in source, with_context

        for command, expected in (
            ("MOVE,150,0,0", (150, 150, 150, 150)),
            ("MOVE,150,0,50", (190, 110, 190, 110)),
            ("MOVE,110,0,80", (160, 0, 160, 0)),
            ("MOVE,110,0,20", (0, 0, 0, 0)),
            ("MOVE,0,0,110", (110, -110, 110, -110)),
            ("MOVE,0,0,-110", (-110, 110, -110, 110)),
        ):
            normalized = normalize_motor_command(command)
            velocity = (
                (0.0, 0.0, 0.0)
                if normalized == "STOP"
                else tuple(float(part) for part in normalized.split(",")[1:])
            )
            assert _firmware_wheel_pwms(*velocity, minima, gains) == expected, (
                with_context,
                command,
                normalized,
            )


def test_legacy_robot_sketch_keeps_the_same_omni_matrix():
    source = _read_firmware("arduino/robot/robot.ino")

    assert all(matrix_line in source for matrix_line in MATRIX)
