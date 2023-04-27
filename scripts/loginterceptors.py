import logging
import sys


class UpgradeWarningToErrorFilter(logging.Filter):
    def filter(self, record):
        if record.levelno == logging._nameToLevel["WARN"]:
            record.levelno = logging._nameToLevel["ERROR"]
            record.levelname = logging.getLevelName(record.levelno)
        return True


class FailOnErrorHandler(logging.Handler):
    def filter(self, record):
        if record.levelno == logging._nameToLevel["ERROR"]:
            sys.exit(1)
