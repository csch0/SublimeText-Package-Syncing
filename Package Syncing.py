import sublime, sublime_plugin

import fnmatch, os.path, logging
logging.basicConfig(level = logging.INFO, format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s")

try:
	from .package_syncing import tools
except ValueError:
	from package_syncing import tools

class PkgSyncListnerCommand(sublime_plugin.EventListener):

	def is_enabled(self, view, on_save = False):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		files_to_include = s.get("files_to_include", [])
		files_to_ignore = s.get("files_to_ignore", []) + ["*.sublime-settings"] if on_save else ["Package Syncing.sublime-settings"]

		include_matches = [fnmatch.fnmatch(view.file_name(), p) for p in files_to_include]
		ignore_matches = [fnmatch.fnmatch(view.file_name(), p) for p in files_to_ignore]
		return any(include_matches) and not any(ignore_matches)

	def on_load(self, view):
		if self.is_enabled(view):			
			sublime.set_timeout(sublime.run_command("pkg_sync_pull", {"check_last_run": False}), 500)

	def on_activated(self, view):
		if view.file_name():			
			sublime.set_timeout(sublime.run_command("pkg_sync", {"mode": ["pull", "push"]}), 250)

	def on_post_save(self, view):
		if self.is_enabled(view, True):			
			sublime.set_timeout(sublime.run_command("pkg_sync_push", {"check_last_run": False}), 500)

class PkgSyncEnableCommand(sublime_plugin.WindowCommand):

	def is_enabled(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		return not s.get("sync", False)

	def run(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		s.set("sync", True)
		sublime.save_settings("Package Syncing.sublime-settings")


class PkgSyncDisableCommand(sublime_plugin.WindowCommand):

	def is_enabled(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		return s.get("sync", False)

	def run(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		s.set("sync", False)
		sublime.save_settings("Package Syncing.sublime-settings")


class PkgSyncCommand(sublime_plugin.ApplicationCommand):

	def is_enabled(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		return s.get("sync", False) and s.get("sync_folder") != None

	def run(self, check_last_run = True, mode = ["pull", "push"], override = False):
		tools.sync(check_last_run, mode, override)


class PkgSyncFolderCommand(sublime_plugin.WindowCommand):

	def run(self):
		# Load settings to provide an initial value for the input panel
		s = sublime.load_settings("Package Syncing.sublime-settings")
		sync_folder = s.get("sync_folder")

		# Suggest user dir if nothing set or folder do not exists
		if not sync_folder or not os.path.isdir(sync_folder):
			sync_folder = os.path.expanduser("~")

		def on_done(path):
			if not os.path.isdir(path):
				os.makedirs(path)

			if os.path.isdir(path):
				if os.listdir(path):
					if sublime.ok_cancel_dialog("The selected folder is not empty, would you like to continue and override your local settings?", "Continue"):
						override = True
					else:
						self.window.show_input_panel("Sync Folder", path, on_done, None, None)
						return
				else:
					override = False

				s.set("sync_folder", path)

				if sublime.ok_cancel_dialog("Enabled sync now?", "Enable"):
					s.set("sync", True)

				sublime.save_settings("Package Syncing.sublime-settings")
				sublime.status_message("sync_folder successfully set to \"%s\"" % path)
				# 
				sublime.run_command("pkg_sync", {"check_last_run:": "false", mode": ["pull", "push"], "override": override})
			else:
				sublime.error_message("Invalid Path %s" % path)

		self.window.show_input_panel("Sync Folder", sync_folder, on_done, None, None)


def plugin_loaded():
	tools.sync(False)

if sublime.version()[0] == "2":
	plugin_loaded()
