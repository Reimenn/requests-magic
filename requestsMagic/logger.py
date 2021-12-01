import logging

logger = logging.getLogger("RequestsMagic")
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s\t %(message)s"))
sh.setLevel(logging.INFO)
logger.addHandler(sh)
logger.setLevel(logging.INFO)


def LoggerLevel(level):
    logger.setLevel(level)
    sh.setLevel(level)
