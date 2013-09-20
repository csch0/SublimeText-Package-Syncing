import sublime
import sublime_plugin

import errno
import fnmatch
import os
import stat
import threading
import time

try:
    from . import logger
except ValueError:
    from package_syncing import logger

log = logger.getLogger(__name__)


class WatcherThread(threading.Thread):

    stop = False

    def __init__(self, folder, callback, sync_interval, files_to_include=[], files_to_ignore=[], dirs_to_ignore=[]):
        self.folder = folder
        self.callback = callback

        self.sync_interval = sync_interval

        self.files_to_include = files_to_include
        self.files_to_ignore = files_to_ignore
        self.dirs_to_ignore = dirs_to_ignore

        self.watcher = Watcher(self.folder, self.callback, self.files_to_include, self.files_to_ignore, self.dirs_to_ignore)

        threading.Thread.__init__(self)

    def run(self):
        while not self.stop:
            self.watcher.loop()
            time.sleep(self.sync_interval)

    def pause(self, status=True):
        # Update file list before unpause watcher
        if not status:
            self.watcher.loop()
        self.watcher.pause = status


class Watcher(object):

    pause = True

    def __init__(self, folder, callback, files_to_include=[], files_to_ignore=[], dirs_to_ignore=[]):

        self.folder = folder
        self.callback = callback

        self.files_to_include = files_to_include
        self.files_to_ignore = files_to_ignore
        self.dirs_to_ignore = dirs_to_ignore

        self.files_map = {}

        self.update_files()
        self.pause = False

    def __del__(self):
        for key, value in self.files_map.items():
            log.debug("unwatching %s" % value["path"])

    def listdir(self, walk=False):
        items = []
        for root, dir_names, file_names in os.walk(self.folder):
            [dir_names.remove(d) for d in dir_names if d in self.dirs_to_ignore]

            for file_name in file_names:
                full_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(full_path, self.folder)

                include_matches = [fnmatch.fnmatch(rel_path, p) for p in self.files_to_include]
                ignore_matches = [fnmatch.fnmatch(rel_path, p) for p in self.files_to_ignore]

                if any(ignore_matches) or not any(include_matches):
                    continue

                items += [{"key": rel_path, "path": full_path, "dir": os.path.dirname(rel_path), "version": os.path.getmtime(full_path)}]

        return items

    def loop(self):
        self.update_files()
        for key, value in self.files_map.items():
            self.check_file(key, value)

    def check_file(self, key, value):
        file_mtime = os.path.getmtime(value["path"])
        if file_mtime != value["version"]:
            self.files_map[key]["version"] = file_mtime
            item = dict({"type": "m"}, **value)

            # Run callback if file changed
            if not self.pause:
                sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": item}), 0)
            else:
                log.trace("Skip %s", item)

    def update_files(self):
        items = []

        for item in self.listdir():
            if item["key"] not in self.files_map:
                items += [item]

        # check existent files
        for key, value in self.files_map.copy().items():
            if not os.path.exists(value["path"]):
                self.unwatch(value)

        for item in items:
            if item["key"] not in self.files_map:
                self.watch(item)

    def watch(self, item):
        log.debug("watching %s" % item["path"])
        self.files_map[item["key"]] = item
        item = dict({"type": "c"}, **item)

        # Run callback if file created
        if not self.pause:
            sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": item}), 0)
        else:
            log.trace("Skip %s", item)

    def unwatch(self, item):
        log.debug("unwatching %s" % item["path"])
        del self.files_map[item["key"]]
        item = dict({"type": "d"}, **item)

        # Run callback if file deleted
        if not self.pause:
            sublime.set_timeout(lambda: sublime.run_command(self.callback, {"item": item}), 0)
        else:
            log.trace("Skip %s", item)
