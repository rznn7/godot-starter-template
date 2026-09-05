extends Node

const OWN_PATH: String = "res://scripts/typecheck.gd"


func _ready() -> void:
	var failures: int = 0
	for path: String in OS.get_cmdline_user_args():
		if path == OWN_PATH:
			continue
		if not _script_is_valid(path):
			failures += 1
	get_tree().quit(1 if failures > 0 else 0)


func _script_is_valid(path: String) -> bool:
	var loaded: Resource = ResourceLoader.load(path, "Script", ResourceLoader.CACHE_MODE_IGNORE)
	var script: GDScript = loaded as GDScript
	if script == null:
		print("SCRIPT-FAIL %s could not be loaded as a GDScript" % path)
		return false
	var status: int = script.reload(true)
	if status != OK:
		print("SCRIPT-FAIL %s failed to compile (error %d)" % [path, status])
		return false
	return true
