import logging

Logger = logging.getLogger("RequestsMagic")
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s\t %(message)s"))
sh.setLevel(logging.INFO)
Logger.addHandler(sh)
Logger.setLevel(logging.INFO)


def LoggerLevel(level):
    Logger.setLevel(level)
    sh.setLevel(level)
