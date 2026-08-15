import logging
from json import load
from logging.config import dictConfig
from os import path

LOGGER_PATH = path.join(path.dirname(__file__), "loggers.json")
PROJECT_ROOT = path.dirname(path.dirname(__file__))
APP_LOG_PATH = path.join(PROJECT_ROOT, "app.log")


class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[38;2;162;103;223m",  # Light Purple (underlined optional)
        logging.INFO: "\033[38;2;162;103;223m",  # Light Purple
        logging.WARNING: "\033[38;2;0;0;139m\033[1m",  # Bold Dark Blue
        logging.ERROR: "\033[38;2;255;0;0m",  # Red
        logging.CRITICAL: "\033[38;2;139;0;0m\033[1m",  # Bold Dark Red
    }

    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        reset = self.RESET

        # Customize per-level output
        if record.levelno == logging.ERROR:
            fmt = f"{color}%(levelname)s{reset}: (%(filename)s):    \033[1m%(message)s{reset}"
        elif record.levelno == logging.CRITICAL:
            fmt = f"{color}%(levelname)s{reset}: (%(filename)s):     {color}%(message)s{reset}"
        elif record.levelno == logging.DEBUG:
            fmt = f"{color}%(levelname)s{reset}:     \033[4m%(message)s{reset}"
        elif record.levelno == logging.WARNING:
            fmt = f"{color}%(levelname)s{reset}:    \033[1m%(message)s{reset}"
        else:  # INFO and default
            fmt = f"{color}%(levelname)s{reset}:     \033[37m%(message)s{reset}"

        self._style._fmt = fmt
        return super().format(record)


def setup_logging():
    with open(LOGGER_PATH, encoding="utf-8") as loggers:
        config = load(loggers)

    config["handlers"]["file"]["filename"] = APP_LOG_PATH
    dictConfig(config)
