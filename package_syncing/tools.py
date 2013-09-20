import sublime
import sublime_plugin

import json
import os
import time

if sublime.version()[0] == "2":
    from codecs import open

try:
    from . import logger
    from . import watcher
except:
    from package_syncing import logger
    from package_syncing import watcher

log = logger.getLogger(__name__)

watcher_local = None
watcher_remote = None


def load_settings():
    s = sublime.load_settings("Package Syncing.sublime-settings")
    return {
        "sync": s.get("sync", False),
        "sync_folder": s.get("sync_folder", False),
        "sync_interval": s.get("sync_interval", 1),
        "files_to_include": s.get("files_to_include", []),
        "files_to_ignore": s.get("files_to_ignore", []),
        "dirs_to_ignore": s.get("dirs_to_ignore", [])
    }


def load_last_data():
    try:
        with open(os.path.join(sublime.packages_path(), "User", "Package Syncing.last-run"), "r", encoding="utf8") as f:
            file_json = json.load(f)
    except:
        file_json = {}
    return file_json


def save_last_data(**kwargs):
    # Load current file
    file_json = load_last_data()
    # Save new values
    for key, value in kwargs.items():
        file_json[key] = value
    try:
        with open(os.path.join(sublime.packages_path(), "User", "Package Syncing.last-run"), "w", encoding="utf8") as f:
            json.dump(file_json, f, sort_keys=True, indent=4)
    except Exception as e:
        log.warning("Error while saving Packages Syncing.last-run %s" % e)


def load_installed_packages(path):
    try:
        with open(path, "r", encoding="utf8") as f:
            file_json = json.load(f)
    except:
        file_json = {}

    return file_json.get("installed_packages", [])


def start_watcher(settings, local=True, remote=True):
    global watcher_local
    global watcher_remote

    if not settings.get("sync", False):
        return

    # Build required options for the watcher
    local_dir = os.path.join(sublime.packages_path(), "User")
    remote_dir = settings.get("sync_folder")
    sync_interval = settings.get("sync_interval")
    files_to_include = settings.get("files_to_include", [])
    files_to_ignore = settings.get("files_to_ignore", []) + ["Package Syncing.sublime-settings", "Package Syncing.last-run"]
    dirs_to_ignore = settings.get("dirs_to_ignore", [])

    # Create local watcher
    if local:
        watcher_local = watcher.WatcherThread(local_dir, "pkg_sync_push_item", sync_interval, files_to_include, files_to_ignore, dirs_to_ignore)
        watcher_local.start()

    # Create remote watcher
    if remote:
        watcher_remote = watcher.WatcherThread(remote_dir, "pkg_sync_pull_item", sync_interval, files_to_include, files_to_ignore, dirs_to_ignore)
        watcher_remote.start()


def pause_watcher(status=True, local=True, remote=True):
    global watcher_local
    global watcher_remote

    # Pause local watcher
    if watcher_local and local:
        watcher_local.pause(status)

    # Pause remote watcher
    if watcher_remote and remote:
        watcher_remote.pause(status)


def restart_watcher():
    settings = load_settings()
    #
    pause_watcher(local=False)
    stop_watcher(local=False)
    start_watcher(load_settings(), local=False)

    # Run pkg_sync
    sublime.set_timeout(lambda: sublime.run_command("pkg_sync", {"mode": ["pull", "push"]}), 1000)


def stop_watcher(local=True, remote=True):
    global watcher_local
    global watcher_remote

    # Stop local watcher
    if watcher_local and local:
        watcher_local.stop = True

    # Stop remote watcher
    if watcher_remote and remote:
        watcher_remote.stop = True
