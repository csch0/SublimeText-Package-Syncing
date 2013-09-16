import sublime, sublime_plugin

class Queue(object):

	current = None
	pool = []

	def __init__(self):
		pass

	def start(self):
		# Clear old thread
		if self.current and self.current["thread"].is_alive():
			sublime.set_timeout(lambda: self.start(), 500)

		else:
			# Reset current thread, since it ended
			self.current = None
			
			# Check for elements in pool
			if self.pool:
				self.current = self.pool.pop(0)
				self.current["thread"].start()
				
				# Attemp a new start of the thread
				sublime.set_timeout(lambda: self.start(), 500)			
		
	def has(self, key):
		pool = self.pool + [self.current] if self.current else []
		return any([item for item in pool if item["key"] == key])

	def add(self, thread, key = None):
		self.pool += [{"key": key if key else thread.name, "thread": thread}]
		self.start()
