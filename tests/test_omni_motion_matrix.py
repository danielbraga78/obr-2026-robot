from pathlib import Path


def _read_firmware(path: str) -> str:
    return Path(__file__).resolve().parents[1].joinpath(path).read_text(encoding="utf-8")


def test_robot_mega_uses_explicit_omni_motor_matrix():
    source = _read_firmware("arduino/firmware/robot_mega/robot_mega.ino")

    assert "const float motor1 = vx + vy + wz;" in source
    assert "const float motor2 = vx - vy - wz;" in source
    assert "const float motor3 = vx - vy + wz;" in source
    assert "const float motor4 = vx + vy - wz;" in source
    assert "setMotorSpeed(0, m1);" in source
    assert "setMotorSpeed(1, m2);" in source
    assert "setMotorSpeed(2, m3);" in source
    assert "setMotorSpeed(3, m4);" in source


def test_legacy_robot_sketch_keeps_the_same_omni_matrix():
    source = _read_firmware("arduino/robot.ino")

    assert "const float motor1 = vx + vy + wz;" in source
    assert "const float motor2 = vx - vy - wz;" in source
    assert "const float motor3 = vx - vy + wz;" in source
    assert "const float motor4 = vx + vy - wz;" in source
