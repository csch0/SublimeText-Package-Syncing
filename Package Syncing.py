import sublime, sublime_plugin

import os.path, logging
logging.basicConfig(level = logging.INFO, format="[%(asctime)s - %(levelname)s - %(name)s] %(message)s")

try:
	from .package_syncing.tools import *
except ValueError:
	from package_syncing.tools import *


class PkgSyncListnerCommand(sublime_plugin.EventListener):

	def on_load(self, view):
		sublime.set_timeout(view.window().run_command("pkg_sync_pull"), 500)

	def on_activated(self, view):
		if view.file_name():			
			sublime.set_timeout(view.window().run_command("pkg_sync_pull"), 250)

	def on_post_save(self, view):
		sublime.set_timeout(view.window().run_command("pkg_sync_push"), 500)


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


class PkgSyncPullCommand(sublime_plugin.WindowCommand):

	def is_enabled(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		return s.get("sync", False) and s.get("sync_folder") != None

	def run(self):
		sync_pull()


class PkgSyncPushCommand(sublime_plugin.WindowCommand):

	def is_enabled(self):
		s = sublime.load_settings("Package Syncing.sublime-settings")
		return s.get("sync", False) and s.get("sync_folder") != None

	def run(self):
		sync_push()


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
				sublime.save_settings("Package Syncing.sublime-settings")
				sublime.status_message("sync_folder successfully set to \"%s\"" % path)
				#
				sync_pull(override)
				sync_push()
			else:
				sublime.error_message("Invalid Path %s" % path)

		self.window.show_input_panel("Sync Folder", sync_folder, on_done, None, None)


def plugin_loaded():
	sync_pull()
	sync_push()
	add_on_change_listener()

if int(sublime.version()) < 3000:
	plugin_loaded()
