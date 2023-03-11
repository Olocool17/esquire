import logging
import sys

log_handler = logging.StreamHandler(stream=sys.stdout)
log_formatter = logging.Formatter(fmt=" %(asctime)s [%(name)s](%(levelname)s) - %(message)s")
log_handler.setFormatter(log_formatter)

def get_logger(logger_name):
    log = logging.getLogger(logger_name)
    log.setLevel(logging.INFO)
    log.addHandler(log_handler)
    return log