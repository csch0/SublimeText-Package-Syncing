import sublime
import sublime_plugin

import logging

LOG = False
TRACE = 9
BASIC_FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s %(funcName)s] %(message)s"

logging.addLevelName("TRACE", TRACE)


class CustomLogger(logging.Logger):

    def isEnabledFor(self, level):
        if not LOG:
            return
        return level >= self.getEffectiveLevel()

    def trace(self, msg="", *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)


def getLogger(name, level=logging.DEBUG):
    log = CustomLogger(name, level)

    # Set stream handler
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter(BASIC_FORMAT))

    log.addHandler(h)
    return log
