import sublime
import sublime_plugin
import os.path

try:
    from .package_syncing import logger
    from .package_syncing import thread
    from .package_syncing import tools
except ValueError:
    from package_syncing import logger
    from package_syncing import thread
    from package_syncing import tools

log = logger.getLogger(__name__)
q = thread.Queue()


class PkgSyncEnableCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        s = tools.load_settings()
        return not s.get("sync", False)

    def run(self):
        s = sublime.load_settings("Package Syncing.sublime-settings")
        s.set("sync", True)
        sublime.save_settings("Package Syncing.sublime-settings")

        # Start watcher
        tools.start_watcher(tools.load_settings())

        # Run pkg_sync
        sublime.run_command("pkg_sync", {"mode": ["pull", "push"]})


class PkgSyncDisableCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        s = tools.load_settings()
        return s.get("sync", False)

    def run(self):
        s = sublime.load_settings("Package Syncing.sublime-settings")
        s.set("sync", False)
        sublime.save_settings("Package Syncing.sublime-settings")

        # Stop watcher
        tools.stop_watcher()


class PkgSyncCommand(sublime_plugin.ApplicationCommand):

    def is_enabled(self):
        s = tools.load_settings()
        return s.get("sync", False) and s.get("sync_folder", False) != False

    def run(self, mode=["pull", "push"], override=False):
        log.debug("pkg_sync %s %s", mode, override)

        # Load settings
        settings = sublime.load_settings("Package Syncing.sublime-settings")

        # Check for valid sync_folder
        if not os.path.isdir(settings.get("sync_folder")):
            sublime.error_message("Invalid sync folder \"%s\", sync disabled! Please adjust your sync folder." % settings.get("sync_folder"))
            settings.set("sync", False)
            sublime.save_settings("Package Syncing.sublime-settings")
            return

        # Check if sync is already running
        if not q.has("sync"):
            t = thread.Sync(tools.load_settings(), mode, override)
            q.add(t, "sync")
        else:
            print("Package Syncing: Already running")


class PkgSyncPullItemCommand(sublime_plugin.ApplicationCommand):

    def is_enabled(self):
        s = tools.load_settings()
        return s.get("sync", False) and s.get("sync_folder", False) and os.path.isdir(s.get("sync_folder"))

    def run(self, item):
        log.debug("pkg_sync_pull_item %s", item)

        # Start a thread to pull the current item
        t = thread.Sync(tools.load_settings(), mode=["pull"], item=item)
        q.add(t)


class PkgSyncPushItemCommand(sublime_plugin.ApplicationCommand):

    def is_enabled(self):
        s = tools.load_settings()
        return s.get("sync", False) and s.get("sync_folder", False) and os.path.isdir(s.get("sync_folder"))

    def run(self, item):
        log.debug("pkg_sync_push_item %s", item)

        # Start a thread to push the current item
        t = thread.Sync(tools.load_settings(), mode=["push"], item=item)
        q.add(t)


class PkgSyncFolderCommand(sublime_plugin.WindowCommand):

    def is_enabled(self):
        return not q.has("sync")

    def run(self):
        # Load settings to provide an initial value for the input panel
        settings = sublime.load_settings("Package Syncing.sublime-settings")
        settings.clear_on_change("package_syncing")
        sublime.save_settings("Package Syncing.sublime-settings")

        sync_folder = settings.get("sync_folder")

        # Suggest user dir if nothing set or folder do not exists
        if not sync_folder:
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

                # Adjust settings
                settings.set("sync", True)
                settings.set("sync_folder", path)

                # Reset last-run file
                file_path = os.path.join(sublime.packages_path(), "User", "Package Control.last-run")
                if os.path.isfile(file_path):
                    os.remove(file_path)

                # Reset last-run file
                file_path = os.path.join(sublime.packages_path(), "User", "Package Syncing.last-run")
                if os.path.isfile(file_path):
                    os.remove(file_path)

                sublime.save_settings("Package Syncing.sublime-settings")
                sublime.status_message("sync_folder successfully set to \"%s\"" % path)

                # Restart watcher
                tools.pause_watcher(local=False)
                tools.stop_watcher(local=False)
                tools.start_watcher(tools.load_settings(), local=False)

                # Run pkg_sync
                sublime.set_timeout(lambda: sublime.run_command("pkg_sync", {"mode": ["pull", "push"], "override": override}), 1000)

            else:
                sublime.error_message("Invalid Path %s" % path)

            # Add on on_change listener
            sublime.set_timeout(lambda: settings.add_on_change("package_syncing", tools.restart_watcher), 500)

        self.window.show_input_panel("Sync Folder", sync_folder, on_done, None, None)


def plugin_loaded():
    s = sublime.load_settings("Package Syncing.sublime-settings")
    s.clear_on_change("package_syncing")
    s.add_on_change("package_syncing", tools.restart_watcher)
    sublime.save_settings("Package Syncing.sublime-settings")

    # Start watcher
    sublime.set_timeout(lambda: tools.start_watcher(tools.load_settings()), 100)

    # Run pkg_sync
    sublime.set_timeout(lambda: sublime.run_command("pkg_sync", {"mode": ["pull", "push"]}), 1000)


def plugin_unloaded():
    s = sublime.load_settings("Package Syncing.sublime-settings")
    s.clear_on_change("package_syncing")
    sublime.save_settings("Package Syncing.sublime-settings")

    # Stop folder watcher
    tools.stop_watcher()


if sublime.version()[0] == "2":
    plugin_loaded()
