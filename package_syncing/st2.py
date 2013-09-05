import sublime, sublime_plugin

import os, fnmatch

def find_resources(pattern):
	resources = []
	if hasattr(sublime, 'find_resources'):
		resources = sublime.find_resources(pattern)
	else:
		for root, dir_names, file_names in os.walk(sublime.packages_path()):
			for file_name in file_names:
				rel_path = os.path.relpath(os.path.join(root, file_name), sublime.packages_path()).replace(os.sep, "/")
				if fnmatch.fnmatch(rel_path.lower(), "*" + pattern.lower()):
					resources += ["Packages/" + rel_path]
	return resources

def load_resource(name):
	if hasattr(sublime, 'load_resource'):
		return sublime.load_resource(name)
	else:
		with open(path, "r", encoding = "utf-8") as f:
			return f.read()