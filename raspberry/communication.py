from __future__ import annotations

import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import List, Optional

import serial

logger = logging.getLogger(__name__)


class SerialTransport:
    """Interface abstrata para comunicação serial USB/UART."""

    def __init__(self, mode: str = "auto", port: str = "auto", baudrate: int = 115200, timeout: float = 0.1, reconnect_delay: float = 1.0, heartbeat_interval: float = 1.0, heartbeat_timeout: float = 2.5) -> None:
        self.mode = mode.lower()
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.serial: Optional[serial.Serial] = None
        self._buffer = ""
        self._connected = False
        self._connected_lock = threading.Lock()  # Lock para proteger _connected
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._command_queue: "queue.Queue[str]" = queue.Queue(maxsize=256)
        self._event_queue: "queue.Queue[str]" = queue.Queue(maxsize=256)
        self._last_heartbeat_sent = 0.0
        self._last_message_received = 0.0
        self._active_port: Optional[str] = None
        self._active_mode: Optional[str] = None
        self._watchdog_warned = False

    def connect(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def send_command(self, command: str) -> None:
        if not command:
            return
        try:
            self._command_queue.put_nowait(command)
        except queue.Full:
            logger.debug("Fila de comandos cheia, descartando comando %s", command)

    def read_events(self) -> List[str]:
        messages: List[str] = []
        while True:
            try:
                messages.append(self._event_queue.get_nowait())
            except queue.Empty:
                break
        return messages

    def is_connected(self) -> bool:
        with self._connected_lock:
            return self._connected
    
    def _set_connected(self, value: bool) -> None:
        """Define estado de conexão de forma thread-safe."""
        with self._connected_lock:
            self._connected = value
    
    def _get_connected(self) -> bool:
        """Lê estado de conexão de forma thread-safe."""
        with self._connected_lock:
            return self._connected

    def close(self) -> None:
        self._stop_event.set()
        if self.serial and self.serial.is_open:
            self.serial.close()
        logger.info("Comunicação serial encerrada")

    def send_heartbeat(self) -> None:
        now = time.monotonic()
        if now - self._last_heartbeat_sent < self.heartbeat_interval:
            return
        self.send_command("HEARTBEAT")
        self._last_heartbeat_sent = now

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                if not self._get_connected():
                    self._connect_with_fallback()
                    if not self._get_connected():
                        time.sleep(self.reconnect_delay)
                        continue

                self._drain_command_queue()
                self._read_available_messages()
                self._check_watchdog()
                time.sleep(0.01)
            except Exception as exc:
                logger.debug("Erro na camada serial: %s", exc)
                self._set_connected(False)
                if self.serial and self.serial.is_open:
                    self.serial.close()
                self.serial = None
                time.sleep(self.reconnect_delay)

    def _connect_with_fallback(self) -> None:
        candidates = self._candidate_ports()
        for candidate in candidates:
            if self._try_connect(candidate):
                self._active_port = candidate
                self._active_mode = self._detect_mode(candidate)
                logger.info("Interface serial ativa: %s (%s)", candidate, self._active_mode)
                return
        logger.debug("Nenhuma porta serial disponível no momento; aguardando reconexão")

    def _candidate_ports(self) -> List[str]:
        configured = self.port if self.port and self.port != "auto" else None
        if configured:
            return [configured]

        candidates: List[str] = []
        if self.mode in {"auto", "usb"}:
            candidates.extend(sorted(self._list_usb_ports()))
        if self.mode in {"auto", "uart"}:
            candidates.extend(["/dev/serial0", "/dev/ttyAMA0", "/dev/ttyS0"])
        if not candidates:
            candidates.extend(["/dev/serial0", "/dev/ttyAMA0", "/dev/ttyS0"])
        return candidates

    def _list_usb_ports(self) -> List[str]:
        ports: List[str] = []
        for path in Path("/dev").iterdir():
            name = path.name
            if name.startswith("ttyACM") or name.startswith("ttyUSB"):
                ports.append(str(path))
        return ports

    def _detect_mode(self, port: str) -> str:
        if "ttyACM" in port or "ttyUSB" in port:
            return "usb"
        return "uart"

    def _try_connect(self, port: str) -> bool:
        try:
            if not os.path.exists(port):
                return False
            self.serial = serial.Serial(port, self.baudrate, timeout=self.timeout)
            time.sleep(1.0)
            self._set_connected(True)
            self._buffer = ""
            self._last_message_received = time.monotonic()
            self._last_heartbeat_sent = time.monotonic()
            return True
        except Exception as exc:
            logger.debug("Falha ao abrir %s: %s", port, exc)
            self.serial = None
            self._set_connected(False)
            return False

    def _drain_command_queue(self) -> None:
        if not self._get_connected() or self.serial is None:
            return
        while True:
            try:
                command = self._command_queue.get_nowait()
            except queue.Empty:
                break
            try:
                self.serial.write((command + "\n").encode("utf-8"))
                self.serial.flush()
                logger.debug("Comando enviado via %s: %s", self._active_port, command)
            except Exception as exc:
                logger.warning("Falha ao enviar comando: %s", exc)
                self._set_connected(False)
                self.serial.close()
                self.serial = None
                self._command_queue.put_nowait(command)
                break

    def _read_available_messages(self) -> None:
        if not self._get_connected() or self.serial is None:
            return
        try:
            if self.serial.in_waiting > 0:
                chunk = self.serial.read(self.serial.in_waiting).decode("utf-8", errors="ignore")
                self._buffer += chunk
                if chunk:
                    self._last_message_received = time.monotonic()
        except Exception as exc:
            logger.warning("Falha ao ler serial: %s", exc)
            self._set_connected(False)
            if self.serial and self.serial.is_open:
                self.serial.close()
            self.serial = None
            return

        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                try:
                    self._event_queue.put_nowait(line)
                except queue.Full:
                    self._event_queue.get_nowait()
                    self._event_queue.put_nowait(line)

    def _check_watchdog(self) -> None:
        """Avisa sobre silêncio prolongado do Arduino, sem derrubar a porta.

        Fechar e reabrir /dev/ttyACM* alterna o DTR e reinicia a placa, que fica
        ~2 s no bootloader e volta a ficar em silêncio: o próprio watchdog criava
        o silêncio que o disparava. Porta de fato morta é detectada na escrita.
        """
        if not self._get_connected():
            return
        if self.heartbeat_timeout <= 0:
            return
        silent_for = time.monotonic() - self._last_message_received
        if silent_for <= self.heartbeat_timeout:
            self._watchdog_warned = False
            return
        if not self._watchdog_warned:
            self._watchdog_warned = True
            logger.warning("Watchdog serial: %s sem resposta há %.1f s (conexão mantida)", self._active_port, silent_for)
