import sublime, sublime_plugin

import os.path

from .package_syncing.tools import *

class PkgSyncListnerCommand(sublime_plugin.EventListener):

	def on_load(self, view):
		sublime.set_timeout(lambda: sync_pull(), 500)

	def on_activated(self, view):
		sublime.set_timeout(lambda: sync_pull(), 250)

	def on_post_save(self, view):
		sublime.set_timeout(lambda: sync_push(), 500)


class PkgSyncPullCommand(sublime_plugin.WindowCommand):

	def run(self):
		sync_pull()


class PkgSyncPushCommand(sublime_plugin.WindowCommand):

	def run(self):
		sync_push()


class PkgSyncSetFolderCommand(sublime_plugin.WindowCommand):

	def run(self):
		# Load settings to provide an initial value for the input panel
		s = sublime.load_settings("Package Syncing.sublime-settings")
		sync_folder = s.get("sync_folder")

		if not sync_folder or not os.path.isdir(sync_folder):
			sync_folder = os.path.expanduser("~")

		def on_done(path):
			if not os.path.isdir(path):
				os.makedirs(path)

			if os.path.isdir(path):
				s.set("sync_folder", path)
				sublime.save_settings("Package Syncing.sublime-settings")
				sublime.status_message("sync_folder successfully set to \"%s\"" % path)
				#
				sublime.run_command("ps_sync")
			else:
				sublime.error_message("Invalid Path %s" % path)

		self.window.show_input_panel("Sync Folder", sync_folder, on_done, None, None)


def plugin_loaded():
	sync_pull()
	sync_push()
	add_on_change_listener()