import sublime, sublime_plugin
import errno, fnmatch, os, stat, threading, time

from . import logger
log = logger.getLogger(__name__)

class WatcherThread(threading.Thread):

	stop = False

	def __init__(self, folder, callback, sync_interval, files_to_include = [], files_to_ignore = [], dirs_to_ignore = []):
		self.folder = folder;
		self.callback = callback

		self.sync_interval = sync_interval
		
		self.files_to_include = files_to_include
		self.files_to_ignore = files_to_ignore
		self.dirs_to_ignore = dirs_to_ignore

		threading.Thread.__init__(self)

	def run(self):
		w = Watcher(self.folder, self.callback, self.files_to_include, self.files_to_ignore, self.dirs_to_ignore)
		while not self.stop:
			w.loop(self.sync_interval)

class Watcher(object):

	init_done = False

	def __init__(self, folder, callback, files_to_include = [], files_to_ignore = [], dirs_to_ignore = []):

		self.folder = folder;
		self.callback = callback
		
		self.files_to_include = files_to_include
		self.files_to_ignore = files_to_ignore
		self.dirs_to_ignore = dirs_to_ignore

		self.files_map = {}
		
		self.update_files()
		self.init_done = True

	def __del__(self):		
		for key, value in self.files_map.items():
			log.debug("unwatching %s" % value["path"])

	def listdir(self, walk = False):
		items = []
		for root, dir_names, file_names in os.walk(self.folder):
			[dir_names.remove(d) for d in dir_names if d in self.dirs_to_ignore]

			for file_name in file_names:
				full_path = os.path.join(root, file_name)
				rel_path = os.path.relpath(full_path, self.folder)

				include_matches = [fnmatch.fnmatch(rel_path, p) for p in self.files_to_include]
				ignore_matches = [fnmatch.fnmatch(rel_path, p) for p in self.files_to_ignore]

				if any(ignore_matches) or not any(include_matches):
					continue

				items += [{"key": rel_path, "path": full_path, "dir": os.path.dirname(rel_path), "version": os.path.getmtime(full_path)}]
		
		return items

	def loop(self, interval = 1.5):
		self.update_files()
		for key, value in self.files_map.items():
			self.check_file(key, value)
		time.sleep(interval)

	def check_file(self, key, value):
		file_mtime = os.path.getmtime(value["path"])
		if file_mtime != value["version"]:
			self.files_map[key]["version"] = file_mtime

			# Run callback if file changed
			sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": dict({"type": "m"}, **value)}), 0)

	def update_files(self):
		items = []

		for item in self.listdir():
			if item["key"] not in self.files_map:
				items += [item]
		
		# check existent files
		for key, value in self.files_map.copy().items():
			if not os.path.exists(value["path"]):
				self.unwatch(value)

		for item in items:
			if item["key"] not in self.files_map:
				self.watch(item)

	def watch(self, item):
		log.debug("watching %s" % item["path"])
		self.files_map[item["key"]] = item

		# Run callback if file created
		if self.init_done:
			sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": dict({"type": "c"}, **item)}), 0)
			

	def unwatch(self, item):
		log.debug("unwatching %s" % item["path"])
		del self.files_map[item["key"]]
		
		# Run callback if file deleted
		sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": dict({"type": "d"}, **item)}), 0)