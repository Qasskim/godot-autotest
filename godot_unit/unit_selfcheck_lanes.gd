extends RefCounted
# 자체 점검(모듈 2) — unit_lanes.gd 가 값 변경을 실제로 잡아내는지 확인한다.
# 게임 파일은 건드리지 않는다. 실행 중인 프로세스의 메모리 값(판정 창, 입력 바인딩, 레인 좌표)만 잠깐 바꿨다가 바로 되돌린다.

var results: Array = []


func cleanup() -> void:
	pass


func _fail_count(hook: Callable = Callable()) -> int:
	var body = load(get_script().resource_path.get_base_dir() + "/unit_lanes.gd").new()
	body.after_setup = hook
	var res: Array = body.run()
	body.cleanup()
	var n := 0
	for r in res:
		if not r["pass"]:
			n += 1
	return n


func _expect_detected(name: String, base: int, after: int) -> void:
	results.append({"name": name, "pass": after > base, "detail": "실패 건수 %d → %d" % [base, after]})


func run() -> Array:
	var base := _fail_count()

	var w = GameBalance.judgment_windows
	var old = w["Oops"]
	w["Oops"] = 249.0
	_expect_detected("자체 점검: Oops 창 250→249ms로 바꾸면 한 번 누름 판정 테스트가 잡아낸다", base, _fail_count())
	w["Oops"] = old

	old = w["Good"]
	w["Good"] = 169.0
	_expect_detected("자체 점검: Good 창 170→169ms로 바꾸면 라인판정 보정 테스트가 잡아낸다", base, _fail_count())
	w["Good"] = old

	var evs: Array = InputMap.action_get_events("key_0")
	InputMap.action_erase_events("key_0")
	_expect_detected("자체 점검: key_0 바인딩을 지우면 키 배치·키보드 입력 테스트가 잡아낸다", base, _fail_count())
	for e in evs:
		InputMap.action_add_event("key_0", e)

	var evs16: Array = InputMap.action_get_events("key16_5")
	InputMap.action_erase_events("key16_5")
	_expect_detected("자체 점검: key16_5 바인딩을 지우면 16키 테스트가 잡아낸다", base, _fail_count())
	for e in evs16:
		InputMap.action_add_event("key16_5", e)

	# 레인 좌표는 테스트가 화면 설정(ScreenLayout._rebuild)에서 다시 만드므로, 그 직후 훅에서 원천 값을 바꾼다
	_expect_detected("자체 점검: 레인 외곽 폭(lane_half_span)을 10% 줄이면 레인 좌표 테스트가 잡아낸다", base,
		_fail_count(func(): ScreenLayout.lane_half_span *= 0.9; LaneSystem.rebuild()))
	_expect_detected("자체 점검: 중앙 간격(lane_center_gap)을 0으로 하면 중앙 X=0 빈 공간 테스트가 잡아낸다", base,
		_fail_count(func(): ScreenLayout.lane_center_gap = 0.0; LaneSystem.rebuild()))
	_expect_detected("자체 점검: 레인 간격(lane_gap)을 1.1배로 하면 레인 좌표 테스트가 잡아낸다", base,
		_fail_count(func(): ScreenLayout.lane_gap *= 1.1; LaneSystem.rebuild()))
	var again := _fail_count()
	results.append({"name": "자체 점검(모듈 2): 모든 값을 되돌린 뒤 실패 건수가 처음과 같다(되돌림 확인)", "pass": again == base, "detail": "처음 %d / 되돌린 뒤 %d" % [base, again]})
	return results
