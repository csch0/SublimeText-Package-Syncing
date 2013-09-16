import sublime, sublime_plugin
import fnmatch, functools, os, time, threading, shutil

from . import logger, tools, watcher
log = logger.getLogger(__name__)

class Sync(threading.Thread):

	def __init__(self, settings, mode = ["pull", "push"], override = False, item = None):
		
		self.settings = settings
		self.mode = mode
		self.item = item
		self.override = override

		threading.Thread.__init__(self)

	def run(self):
		sync_interval = self.settings.get("sync_interval", 1)

		# If no item pull and push all
		if not self.item:
			
			print("Package Syncing: Start Complete Sync")
			
			# Stop watcher and wait for the poll
			tools.stop_watcher()
			time.sleep(sync_interval + 0.5)
		
			# Fetch all items from the remote location
			if "pull" in self.mode:
				self.pull_all()
			
			# Push all items to the remote location
			if "push" in self.mode:
				self.push_all()

			# Restart watcher again
			tools.start_watcher(self.settings)

			print("Package Syncing: End Complete Sync")
		
		else:

			# Pull the selected item
			if "pull" in self.mode:
				self.pull(self.item)

			# Push the selected item
			if "push" in self.mode:
				self.push(self.item)

	def find_files(self, path):
		log.debug("find_files started for %s", path)
		
		files_to_include = self.settings.get("files_to_include", [])
		files_to_ignore = self.settings.get("files_to_ignore", []) + ["Package Syncing.sublime-settings", "Package Syncing.last-run"]
		dirs_to_ignore = self.settings.get("dirs_to_ignore", [])

		log.debug("path %s" % path)
		log.debug("files_to_include %s" % files_to_include)
		log.debug("files_to_ignore %s" % files_to_ignore)
		log.debug("dirs_to_ignore %s" % dirs_to_ignore)

		resources = {}
		for root, dir_names, file_names in os.walk(path):
			[dir_names.remove(dir) for dir in dir_names if dir in dirs_to_ignore]

			for file_name in file_names:
				full_path = os.path.join(root, file_name)
				rel_path = os.path.relpath(full_path, path)

				include_matches = [fnmatch.fnmatch(rel_path, p) for p in files_to_include]
				ignore_matches = [fnmatch.fnmatch(rel_path, p) for p in files_to_ignore]
				if any(ignore_matches) or not any(include_matches):
					continue

				resources[rel_path] = {"version": os.path.getmtime(full_path), "path": full_path, "dir": os.path.dirname(rel_path)}

		return resources

	def pull_all(self):
		log.debug("pull_all started with override = %s" % self.override)

		local_dir = os.path.join(sublime.packages_path(), "User")
		remote_dir = self.settings.get("sync_folder")

		local_data = self.find_files(local_dir)
		remote_data = self.find_files(remote_dir)

		# Get data of last sync
		last_local_data, last_remote_data = tools.load_last_data()

		deleted_local_data = [key for key in last_local_data if key not in local_data]
		deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

		log.debug("local_data: %s" % local_data)
		log.debug("remote_data: %s" % remote_data)
		log.debug("deleted_local_data: %s" % deleted_local_data)
		log.debug("deleted_remote_data: %s" % deleted_remote_data)

		diff = [{"type": "d", "key": key} for key in last_remote_data if key not in remote_data]
		for key, value in remote_data.items():
			if key in deleted_local_data:
				pass
			elif key not in local_data:
				diff += [dict({"type": "c", "key": key}, **value)]
			elif int(value["version"]) > int(local_data[key]["version"]) or self.override:
				diff += [dict({"type": "m", "key": key}, **value)]

		for item in diff:
			self.pull(item)

		# Set data for next last sync
		tools.save_last_data(self.find_files(local_dir), self.find_files(remote_dir))

	def pull(self, item):
		log.debug("pull started for %s" % item)

		local_dir = os.path.join(sublime.packages_path(), "User")
		remote_dir = self.settings.get("sync_folder")

		# Get data of last sync
		last_local_data, last_remote_data = tools.load_last_data()

		# Make target file path and directory
		target = os.path.join(local_dir, item["key"])
		target_dir = os.path.dirname(target)

		# Skip if file was just pushed
		try:
			if item["type"] == "c" or item["type"] == "m":
				
				# Check for an updated Package Control setting file and backup old file
				if item["key"] == "Package Control.sublime-settings":
					previous_installed_packages = tools.load_installed_packages(target)

				# Check if the watcher detects a file again
				if last_local_data[item["key"]]["version"] == item["version"]:
					log.debug("Already pulled")
					return
		except:
			pass

		# If a file was created
		if item["type"] == "c":

			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(item["path"], target)
			log.info("Created %s" % target)
			if not log.isEnabledFor(logger.logging.INFO):
				print("Package Syncing: Created %s" % target)
			# 
			last_local_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}
			last_remote_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}

		# If a file was delated
		elif item["type"] == "d":
			if os.path.isfile(target):
				os.remove(target)
				log.info("Deleted %s" % target)
				if not log.isEnabledFor(logger.logging.INFO):
					print("Package Syncing: Deleted %s" % target)

			try:
				del last_local_data[item["key"]]
				del last_remote_data[item["key"]]
			except:
				pass
			
			# Check if directory is empty and remove it if, just cosmetic issue
			if os.path.isdir(target_dir) and not os.listdir(target_dir):
				os.rmdir(target_dir)

		# If a file was modified
		elif item["type"] == "m":
			
			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(item["path"], target)
			log.info("Updated %s" % target)
			if not log.isEnabledFor(logger.logging.INFO):
				print("Package Syncing: Updated %s" % target)
			# 
			last_local_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}
			last_remote_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}

		# Set data for next last sync
		tools.save_last_data(last_local_data, last_remote_data)

		if item["key"] == "Package Control.sublime-settings":
			# Handle Package Control
			sublime.set_timeout(functools.partial(tools.package_control, previous_installed_packages), 1000)

	def push_all(self):
		log.debug("push_all started with override = %s" % self.override)

		s = sublime.load_settings("Package Syncing.sublime-settings")
		local_dir = os.path.join(sublime.packages_path(), "User")
		remote_dir = s.get("sync_folder")

		if not s.get("sync"):
			return

		if not os.path.isdir(remote_dir):
			sublime.error_message("Invalid sync folder \"%s\", sync disabled! Please adjust your sync folder." % remote_dir)
			s.set("sync", False)
			sublime.save_settings("Package Syncing.sublime-settings")
			return

		local_data = self.find_files(local_dir)
		remote_data = self.find_files(remote_dir)

		# Get data of last sync
		last_local_data, last_remote_data = tools.load_last_data()

		deleted_local_data = [key for key in last_local_data if key not in local_data]
		deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

		log.debug("local_data: %s" % local_data)
		log.debug("remote_data: %s" % remote_data)
		log.debug("deleted_local_data: %s" % deleted_local_data)
		log.debug("deleted_remote_data: %s" % deleted_remote_data)

		diff = [{"type": "d", "key": key} for key in last_local_data if key not in local_data]
		for key, value in local_data.items():
			if key in deleted_remote_data:
				pass
			elif key not in remote_data:
				diff += [dict({"type": "c", "key": key}, **value)]
			elif int(value["version"]) > int(remote_data[key]["version"]) or self.override:
				diff += [dict({"type": "m", "key": key}, **value)]

		for item in diff:
			self.push(item)

		# Set data for next last sync
		tools.save_last_data(self.find_files(local_dir), self.find_files(remote_dir))

	def push(self, item):
		log.debug("push started for %s" % item)

		local_dir = os.path.join(sublime.packages_path(), "User")
		remote_dir = self.settings.get("sync_folder")

		# Get data of last sync
		last_local_data, last_remote_data = tools.load_last_data()

		# Skip if file was just copied
		try:
			if item["type"] == "c" or item["type"] == "m":
				if last_remote_data[item["key"]]["version"] == item["version"]:
					log.debug("Already pushed")
					return
		except:
			pass

		# Make target file path and dir
		target = os.path.join(remote_dir, item["key"])
		target_dir = os.path.dirname(target)

		if item["type"] == "c":
			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(item["path"], target)
			log.info("Created %s" % target)
			if not log.isEnabledFor(logger.logging.INFO):
				print("Package Syncing: Created %s" % target)
			# 
			last_local_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}
			last_remote_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}

		elif item["type"] == "d":
			if os.path.isfile(target):
				os.remove(target)
				log.info("Deleted %s" % target)
				if not log.isEnabledFor(logger.logging.INFO):
					print("Package Syncing: Deleted %s" % target)
			
			try:
				del last_local_data[item["key"]]
				del last_remote_data[item["key"]]
			except:
				pass
			
			# Check if dir is empty and remove it if
			if os.path.isdir(target_dir) and not os.listdir(target_dir):
				os.rmdir(target_dir)

		elif item["type"] == "m":
			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(item["path"], target)
			log.info("Updated %s" % target)
			if not log.isEnabledFor(logger.logging.INFO):
				print("Package Syncing: Updated %s" % target)
			# 
			last_local_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}
			last_remote_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}

		# Set data for next last sync
		tools.save_last_data(last_local_data, last_remote_data)

