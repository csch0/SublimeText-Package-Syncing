import sublime, sublime_plugin
import fnmatch, functools, json, os, shutil, sys, time, threading

try:
	from . import logger, watcher
	log = logger.getLogger(__name__)
except:
	from package_syncing import logger, watcher
	log = logger.getLogger(__name__)

def load_settings():
	s = sublime.load_settings("Package Syncing.sublime-settings")
	return { 
		"log": s.get("log", False),
		"sync": s.get("sync", False),
		"sync_folder": s.get("sync_folder", False),
		"sync_interval": s.get("sync_interval", 1),
		"files_to_include": s.get("files_to_include", []),
		"files_to_ignore": s.get("files_to_ignore", []),
		"dirs_to_ignore": s.get("dirs_to_ignore", [])
	}

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
		log.warning("Error while saving Packages Syncing.last-run %s" % e)

def load_installed_packages(path):
	try:
		with open(path, "r", encoding = "utf8") as f:
			file_json = json.load(f)
	except:
		file_json = {}
	
	return file_json.get("installed_packages", [])

def package_control(previous_installed_packages):	
	s = sublime.load_settings("Package Control.sublime-settings")
	installed_packages = s.get("installed_packages", [])

	to_install = [item for item in installed_packages if item not in previous_installed_packages]
	to_remove = [item for item in previous_installed_packages if item not in installed_packages]

	s.set("installed_packages", installed_packages + to_remove)
	sublime.save_settings("Package Control.sublime-settings")

	thread = threading.Thread(target = functools.partial(perform_package_control, to_install, to_remove))
	thread.start()

def perform_package_control(to_install, to_remove):
	log.debug("%s %s", to_install, to_remove)
	try:
		# Import package_manager
		mod = sys.modules["package_control.package_manager" if sublime.version()[0] == "2" else "Package Control.package_control.package_manager"]
		package_manager = mod.PackageManager()

		# check for installed packages
		for item in to_install:
			print("Package Syncing: Installing %s" % item)
			package_manager.install_package(item)
			print("Package Syncing: Installed %s by using Package Control" % item)

		# check for removed packages
		for item in to_remove:
			print("Package Syncing: Removing %s" % item)
			package_manager.remove_package(item)
			print("Package Syncing: Removed %s" % item)
	except:
		print("Package Syncing: Cannot load Package Controller")

watcher_local = None
watcher_remote = None

def start_watcher(setting):
	local_dir = os.path.join(sublime.packages_path(), "User")
	remote_dir = setting.get("sync_folder")
	# 
	sync_interval = setting.get("sync_interval")
	# 
	files_to_include = setting.get("files_to_include", [])
	files_to_ignore = setting.get("files_to_ignore", []) + ["Package Syncing.sublime-settings", "Package Syncing.last-run"]
	dirs_to_ignore = setting.get("dirs_to_ignore", [])
	# 
	global watcher_local
	global watcher_remote
	# 
	watcher_remote = watcher.WatcherThread(remote_dir, "pkg_sync_pull_item", sync_interval, files_to_include, files_to_ignore, dirs_to_ignore)
	watcher_remote.start()
	#
	watcher_local = watcher.WatcherThread(local_dir, "pkg_sync_push_item", sync_interval, files_to_include, files_to_ignore, dirs_to_ignore)
	watcher_local.start()

def stop_watcher():
	
	global watcher_local
	global watcher_remote

	try:
		watcher_local.stop = True
		watcher_remote.stop = True
	except:
		pass
