import logging
import sys


def get_logger(logger_name):
    log = logging.getLogger(logger_name)
    log.setLevel(logging.INFO)
    outputhandler = logging.StreamHandler(stream=sys.stdout)
    outputhandler.setFormatter(
        logging.Formatter(
            fmt=" %(asctime)s [%(name)s](%(levelname)s) - %(message)s"))
    log.addHandler(outputhandler)
    return log