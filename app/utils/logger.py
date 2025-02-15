import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_loggers = {}

class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self, fmt: str):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_log_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")


def setup_logging(base_log_path: str, module_name: Optional[str] = None, console_output: bool = False) -> logging.Logger:
    global _loggers
    
    os.makedirs(base_log_path, exist_ok=True)
    
    logger_name = module_name if module_name else "root"
    
    if logger_name in _loggers:
        return _loggers[logger_name]
        
    log_file = os.path.join(base_log_path, f"{logger_name}.log")
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    logger.handlers.clear()
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(console_handler)
    
    logger.propagate = False
    
    _loggers[logger_name] = logger
    return logger


def get_logger(name: str, console_output: bool = False) -> logging.Logger:
    if name not in _loggers:
        log_path = get_log_path()
        return setup_logging(log_path, name, console_output)
    return _loggers[name]


def setup_profile_logger(profile_path: str) -> logging.Logger:
    logger_name = f"profile_{os.path.basename(profile_path)}"
    log_file = os.path.join(profile_path, "profile.log")
    
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    
    logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.propagate = False
    
    return logger