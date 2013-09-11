import logging

TRACE = 9

logging.addLevelName("TRACE", TRACE)

BASIC_FORMAT = "[%(asctime)s - %(levelname)s - %(name)s::%(funcName)s] %(message)s"

class CustomLogger(logging.Logger):

	def trace(self, msg = "", *args, **kwargs):
		self._log(TRACE, msg, args, **kwargs)

def getLogger(name, level = logging.INFO):
	log = CustomLogger(name, level)
	
	# Set stream handler
	h = logging.StreamHandler()
	h.setFormatter(logging.Formatter(BASIC_FORMAT))

	log.addHandler(h)
	return log