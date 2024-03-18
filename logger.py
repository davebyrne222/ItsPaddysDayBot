import logging
from logging.handlers import RotatingFileHandler


def setup_logging(filename='logs/bot.log'):
    console_level: int = logging.INFO
    file_level: int = logging.DEBUG
    log_format: str = '[%(asctime)s - %(name)s - %(levelname)s] - %(message)s'

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # File handler
    # file_handler = logging.FileHandler(filename)
    file_handler = RotatingFileHandler(filename, maxBytes=1000000, backupCount=10)
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()
