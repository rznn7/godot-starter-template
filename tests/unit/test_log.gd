extends GdUnitTestSuite


func test_format_entry_prefixes_level() -> void:
	var logger: AppLog = auto_free(AppLog.new())
	assert_str(logger.format_entry(AppLog.Level.INFO, "ready")).is_equal("[INFO] ready")


func test_is_enabled_respects_min_level() -> void:
	var logger: AppLog = auto_free(AppLog.new())
	logger.min_level = AppLog.Level.WARN
	assert_bool(logger.is_enabled(AppLog.Level.DEBUG)).is_false()
	assert_bool(logger.is_enabled(AppLog.Level.ERROR)).is_true()
