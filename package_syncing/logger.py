import sublime, sublime_plugin
import logging

TRACE = 9

logging.addLevelName("TRACE", TRACE)

BASIC_FORMAT = "[%(asctime)s - %(levelname)s - %(filename)s %(funcName)s] %(message)s"

class CustomLogger(logging.Logger):

	def isEnabledFor(self, level):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		if not s.get("log", False):
			return
		return level >= self.getEffectiveLevel()

	def trace(self, msg = "", *args, **kwargs):
		if self.isEnabledFor(TRACE):
			self._log(TRACE, msg, args, **kwargs)

def getLogger(name, level = logging.DEBUG):
	log = CustomLogger(name, level)
	
	# Set stream handler
	h = logging.StreamHandler()
	h.setFormatter(logging.Formatter(BASIC_FORMAT))

	log.addHandler(h)
	return log