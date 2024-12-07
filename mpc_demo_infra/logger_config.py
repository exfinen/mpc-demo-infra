import logging
import os
from logging.handlers import RotatingFileHandler

format = '%(asctime)s [%(levelname)s] %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'

def configure_console_logger():
    logging.basicConfig(
        level=logging.DEBUG,
        format=format,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(),
        ],
    )

def configure_file_console_loggers(name: str, max_bytes_mb: int, backup_count: int):
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    pid = os.getpid()
    log_file = os.path.join(log_dir, f'{name}_{pid}.log')

    mb = 1024 * 1024

    logging.basicConfig(
        level=logging.DEBUG,
        format=format,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                f'logs/{name}_{pid}.log',
                maxBytes=max_bytes_mb * mb,
                backupCount=backup_count
            ),
        ],
    )

