import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raspberry.camera import apply_camera_orientation
from raspberry.main import RobotApp
from raspberry.config import BASE_SPEED, MIN_SPEED, MOTOR_DEADBAND_PWM, MOTOR_MIN_MEANINGFUL_PWM
from raspberry.motion import _wheel_speeds, fit_to_motor_deadband, normalize_motor_command


class CameraOrientationTests(unittest.TestCase):
    def test_normal_camera_returns_the_same_frame(self):
        frame = np.arange(24, dtype=np.uint8).reshape((2, 4, 3))

        with patch("raspberry.camera.CAMERA_INVERTED", False):
            result = apply_camera_orientation(frame)

        self.assertIs(result, frame)

    def test_inverted_camera_rotates_frame_exactly_180_degrees(self):
        frame = np.arange(24, dtype=np.uint8).reshape((2, 4, 3))

        with patch("raspberry.camera.CAMERA_INVERTED", True):
            result = apply_camera_orientation(frame)

        np.testing.assert_array_equal(result, frame[::-1, ::-1])


class MotorOrientationTests(unittest.TestCase):
    """Comandos escolhidos acima da zona morta, para isolar orientação e curva.

    Valores baixos passariam pelo ajuste do fit_to_motor_deadband e o teste
    mediria duas coisas ao mesmo tempo.
    """

    def test_normal_camera_preserves_move(self):
        with patch("raspberry.motion.CAMERA_INVERTED", False), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.0
        ):
            self.assertEqual(normalize_motor_command("MOVE,180,0,40"), "MOVE,180,0,40")

    def test_inverted_camera_rotates_linear_command_axes(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.0
        ):
            self.assertEqual(normalize_motor_command("MOVE,180,0,40"), "MOVE,-180,0,40")
            self.assertEqual(normalize_motor_command("MOVE,0,150,0"), "MOVE,0,-150,0")

    def test_curve_correction_scales_turning_component_symmetrically(self):
        # CAMERA_INVERTED precisa valer para todos os blocos: sem isso os
        # seguintes pegavam o valor real do config e negavam vx.
        with patch("raspberry.motion.CAMERA_INVERTED", False):
            with patch("raspberry.motion.CURVE_CORRECTION", 0.5):
                left_soft = normalize_motor_command("MOVE,180,0,-40")
            with patch("raspberry.motion.CURVE_CORRECTION", 1.0):
                left_default = normalize_motor_command("MOVE,180,0,-40")
            with patch("raspberry.motion.CURVE_CORRECTION", 1.5):
                left_strong = normalize_motor_command("MOVE,180,0,-40")
                right_strong = normalize_motor_command("MOVE,180,0,40")

        self.assertEqual(left_soft, "MOVE,180,0,-20")
        self.assertEqual(left_default, "MOVE,180,0,-40")
        self.assertEqual(left_strong, "MOVE,180,0,-60")
        self.assertEqual(right_strong, "MOVE,180,0,60")

    def test_curve_correction_clamps_turning_component(self):
        with patch("raspberry.motion.CAMERA_INVERTED", False), patch(
            "raspberry.motion.CURVE_CORRECTION", 10.0
        ):
            command = normalize_motor_command("MOVE,180,0,40")

        self.assertEqual(command.split(",")[3], "255")

    def test_stop_and_emergency_stop_are_never_transformed(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 10.0
        ):
            self.assertEqual(normalize_motor_command("STOP"), "STOP")
            self.assertEqual(normalize_motor_command("EMERGENCY STOP"), "EMERGENCY STOP")
            self.assertEqual(normalize_motor_command("EMERGENCY_STOP"), "EMERGENCY_STOP")

    def test_replayed_command_is_not_normalized_twice(self):
        with patch("raspberry.motion.CAMERA_INVERTED", True), patch(
            "raspberry.motion.CURVE_CORRECTION", 1.5
        ):
            command = normalize_motor_command("MOVE,180,0,20")
            app = SimpleNamespace(context=SimpleNamespace(last_command=command))
            app._is_last_command_valid = lambda: True
            self.assertEqual(RobotApp._resolve_command(app, None), command)


class MotorDeadbandTests(unittest.TestCase):
    """A faixa útil dos motores vai de 110 a 255: razão de apenas 2,3 para 1.

    Um comando cuja roda mais lenta caia abaixo de 110 não pode ser executado
    como pedido, e o firmware antigo elevava essa roda ao próprio mínimo — o que
    travava a taxa de giro a partir de wz≈40 e fazia o robô passar reto nas
    curvas de 90 graus.
    """

    def wheels(self, vx, vy, wz):
        return [round(speed) for speed in _wheel_speeds(*fit_to_motor_deadband(vx, vy, wz))]

    def test_command_already_expressible_is_untouched(self):
        self.assertEqual(fit_to_motor_deadband(180.0, 0.0, 0.0), (180.0, 0.0, 0.0))

    def test_slightly_short_command_is_amplified_keeping_the_trajectory(self):
        vx, vy, wz = fit_to_motor_deadband(145.0, 0.0, 50.0)

        self.assertAlmostEqual(vx / wz, 145.0 / 50.0, places=6)  # mesma trajetória
        self.assertTrue(all(abs(w) >= MOTOR_DEADBAND_PWM for w in self.wheels(145.0, 0.0, 50.0)))

    def test_command_below_the_motor_resolution_is_dropped(self):
        # Ampliar 22x um pedido de 5 não é a mesma trajetória mais rápida, é um
        # solavanco. Esses motores simplesmente não fazem giro fino.
        # Não vira solavanco: o comando segue pequeno e o firmware o ignora.
        self.assertTrue(all(abs(w) < MOTOR_DEADBAND_PWM for w in self.wheels(0.0, 0.0, 5.0)))

    def test_sharp_curve_sacrifices_translation_not_turn(self):
        vx, _, wz = fit_to_motor_deadband(110.0, 0.0, 125.0)

        self.assertEqual(wz, 125.0)  # a curva pedida é preservada
        self.assertLess(vx, 110.0)  # o avanço é o que cede
        self.assertTrue(all(abs(w) >= MOTOR_DEADBAND_PWM for w in self.wheels(110.0, 0.0, 125.0)))

    def test_curve_that_only_fits_as_a_pivot_becomes_a_pivot(self):
        vx, vy, wz = fit_to_motor_deadband(110.0, 0.0, 100.0)

        self.assertEqual((vx, vy), (0.0, 0.0))
        self.assertEqual(wz, MOTOR_DEADBAND_PWM)

    def test_every_line_following_command_reaches_the_motors(self):
        # Varredura do espaço que o seguidor de linha realmente emite: vx entre
        # MIN_SPEED e BASE_SPEED, mais o pivô puro. Nenhuma roda pode ficar na
        # zona morta, onde o comando não seria cumprido.
        for vx in [0] + list(range(MIN_SPEED, BASE_SPEED + 1, 5)):
            for wz in range(-125, 126, 5):
                if max(abs(w) for w in _wheel_speeds(vx, 0.0, wz)) < MOTOR_MIN_MEANINGFUL_PWM:
                    continue  # comando pequeno demais para os motores; ver teste abaixo
                with self.subTest(vx=vx, wz=wz):
                    fitted = fit_to_motor_deadband(float(vx), 0.0, float(wz))
                    wheels = _wheel_speeds(*fitted)
                    for wheel in wheels:
                        self.assertTrue(
                            abs(wheel) < 0.5 or abs(wheel) >= MOTOR_DEADBAND_PWM - 1e-6,
                            f"roda em {wheel:.0f} na zona morta para vx={vx} wz={wz}",
                        )


if __name__ == "__main__":
    unittest.main()
