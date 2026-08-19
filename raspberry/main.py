import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from raspberry.camera import CameraManager
from raspberry.config import CAMERA_BACKEND, SERIAL_BAUDRATE, SERIAL_MODE, SERIAL_PORT, SERIAL_RECONNECT_DELAY, SERIAL_TIMEOUT, SENSORS_ENABLED, RobotContext
from raspberry.serial_manager import SerialManager
from raspberry.preview import PreviewWindow
from raspberry.state_machine import RobotStateMachine
from raspberry.strategy import Strategy
from raspberry.runtime import ExecutionLoopController
from raspberry.states.alignment import AlignBallState
from raspberry.telemetry import format_arduino_payload
from raspberry.states.avoid_obstacle import AvoidObstacleState
from raspberry.states.calibration import CalibrationState
from raspberry.states.capture_ball import CaptureBallState
from raspberry.states.drop_ball import DropBallState
from raspberry.states.enter_rescue import EnterRescueState
from raspberry.states.finish import FinishState
from raspberry.states.follow_line import FollowLineState
from raspberry.states.search_ball import SearchBallState
from raspberry.states.search_line import SearchLineState
from raspberry.states.search_safe_zone import SearchSafeZoneState
from raspberry.vision.ball_detector import BallDetector
from raspberry.vision.line_detector import LineDetector
from raspberry.vision.pipeline import VisionPipeline
from raspberry.vision.rescue_detector import RescueDetector
from raspberry.vision.safe_zone_detector import SafeZoneDetector
from competition.integration import CompetitionRuntimeAdapter

