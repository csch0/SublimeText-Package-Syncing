import sublime, sublime_plugin

import fnmatch, logging, os, shutil, threading

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
	from .st2 import *
except ValueError:
	from st2 import *

PKG_SYNC_TIMER = None
PKG_SYNC_QUEUE = []

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

def push_settings():
	logger.debug("push_settings started")

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
	last_data = sublime.load_settings("Package Syncing.last-run")
	last_local_data = last_data.get("local_data", {})
	last_remote_data = last_data.get("remote_data", {})

	deleted_local_data = [key for key in last_local_data if key not in local_data]
	deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

	logger.debug("local_data: %s", local_data)
	logger.debug("remote_data: %s", remote_data)
	logger.debug("deleted_local_data: %s", deleted_local_data)
	logger.debug("deleted_remote_data: %s", deleted_remote_data)

	diff = [{"type": "d", "target": os.path.join(remote_dir, key)} for key in last_local_data if key not in local_data]
	for key, value in local_data.items():
		if key in deleted_remote_data:
			pass
		elif key not in remote_data:
			diff += [{"type": "n", "target": os.path.join(remote_dir, key), "source": value["path"]}]
		elif int(value["version"]) > int(remote_data[key]["version"]):
			diff += [{"type": "u", "target": os.path.join(remote_dir, key), "source": value["path"]}]

	# Apply diff for push
	for item in diff:
		logger.debug("%s", item)
		if item["type"] == "d":
			if os.path.isfile(item["target"]):
				os.remove(item["target"])
				logger.info("Deleted %s",  item["target"])
		elif item["type"] == "n":
			if not os.path.isdir(os.path.dirname(item["target"])):
				os.mkdir(os.path.dirname(item["target"]))
			shutil.copy2(item["source"], item["target"])
			logger.info("Created %s", item["target"])
		elif item["type"] == "u":
			if not os.path.isdir(os.path.dirname(item["target"])):
				os.mkdir(os.path.dirname(item["target"]))
			shutil.copy2(item["source"], item["target"])
			logger.info("Updated %s", item["target"])

	# Set data for next last sync
	last_data.set("local_data", local_data)
	last_data.set("remote_data", find_files(remote_dir))
	sublime.save_settings("Package Syncing.last-run")

def pull_settings(override = False):
	logger.debug("sync_pull started with override = %s", override)

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

	clear_on_change_listener()

	local_data = find_files(local_dir)
	remote_data = find_files(remote_dir)

	# Get data of last sync
	last_data = sublime.load_settings("Package Syncing.last-run")
	last_local_data = last_data.get("local_data", {})
	last_remote_data = last_data.get("remote_data", {})

	deleted_local_data = [key for key in last_local_data if key not in local_data]
	deleted_remote_data = [key for key in last_remote_data if key not in remote_data]

	logger.debug("local_data: %s", local_data)
	logger.debug("remote_data: %s", remote_data)
	logger.debug("deleted_local_data: %s", deleted_local_data)
	logger.debug("deleted_remote_data: %s", deleted_remote_data)

	diff = [{"type": "d", "target": os.path.join(local_dir, key)} for key in last_remote_data if key not in remote_data]
	for key, value in remote_data.items():
		if key in deleted_local_data:
			pass
		elif key not in local_data:
			diff += [{"type": "n", "target": os.path.join(local_dir, key), "source": value["path"]}]
		elif int(value["version"]) > int(local_data[key]["version"]):
			diff += [{"type": "u", "target": os.path.join(local_dir, key), "source": value["path"]}]
		elif override:
			diff += [{"type": "o", "target": os.path.join(local_dir, key), "source": value["path"]}]

	# Apply diff for pull
	for item in diff:
		logger.debug("%s", item)
		if item["type"] == "d":
			if os.path.isfile(item["target"]):
				os.remove(item["target"])
				logger.info("Deleted %s",  item["target"])
		elif item["type"] == "n":
			if not os.path.isdir(os.path.dirname(item["target"])):
				os.mkdir(os.path.dirname(item["target"]))
			shutil.copy2(item["source"], item["target"])
			logger.info("Created %s", item["target"])
		elif item["type"] == "u":
			if not os.path.isdir(os.path.dirname(item["target"])):
				os.mkdir(os.path.dirname(item["target"]))
			shutil.copy2(item["source"], item["target"])
			logger.info("Updated %s", item["target"])

	# Set data for next last sync
	last_data.set("local_data", find_files(local_dir))
	last_data.set("remote_data", remote_data)
	sublime.save_settings("Package Syncing.last-run")

	add_on_change_listener()

def do_sync():
	global PKG_SYNC_QUEUE
	
	logger.debug("on_done %s", PKG_SYNC_QUEUE)
	for item in PKG_SYNC_QUEUE:
		for mode in item.split(".", 1)[0].split("|"):
			if "pull" in mode:
				pull_settings(item.split(".", 2)[1] == "True")
			if "push" in mode:
				push_settings()

	PKG_SYNC_QUEUE = []

def sync(check_last_run = True, mode = ["pull", "push"], override = False):
	global PKG_SYNC_TIMER
	global PKG_SYNC_QUEUE
	
	logger.debug("sync %s %s %s", check_last_run, mode, override)
	
	# Save mode_string
	mode_string = "%s.%s" % ("|".join(mode), override)
	if mode_string not in PKG_SYNC_QUEUE:
		PKG_SYNC_QUEUE += [mode_string]

	if check_last_run:
		if not PKG_SYNC_TIMER or not PKG_SYNC_TIMER.is_alive():
			s = sublime.load_settings("Package Syncing.sublime-settings")
			sync_interval = s.get("sync_interval", 10)

			# Start the timer
			PKG_SYNC_TIMER = threading.Timer(sync_interval, do_sync)
			PKG_SYNC_TIMER.start()
	else:
		do_sync()

def find_settings(user = False):
	settings = []
	for item in find_resources("*.sublime-settings"):
		file_name = os.path.basename(item)
		if user:
			if item[8:14] == "/User/" and file_name not in ["Package Syncing.sublime-settings"]:
				settings += [file_name]
		else:
			if item[8:14] != "/User/" and file_name not in ["Package Syncing.sublime-settings"]:
				settings += [file_name]
	return settings

def add_on_change_listener():
	for name in find_settings():
		# logger.debug("add_on_change_listener %s", name)
		s = sublime.load_settings(name)
		s.clear_on_change("package_sync")
		s.add_on_change("package_sync", push_settings)

def clear_on_change_listener():
	for name in find_settings():
		# logger.debug("clear_on_change_listener %s", name)
		s = sublime.load_settings(name)
		s.clear_on_change("package_sync")
