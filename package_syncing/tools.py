import sublime, sublime_plugin

import fnmatch, json, logging, os, shutil, threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
	from . import watcher
except ValueError:
	from tools import watcher


def find_files(path):
	s = sublime.load_settings("Package Syncing.sublime-settings")
	files_to_include = s.get("files_to_include", [])
	files_to_ignore = s.get("files_to_ignore", []) + ["Package Syncing.sublime-settings", "Package Syncing.last-run"]
	dirs_to_ignore = s.get("dirs_to_ignore", [])

	logger.debug("path %s", path)
	logger.debug("files_to_include %s", files_to_include)
	logger.debug("files_to_ignore %s", files_to_ignore)
	logger.debug("dirs_to_ignore %s", dirs_to_ignore)

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

def load_last_data():
	try:
		with open(os.path.join(sublime.packages_path(), "User", "Package Syncing.last-run"), "r", encoding = "utf8") as f:
			file_json = json.load(f)
	except:
		file_json = {}

	last_local_data = file_json.get("last_local_data", {})
	last_remote_data = file_json.get("last_remote_data", {})

	return last_local_data, last_remote_data

def save_last_data(local_data, remote_data):
	try:
		file_json = {"last_local_data": local_data, "last_remote_data": remote_data}
		with open(os.path.join(sublime.packages_path(), "User", "Package Syncing.last-run"), "w", encoding = "utf8") as f:
			json.dump(file_json, f, sort_keys = True, indent = 4)
	except Exception as e:
		logger.warning("Error while saving Packages Syncing.last-run %s", e)

def push_all(override = False):
	logger.debug("push_all started with override = %s", override)

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

	local_data = find_files(local_dir)
	remote_data = find_files(remote_dir)

	# Get data of last sync
	last_local_data, last_remote_data = load_last_data()

	deleted_local_data = [key for key in last_local_data if key not in local_data]
	deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

	logger.debug("local_data: %s", local_data)
	logger.debug("remote_data: %s", remote_data)
	logger.debug("deleted_local_data: %s", deleted_local_data)
	logger.debug("deleted_remote_data: %s", deleted_remote_data)

	diff = [{"type": "d", "key": key} for key in last_local_data if key not in local_data]
	for key, value in local_data.items():
		if key in deleted_remote_data:
			pass
		elif key not in remote_data:
			diff += [dict({"type": "c", "key": key}, **value)]
		elif int(value["version"]) > int(remote_data[key]["version"]) or override:
			diff += [dict({"type": "m", "key": key}, **value)]

	for item in diff:
		push(item)

	# Set data for next last sync
	save_last_data(find_files(local_dir), find_files(remote_dir))

def push(item):
	logger.debug("push started for %s", item)

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

	# Get data of last sync
	last_local_data, last_remote_data = load_last_data()

	# Skip if file was just copied
	try:
		if item["type"] == "c" or item["type"] == "m":
			if last_remote_data[item["key"]]["version"] == item["version"]:
				logger.info("Already pushed")
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
		logger.info("Created %s", target)
		# 
		last_local_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}
		last_remote_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}

	elif item["type"] == "d":
		if os.path.isfile(target):
			os.remove(target)
			logger.info("Deleted %s",  target)
		
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
		logger.info("Updated %s", target)
		# 
		last_local_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}
		last_remote_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}

	# Set data for next last sync
	save_last_data(last_local_data, last_remote_data)
	
def pull_all(override = False):
	logger.debug("pull_all started with override = %s", override)

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

	local_data = find_files(local_dir)
	remote_data = find_files(remote_dir)

	# Get data of last sync
	last_local_data, last_remote_data = load_last_data()

	deleted_local_data = [key for key in last_local_data if key not in local_data]
	deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

	logger.debug("local_data: %s", local_data)
	logger.debug("remote_data: %s", remote_data)
	logger.debug("deleted_local_data: %s", deleted_local_data)
	logger.debug("deleted_remote_data: %s", deleted_remote_data)

	diff = [{"type": "d", "key": key} for key in last_remote_data if key not in remote_data]
	for key, value in remote_data.items():
		if key in deleted_local_data:
			pass
		elif key not in local_data:
			diff += [dict({"type": "c", "key": key}, **value)]
		elif int(value["version"]) > int(local_data[key]["version"]) or override:
			diff += [dict({"type": "m", "key": key}, **value)]

	for item in diff:
		pull(item)

	# Set data for next last sync
	save_last_data(find_files(local_dir), find_files(remote_dir))

def pull(item):
	logger.debug("pull started for %s", item)

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

	# Get data of last sync
	last_local_data, last_remote_data = load_last_data()

	# Skip if file was just copied
	try:
		if item["type"] == "c" or item["type"] == "m":
			if last_local_data[item["key"]]["version"] == item["version"]:
				logger.info("Already pulled")
				return
	except:
		pass

	# Make target file path and dir
	target = os.path.join(local_dir, item["key"])
	target_dir = os.path.dirname(target)

	if item["type"] == "c":
		if not os.path.isdir(target_dir):
			os.mkdir(target_dir)
		shutil.copy2(item["path"], target)
		logger.info("Created %s", target)
		# 
		last_local_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}
		last_remote_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}

	elif item["type"] == "d":
		if os.path.isfile(target):
			os.remove(target)
			logger.info("Deleted %s",  target)

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
		logger.info("Updated %s", target)
		# 
		last_local_data[item["key"]] = {"path": target, "dir": item["dir"], "version": item["version"]}
		last_remote_data[item["key"]] = {"path": item["path"], "dir": item["dir"], "version": item["version"]}

	# Set data for next last sync
	save_last_data(last_local_data, last_remote_data)

watcher_local = None
watcher_remote = None

def start_watcher():
	s = sublime.load_settings("Package Syncing.sublime-settings")
	local_dir = os.path.join(sublime.packages_path(), "User")
	remote_dir = s.get("sync_folder")
	# 
	files_to_include = s.get("files_to_include", [])
	files_to_ignore = s.get("files_to_ignore", []) + ["Package Syncing.sublime-settings", "Package Syncing.last-run"]
	dirs_to_ignore = s.get("dirs_to_ignore", [])
	# 
	global watcher_local
	global watcher_remote
	# 
	watcher_remote = watcher.WatcherThread(remote_dir, pull, files_to_include, files_to_ignore, dirs_to_ignore)
	watcher_remote.start()
	#
	watcher_local = watcher.WatcherThread(local_dir, push, files_to_include, files_to_ignore, dirs_to_ignore)
	watcher_local.start()

def stop_watcher():
	
	global watcher_local
	global watcher_remote

	try:
		watcher_local.stop = True
		watcher_remote.stop = True
	except:
		pass
