debug_level = 0

def logger(level, *args):
	if debug_level != None and level <= debug_level:
		print(*args)