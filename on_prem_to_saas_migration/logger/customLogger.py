import logging
from logger import customFormatter
from logger import fileFormatter
from datetime import date
import os

class Logger:
    def __init__(self):
        today = date.today()
        if not os.path.exists("logger/logs/"):
            os.makedirs("logger/logs")
            
        self.file_name = f'logger/logs/{today}.txt'
        self.cli_logger = self.get_cli_logger("migration-cli-logger")
        self.file_logger = self.get_file_logger("migration-file-logger")

    def get_cli_logger(self, logger_name):
        cli_logger = logging.getLogger(logger_name)
        cli_logger.setLevel(logging.DEBUG)

        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        ch.setFormatter(customFormatter.CustomFormatter())
        cli_logger.addHandler(ch)

        return cli_logger
    
    def get_file_logger(self, logger_name):
        file_logger = logging.getLogger(logger_name)
        file_logger.setLevel(logging.DEBUG)

        
        fh = logging.FileHandler(self.file_name)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fileFormatter.FileFormatter())
        file_logger.addHandler(fh)

        return file_logger

    def info(self, text, file_only = False):
        self.file_logger.info(text)
        if not file_only:
            self.cli_logger.info(text)
        else:
            self.cli_logger.debug(f'Data printed in file {self.file_name}')

    def debug(self, text, file_only = False):
        self.file_logger.debug(text)
        if not file_only:
            self.cli_logger.debug(text)
        else:
            self.cli_logger.debug(f'Data printed in file {self.file_name}')

    def warn(self, text, file_only = False):
        self.file_logger.warning(text)
        if not file_only:
            self.cli_logger.warning(text)
        else:
            self.cli_logger.debug(f'Data printed in file {self.file_name}')

    def error(self, text, file_only = False):
        self.file_logger.error(text)
        if not file_only:
            self.cli_logger.error(text)
        else:
            self.cli_logger.debug(f'Data printed in file {self.file_name}')

    def critical(self, text, file_only = False):
        self.file_logger.critical(text)
        if not file_only:
            self.cli_logger.critical(text)
        else:
            self.cli_logger.debug(f'Data printed in file {self.file_name}')
    