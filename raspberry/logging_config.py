"""Sistema de logging estruturado para o robô de competição.

Suporta múltiplos níveis: DEBUG, INFO, WARNING, ERROR.
Controlado via config.DEBUG e por variáveis de ambiente.
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from .config import DEBUG


def setup_logging(log_dir: str = "/tmp", log_file: str = "robot_competition.log", level: str | None = None) -> None:
    """Configura o sistema de logging estruturado.
    
    Args:
        log_dir: Diretório para arquivos de log
        log_file: Nome do arquivo de log
        level: Nível de log (DEBUG, INFO, WARNING, ERROR) ou None para usar config.DEBUG
    
    Exemplos:
        setup_logging()  # Usa config.DEBUG
        setup_logging(level="WARNING")  # Apenas warnings e erros
    """
    
    # Determinar nível a partir do argumento ou config.DEBUG
    if level is None:
        level = "DEBUG" if DEBUG else "INFO"
    
    level = level.upper()
    
    # Criar logger raiz
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # Logger capta tudo, handlers filtram
    
    # Remover handlers anteriores
    logger.handlers.clear()
    
    # Formato detalhado para debug, simples para produção
    if DEBUG:
        fmt = "%(asctime)s [%(levelname)s] %(name)s:%(funcName)s():%(lineno)d - %(message)s"
    else:
        fmt = "%(asctime)s [%(levelname)s] %(message)s"
    
    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Handler para console (stderr)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo (se aplicável)
    try:
        log_path = Path(log_dir) / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_path),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)  # Arquivo sempre captura DEBUG
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as exc:
        console_handler.warning("Não foi possível configurar logging em arquivo: %s", exc)
    
    # Reduzir verbosidade de bibliotecas externas
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("serial").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Obtém um logger para um módulo específico.
    
    Args:
        name: Nome do logger (normalmente __name__)
    
    Returns:
        Logger configurado
    """
    return logging.getLogger(name)


# Configurar logging ao importar
setup_logging()
