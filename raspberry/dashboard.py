"""Dashboard de monitoramento para o robô em tempo real.

Exibe informações via interface de curses (terminal):
- Estado atual do robô
- FPS da câmera e processamento
- Uso de CPU e memória
- Status da conexão serial
- Último comando e resposta
- Erros recentes

O dashboard é desabilitado automaticamente quando DEBUG=False.
"""

import curses
import logging
import time
from collections import deque
from typing import Optional

from .config import DEBUG

logger = logging.getLogger(__name__)


class MonitoringDashboard:
    """Dashboard de monitoramento em curses (terminal UI)."""

    def __init__(self, enabled: bool = DEBUG, update_rate: float = 1.0):
        """Inicializa o dashboard.
        
        Args:
            enabled: Se False, dashboard não faz nada
            update_rate: Frequência de atualização em Hz (padrão 1 Hz = baixo overhead)
        """
        self.enabled = enabled and DEBUG
        self.update_rate = update_rate
        self._last_update = time.monotonic()
        
        # Buffer de eventos para exibição
        self._errors = deque(maxlen=5)
        self._events = deque(maxlen=10)
        
        # Métricas
        self._camera_fps = 0.0
        self._process_fps = 0.0
        self._cpu_percent = 0.0
        self._mem_percent = 0.0
        self._last_command = ""
        self._last_response = ""
        self._current_state = "BOOT"
        self._serial_connected = False
        
        # Janela curses (inicializada em update() se necessário)
        self._stdscr: Optional[object] = None
        self._initialized = False
    
    def update(self, app_context: dict) -> None:
        """Atualiza o dashboard com informações da aplicação.
        
        Args:
            app_context: Dicionário contendo:
                - current_state: Estado atual
                - camera_fps: FPS da câmera
                - process_fps: FPS de processamento
                - cpu_percent: Uso de CPU (%)
                - mem_percent: Uso de memória (%)
                - serial_connected: Conexão serial OK
                - last_command: Último comando
                - last_response: Última resposta
        """
        if not self.enabled:
            return
        
        now = time.monotonic()
        if now - self._last_update < 1.0 / self.update_rate:
            return
        
        self._last_update = now
        
        # Atualizar métricas
        self._current_state = app_context.get("current_state", "UNKNOWN")
        self._camera_fps = app_context.get("camera_fps", 0.0)
        self._process_fps = app_context.get("process_fps", 0.0)
        self._cpu_percent = app_context.get("cpu_percent", 0.0)
        self._mem_percent = app_context.get("mem_percent", 0.0)
        self._serial_connected = app_context.get("serial_connected", False)
        self._last_command = app_context.get("last_command", "")
        self._last_response = app_context.get("last_response", "")
    
    def record_error(self, error: str) -> None:
        """Registra um erro para exibição no dashboard."""
        if self.enabled:
            self._errors.append((time.monotonic(), error))
    
    def record_event(self, event: str) -> None:
        """Registra um evento para exibição no dashboard."""
        if self.enabled:
            self._events.append((time.monotonic(), event))
    
    def render(self, stdscr) -> None:
        """Renderiza o dashboard (chamado pelo loop curses).
        
        Este método é chamado por uma janela curses externa.
        Em produção (DEBUG=False), é um no-op.
        
        Args:
            stdscr: Objeto curses window
        """
        if not self.enabled:
            return
        
        try:
            h, w = stdscr.getmaxyx()
            
            stdscr.clear()
            
            # Cabeçalho
            header = f"ROBÔ OBR 2026 - {self._current_state}"
            stdscr.addstr(0, (w - len(header)) // 2, header, curses.A_BOLD)
            
            # Métricas
            y = 2
            stdscr.addstr(y, 0, f"FPS Câmera: {self._camera_fps:.1f} | FPS Proc: {self._process_fps:.1f}")
            y += 1
            stdscr.addstr(y, 0, f"CPU: {self._cpu_percent:.1f}% | Mem: {self._mem_percent:.1f}%")
            y += 1
            status = "✓ CONECTADO" if self._serial_connected else "✗ DESCONECTADO"
            stdscr.addstr(y, 0, f"Serial: {status}")
            
            # Último comando/resposta
            y += 2
            stdscr.addstr(y, 0, "Último Comando:")
            y += 1
            stdscr.addstr(y, 0, f"  {self._last_command[:w-4]}")
            y += 1
            stdscr.addstr(y, 0, "Última Resposta:")
            y += 1
            stdscr.addstr(y, 0, f"  {self._last_response[:w-4]}")
            
            # Erros recentes
            if self._errors:
                y += 2
                stdscr.addstr(y, 0, "Erros Recentes:", curses.A_BOLD)
                y += 1
                for ts, error in self._errors:
                    age = int(time.monotonic() - ts)
                    stdscr.addstr(y, 0, f"  [{age}s] {error[:w-8]}")
                    y += 1
            
            stdscr.refresh()
        except Exception as exc:
            logger.debug("Erro ao renderizar dashboard: %s", exc)
    
    def get_status_line(self) -> str:
        """Retorna uma linha de status em texto puro (para logging sem curses).
        
        Útil para registrar status em log files.
        """
        return (
            f"State={self._current_state} | "
            f"CamFPS={self._camera_fps:.1f} | "
            f"ProcFPS={self._process_fps:.1f} | "
            f"CPU={self._cpu_percent:.1f}% | "
            f"Mem={self._mem_percent:.1f}% | "
            f"Serial={'OK' if self._serial_connected else 'FAIL'}"
        )


# Instância global
_dashboard: Optional[MonitoringDashboard] = None


def get_dashboard() -> MonitoringDashboard:
    """Obtém ou cria a instância global do dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard
