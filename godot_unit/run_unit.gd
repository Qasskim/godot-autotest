extends SceneTree
# 헤드리스 단위 테스트 실행기.
#   godot --headless --path <게임 프로젝트> --script run_unit.gd -- module=balance
# 이 스크립트는 오토로드(GameBalance 등)가 등록되기 전에 컴파일되므로 오토로드 이름을 직접 쓰지 않는다.
# 테스트 본체(unit_<module>.gd)는 시작한 뒤에 불러온다. 결과는 한 건씩 "@@UNIT@@ {json}" 줄로 출력한다.

const WATCHDOG_SEC := 90.0   # 모듈이 스크립트 오류로 중간에 멈추면 아래 quit에 닿지 못하므로 제한 시간 뒤 강제 종료한다


func _initialize() -> void:
	create_timer(WATCHDOG_SEC).timeout.connect(func():
		print("@@UNIT_ERROR@@ 제한 시간 초과 — 모듈이 중간에 멈췄습니다(스크립트 오류 확인)")
		quit(3))
	var module := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("module="):
			module = a.substr(7)
	if module.is_empty():
		print("@@UNIT_ERROR@@ module= 인자가 없습니다")
		quit(2)
		return
	var path := "%s/unit_%s.gd" % [get_script().resource_path.get_base_dir(), module]
	var script = load(path)
	if script == null:
		print("@@UNIT_ERROR@@ 모듈을 불러오지 못했습니다: ", path)
		quit(2)
		return
	var body = script.new()
	var results: Array = body.run()
	for r in results:
		print("@@UNIT@@ ", JSON.stringify(r))
	if body.has_method("cleanup"):
		body.cleanup()
	quit(0)
