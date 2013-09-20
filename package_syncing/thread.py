import sublime
import sublime_plugin

import fnmatch
import functools
import os
import shutil
import sys
import threading
import time

try:
    from . import logger
    from . import tools
    from . import watcher
except ValueError:
    from package_syncing import logger
    from package_syncing import tools
    from package_syncing import watcher

log = logger.getLogger(__name__)


class Queue(object):

    current = None
    pool = []

    def __init__(self):
        pass

    def start(self):
        # Clear old thread
        if self.current and self.current["thread"].is_alive():
            sublime.set_timeout(lambda: self.start(), 500)

        else:
            # Reset current thread, since it ended
            self.current = None

            # Check for elements in pool
            if self.pool:
                self.current = self.pool.pop(0)
                self.current["thread"].start()

                # Attemp a new start of the thread
                sublime.set_timeout(lambda: self.start(), 500)

    def has(self, key):
        pool = self.pool + [self.current] if self.current else []
        return any([item for item in pool if item["key"] == key])

    def add(self, thread, key=None):
        self.pool += [{"key": key if key else thread.name, "thread": thread}]
        self.start()


class Sync(threading.Thread):

    def __init__(self, settings, mode=["pull", "push"], override=False, item=None):

        self.settings = settings
        self.mode = mode
        self.item = item
        self.override = override

        threading.Thread.__init__(self)

    def run(self):
        sync_interval = self.settings.get("sync_interval", 1)

        # Stop watcher and wait for the poll
        tools.pause_watcher(local="pull" in self.mode, remote="push" in self.mode)

        # If no item pull and push all
        if not self.item:
            print("Package Syncing: Start Complete Sync")

            # Fetch all items from the remote location
            if "pull" in self.mode:
                self.pull_all()

            # Push all items to the remote location
            if "push" in self.mode:
                self.push_all()

            print("Package Syncing: End Complete Sync")
        else:
            # Pull the selected item
            if "pull" in self.mode:
                self.pull(self.item)

            # Push the selected item
            if "push" in self.mode:
                self.push(self.item)

        # Restart watcher again
        tools.pause_watcher(False, local="pull" in self.mode, remote="push" in self.mode)

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
        last_data = tools.load_last_data()
        last_local_data = last_data.get("last_local_data", {})
        last_remote_data = last_data.get("last_remote_data", {})

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
        tools.save_last_data(last_local_data=self.find_files(local_dir), last_remote_data=self.find_files(remote_dir))

    def pull(self, item):
        log.debug("pull started for %s" % item)

        local_dir = os.path.join(sublime.packages_path(), "User")
        remote_dir = self.settings.get("sync_folder")

        # Get data of last sync
        last_data = tools.load_last_data()
        last_local_data = last_data.get("last_local_data", {})
        last_remote_data = last_data.get("last_remote_data", {})

        # Make target file path and directory
        target = os.path.join(local_dir, item["key"])
        target_dir = os.path.dirname(target)

        # Skip if file was just pushed
        try:
            if item["type"] == "c" or item["type"] == "m":

                # Check for an updated Package Control setting file and backup old file
                if item["key"] == "Package Control.sublime-settings":
                    previous_installed_packages = tools.load_installed_packages(target)
                    installed_packages = tools.load_installed_packages(item["path"])

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
        tools.save_last_data(last_local_data=last_local_data, last_remote_data=last_remote_data)

        if item["type"] != "d" and item["key"] == "Package Control.sublime-settings":
            # Handle Package Control
            self.pull_package_control(last_data, previous_installed_packages, installed_packages)

    def pull_package_control(self, last_data, previous_installed_packages, installed_packages):
        # Save items to remove
        to_install = [item for item in installed_packages if item not in previous_installed_packages]
        to_remove = [item for item in previous_installed_packages if item not in installed_packages]

        log.debug("install: %s", to_install)
        log.debug("remove: %s", to_remove)

        # Check for old remove_packages
        remove_packages = last_data.get("remove_packages", [])
        remove_packages += [item for item in to_remove if item != "Package Control" and item not in remove_packages]

        log.debug("remove_packages %s", remove_packages)

        if remove_packages:
            removed_packages = self.remove_packages(remove_packages)
        else:
            removed_packages = []

        # Check if new packages are available and run package cleanup to install missing packages
        if to_install:
            sublime.set_timeout(self.install_packages, 1000)

        tools.save_last_data(remove_packages=[item for item in remove_packages if item not in removed_packages])

    def install_packages(self):
        try:
            # Reset last-run file
            file_path = os.path.join(sublime.packages_path(), "User", "Package Control.last-run")
            if os.path.isfile(file_path):
                os.remove(file_path)

            # Import package_control_cleaner
            mod = sys.modules["package_control.package_cleanup" if sublime.version()[0] == "2" else "Package Control.package_control.package_cleanup"]
            package_control_cleaner = mod.PackageCleanup()
            package_control_cleaner.start()
        except:
            print("Package Syncing: Error while loading Package Control")

    def remove_packages(self, packages):
        log.debug("packages %s", packages)

        # Reset ignored_packages and wait_flag
        self.ignored_packages = []
        self.wait_flag = True

        # At first ignore packages on main thread
        def ignore_packages():
            settings = sublime.load_settings("Preferences.sublime-settings")
            self.ignored_packages = settings.get('ignored_packages')
            settings.set("ignored_packages", self.ignored_packages + [item for item in packages if item not in self.ignored_packages])
            sublime.save_settings("Preferences.sublime-settings")
            #
            self.wait_flag = False

        sublime.set_timeout(ignore_packages, 0)

        # Wait to complete writing ignored_packages
        while self.wait_flag:
            time.sleep(0.25)

        # wait for sublime text to ignore packages
        time.sleep(1)

        removed_packages = []
        for package in packages[:]:
            status = self.remove_package(package)
            if status:
                removed_packages += [package]

        # Reset wait flag
        self.wait_flag = True

        # Update ignore packages on main thread
        def unignore_packages():
            settings = sublime.load_settings("Preferences.sublime-settings")
            settings.set("ignored_packages", self.ignored_packages)
            sublime.save_settings("Preferences.sublime-settings")
            #
            self.wait_flag = False

        sublime.set_timeout(unignore_packages, 1000)

        # Wait to complete writing ignored_packages
        while self.wait_flag:
            time.sleep(0.25)

        return removed_packages

    def remove_package(self, package):
        # Check for installed_package path
        try:
            installed_package_path = os.path.join(sublime.installed_packages_path(), package + ".sublime-package")
            if os.path.exists(installed_package_path):
                os.remove(installed_package_path)
        except:
            return False

        # Check for pristine_package_path path
        try:
            pristine_package_path = os.path.join(os.path.dirname(sublime.packages_path()), "Pristine Packages", package + ".sublime-package")
            if os.path.exists(pristine_package_path):
                os.remove(pristine_package_path)
        except:
            return False

        # Check for package dir
        try:
            os.chdir(sublime.packages_path())
            package_dir = os.path.join(sublime.packages_path(), package)
            if os.path.exists(package_dir):
                if shutil.rmtree(package_dir):
                    open(os.path.join(package_dir, 'package-control.cleanup'), 'w').close()
        except:
            return False

        return True

    def push_all(self):
        log.debug("push_all started with override = %s" % self.override)

        local_dir = os.path.join(sublime.packages_path(), "User")
        remote_dir = self.settings.get("sync_folder")

        local_data = self.find_files(local_dir)
        remote_data = self.find_files(remote_dir)

        # Get data of last sync
        last_data = tools.load_last_data()
        last_local_data = last_data.get("last_local_data", {})
        last_remote_data = last_data.get("last_remote_data", {})

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
        tools.save_last_data(last_local_data=self.find_files(local_dir), last_remote_data=self.find_files(remote_dir))

    def push(self, item):
        log.debug("push started for %s" % item)

        local_dir = os.path.join(sublime.packages_path(), "User")
        remote_dir = self.settings.get("sync_folder")

        # Get data of last sync
        last_data = tools.load_last_data()
        last_local_data = last_data.get("last_local_data", {})
        last_remote_data = last_data.get("last_remote_data", {})

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
        tools.save_last_data(last_local_data=last_local_data, last_remote_data=last_remote_data)
