import logging
from typing import List

from .communication import SerialTransport

logger = logging.getLogger(__name__)


class SerialManager(SerialTransport):
    """Compatibilidade com a interface antiga do projeto."""

    def read_messages(self) -> List[str]:
        return self.read_events()