# ROBOT_LOG_LEVEL=DEBUG mostra, entre outras coisas, cada linha vinda do Arduino.
logging.basicConfig(level=os.environ.get("ROBOT_LOG_LEVEL", "INFO").upper(), format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class RobotApp:
    def __init__(self) -> None:
        self.camera = CameraManager(backend=CAMERA_BACKEND)
        self.serial = SerialManager(mode=SERIAL_MODE, port=SERIAL_PORT, baudrate=SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT, reconnect_delay=SERIAL_RECONNECT_DELAY)
        self.serial.connect()
        self.context = RobotContext()
        self.context.camera_ready = self.camera.is_ready()
        self.context.serial_ready = self.serial.is_connected()
        self.strategy = Strategy()
        self.competition_adapter = CompetitionRuntimeAdapter()
        self.detectors = {
            "line": LineDetector(),
            "ball": BallDetector(),
            "rescue": RescueDetector(),
            "safe_zone": SafeZoneDetector(),
        }
        self.vision_pipeline = VisionPipeline(detectors=self.detectors)
        self.machine = RobotStateMachine({
            "BOOT": CalibrationState(),
            "CALIBRATION": CalibrationState(),
            "FOLLOW_LINE": FollowLineState(),
            "SEARCH_LINE": SearchLineState(),
            "AVOID_OBSTACLE": AvoidObstacleState(),
            "ENTER_RESCUE": EnterRescueState(),
            "SEARCH_BALL": SearchBallState(),
            "ALIGN_BALL": AlignBallState(),
            "CAPTURE_BALL": CaptureBallState(),
            "SEARCH_SAFE_ZONE": SearchSafeZoneState(),
            "DROP_BALL": DropBallState(),
            "FINISH": FinishState(),
        })
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self.result_queue: queue.Queue = queue.Queue(maxsize=2)
        self._stop_event = threading.Event()
        self.last_frame = None
        # Lock para evitar race conditions entre vision_thread e main loop
        self._frame_lock = threading.Lock()
        self._last_telemetry_log = 0.0
        self._vision_fps = 0.0
        self._last_capture_at = None
        self.preview = PreviewWindow()
        logger.info("Câmera: %s | %s", self.camera.describe(), self.preview.describe_status())
        self.loop_controller = ExecutionLoopController(target_hz=20.0)
        self._vision_thread = threading.Thread(target=self._vision_loop, daemon=True)
        self._vision_thread.start()

    def run(self) -> None:
        while not self._stop_event.is_set():
            cycle_start = self.loop_controller.begin_cycle()
            try:
                self.context.camera_ready = self.camera.is_ready()
                self.context.serial_ready = self.serial.is_connected()
                self._process_messages()
                try:
                    result = self.result_queue.get_nowait()
                except queue.Empty:
                    result = None
                with self._frame_lock:
                    current_frame = self.last_frame
                if result is not None and self.loop_controller.is_result_stale(result.captured_at):
                    logger.debug("Resultado visual descartado por idade (%.0f ms)", (time.monotonic() - result.captured_at) * 1000.0)
                    result = None
                if result is not None:
                    self._update_context_from_result(result)
                    # A máquina é a fonte única de verdade; o contexto a espelha.
                    self.context.current_state = self.machine.current_state
                    decision = self.strategy.evaluate(self.context)
                    if decision.next_state:
                        # Transição reativa: obstáculo, resgate, bola.
                        self.machine.transition_to(decision.next_state)
                        self.context.current_state = self.machine.current_state
                    state_result = self.machine.run_once(self.context, current_frame, self.detectors)
                    if state_result.command:
                        self._log_telemetry(state_result.command)
                        self.serial.send_command(state_result.command)
                        self.context.last_command = state_result.command

                    competition_command = self.competition_adapter.build_command(self.context, self.machine.current_state)
                    if competition_command and not state_result.command:
                        self.serial.send_command(competition_command)
                        self.context.last_command = competition_command
                mask = getattr(self.detectors["line"], "last_mask", None) if self.preview.show_mask else None
                self.preview.render(current_frame, self.context, self.context.last_command, self._preview_stats(), mask)
                if self.preview.quit_requested:
                    logger.info("Encerramento solicitado pela janela de preview")
                    self._stop_event.set()
                self.serial.send_heartbeat()
                loop_latency_ms = (self.loop_controller.wait_for_next_cycle(cycle_start) - cycle_start) * 1000.0
                self.loop_controller.record_latency(loop_latency_ms)
            except Exception as exc:
                logger.exception("Erro inesperado no loop principal: %s", exc)
                self.serial.send_command("STOP")
                time.sleep(0.2)

    def _vision_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                frame = self.camera.read_frame()
                captured_at = time.monotonic()
                if frame is None:
                    time.sleep(0.05)
                    continue
                self._track_vision_fps(captured_at)
                with self._frame_lock:
                    self.last_frame = frame
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self.frame_queue.put_nowait(frame)
                result = self.vision_pipeline.process_frame(frame, captured_at=captured_at)
                if result is not None:
                    try:
                        self.result_queue.put_nowait(result)
                    except queue.Full:
                        try:
                            self.result_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self.result_queue.put_nowait(result)
            except Exception as exc:
                logger.debug("Falha no processamento visual: %s", exc)
                time.sleep(0.05)

    def _track_vision_fps(self, captured_at: float) -> None:
        """Média móvel da taxa real de captura, exibida no preview."""
        if self._last_capture_at is not None:
            delta = captured_at - self._last_capture_at
            if delta > 0:
                self._vision_fps = 0.8 * self._vision_fps + 0.2 * (1.0 / delta)
        self._last_capture_at = captured_at

    def _preview_stats(self) -> str:
        camera = f"{self.camera.active_backend}" if self.context.camera_ready else "SEM CAMERA"
        serial = "ok" if self.context.serial_ready else "SEM SERIAL"
        return f"cam: {camera} {self._vision_fps:.0f} fps | loop: {self.loop_controller.average_latency_ms:.0f} ms | serial: {serial}"

    def _log_telemetry(self, command: str) -> None:
        """Registra o resumo visão->Arduino.

        O loop roda a 20 Hz; escrever em stdout a cada comando inunda o console e
        adiciona latência ao controle. INFO sai no máximo 1x/s, DEBUG sai sempre.
        """
        summary = format_arduino_payload(self.context, command)
        logger.debug("Visão detectada -> Arduino: %s", summary)
        now = time.monotonic()
        if now - self._last_telemetry_log >= 1.0:
            self._last_telemetry_log = now
            logger.info("Visão detectada -> Arduino: %s", summary)

    def _update_context_from_result(self, result) -> None:
        if result is None:
            return
        detections = result.detections
        self.context.last_detections = {
            name: value for name, value in detections.items() if value is not None
        }
        self.context.rescue_detected = bool(detections.get("rescue"))
        self.context.safe_zone_detected = bool(detections.get("safe_zone"))
        ball = detections.get("ball")
        self.context.ball_detected = ball is not None
        if ball is not None:
            self.context.ball_distance = getattr(ball, "distance", None)

    def _process_messages(self) -> None:
        messages = self.serial.read_messages()
        for message in messages:
            if message == "OBSTACLE":
                self.context.obstacle_detected = True
            elif message == "BALL_CAPTURED":
                self.context.last_event = "BALL_CAPTURED"
            elif message == "BALL_DROPPED":
                self.context.last_event = "BALL_DROPPED"
            elif message.startswith("DIST,"):
                try:
                    self.context.ball_distance = float(message.split(",", 1)[1])
                except ValueError:
                    pass

    def stop(self) -> None:
        """Encerra o robô de forma limpa."""
        logger.info("Iniciando shutdown do robô...")
        self._stop_event.set()
        # Aguardar vision thread terminar (máximo 2 segundos)
        if self._vision_thread.is_alive():
            self._vision_thread.join(timeout=2.0)
        self.preview.close()
        self.camera.release()
        self.serial.close()
        logger.info("Robô encerrado com sucesso")


if __name__ == "__main__":
    app = RobotApp()
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupção do usuário detectada")
    finally:
        app.stop()
