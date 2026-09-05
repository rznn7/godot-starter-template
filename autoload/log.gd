class_name AppLog
extends Node

enum Level { DEBUG, INFO, WARN, ERROR }

const LEVEL_NAMES: Dictionary = {
	Level.DEBUG: "DEBUG",
	Level.INFO: "INFO",
	Level.WARN: "WARN",
	Level.ERROR: "ERROR",
}

var min_level: Level = Level.DEBUG


func is_enabled(level: Level) -> bool:
	return level >= min_level


func format_entry(level: Level, message: String) -> String:
	var level_name: String = LEVEL_NAMES[level]
	return "[%s] %s" % [level_name, message]


func debug(message: String) -> void:
	_emit(Level.DEBUG, message)


func info(message: String) -> void:
	_emit(Level.INFO, message)


func warn(message: String) -> void:
	_emit(Level.WARN, message)


func error(message: String) -> void:
	_emit(Level.ERROR, message)


func _emit(level: Level, message: String) -> void:
	if not is_enabled(level):
		return
	var entry: String = format_entry(level, message)
	if level >= Level.WARN:
		push_warning(entry)
	print(entry)
