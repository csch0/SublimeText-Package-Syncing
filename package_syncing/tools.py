import sublime, sublime_plugin

import fnmatch, os, shutil

try:
	from .debug import logger
	from .st2 import *
except ValueError:
	from st2 import *
	from debug import logger

def find_files(path):
	s = sublime.load_settings("Package Syncing.sublime-settings")
	include_pattern = s.get("include_pattern", [])
	ignore_pattern = s.get("ignore_pattern", []) + ["Package Syncing.sublime-settings"]

	logger(1, "include_pattern", include_pattern)
	logger(1, "ignore_pattern", ignore_pattern)

	resources = {}
	for root, dir_names, file_names in os.walk(path):
		for file_name in file_names:
			full_path = os.path.join(root, file_name)
			rel_path = os.path.relpath(full_path, path)

			# files_to_ignore
			if any([fnmatch.fnmatch(rel_path, p) for p in ignore_pattern]):
				continue

			# include_pattern
			if not any([fnmatch.fnmatch(rel_path, p) for p in include_pattern]):
				continue

			resources[rel_path] = {"version": os.path.getmtime(full_path), "path": full_path, "dir": os.path.dirname(rel_path)}

	return resources


def sync_push():
	s = sublime.load_settings("Package Syncing.sublime-settings")
	local_dir = os.path.join(sublime.packages_path(), "User")
	remote_dir = s.get("sync_folder")

	if not s.get("sync"):
		return

	if not os.path.isdir(remote_dir):
		sublime.status_message("Invalid Sync Folder \"%s\"" % remote_dir)
		return

	local_data = find_files(local_dir)
	remote_data = find_files(remote_dir)

	logger(2, local_data)
	logger(2, remote_data)

	for key, value in local_data.items():
		if key not in remote_data or int(value["version"]) > int(remote_data[key]["version"]):
			target_dir = os.path.join(remote_dir, value["dir"])
			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(value["path"], target_dir)
			# Debug
			logger(0, "%s --> %s" % (key, target_dir))
			logger(1, "%s <-> %s" % (value["version"], remote_data[key]["version"] if key in remote_data else "None"))


def sync_pull(override = False):
	s = sublime.load_settings("Package Syncing.sublime-settings")
	local_dir = os.path.join(sublime.packages_path(), "User")
	remote_dir = s.get("sync_folder")

	if not s.get("sync"):
		return

	if not os.path.isdir(remote_dir):
		sublime.status_message("Invalid Sync Folder \"%s\"" % remote_dir)
		return

	clear_on_change_listener()

	local_data = find_files(local_dir)
	remote_data = find_files(remote_dir)

	logger(2, local_data)
	logger(2, remote_data)

	for key, value in remote_data.items():
		if key not in local_data or int(value["version"]) > int(local_data[key]["version"]) or override:
			target_dir = os.path.join(local_dir, value["dir"])
			if not os.path.isdir(target_dir):
				os.mkdir(target_dir)
			shutil.copy2(value["path"], target_dir)
			# Debug
			logger(0, "%s --> %s" % (key, target_dir))
			logger(1, "%s <-> %s" % (value["version"], local_data[key]["version"] if key in local_data else "None"))

	add_on_change_listener()

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
		logger(2, "add_on_change_listener", name)
		s = sublime.load_settings(name)
		s.clear_on_change("package_sync")
		s.add_on_change("package_sync", sync_push)

def clear_on_change_listener():
	for name in find_settings():
		logger(2, "clear_on_change_listener", name)
		s = sublime.load_settings(name)
		s.clear_on_change("package_sync")
