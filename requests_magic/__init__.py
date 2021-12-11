""" requests magic
"""

from .scheduler import Scheduler
from .item import Item
from .request import Request
from .pipeline import Pipeline, SimpleFilePipeline, SimpleConsolePipeline
from .spider import Spider
from .mmlog import logger, console_handler


