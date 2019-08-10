# coding:utf-8
import logging.handlers
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger
from config import slack_token


if __name__ == '__main__':
    logger = getLogger(__name__)
    handler_format = Formatter('[%(asctime)s][%(name)s][%(levelname)s]-%(message)s')
    fh = logging.handlers.TimedRotatingFileHandler(
        filename='log/system.log',
        when='midnight',
        encoding='utf-8',
        backupCount=20
    )
    fh.setFormatter(handler_format)
    logger.addHandler(fh)
    sh = StreamHandler()
    sh.setLevel(DEBUG)
    sh.setFormatter(handler_format)
    logger.addHandler(sh)
    logger.setLevel(DEBUG)
    logger.propagate = False
    logger.info("Start-UP")
