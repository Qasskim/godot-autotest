extends RefCounted
# 자체 점검(모듈 9) — unit_hold.gd 가 수치 변경을 실제로 잡아내는지 확인한다.
# 게임 파일은 건드리지 않는다. 실행 중인 프로세스의 GameBalance 메모리 값만 잠깐 바꿨다가 바로 되돌린다.

var needs_frames := true   # unit_hold 가 InputManager 뷰포트를 읽는다
var results: Array = []


func cleanup() -> void:
	pass


func _fail_count() -> int:
	var body = load(get_script().resource_path.get_base_dir() + "/unit_hold.gd").new()
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
	_expect_detected("자체 점검(모듈 9): Oops 창 250→249ms로 바꾸면 끝 앞 창 경계 테스트가 잡아낸다", base, _fail_count())
	w["Oops"] = old

	old = w["Good"]
	w["Good"] = 90.0
	_expect_detected("자체 점검(모듈 9): Good 창 170→90ms로 바꾸면(100ms 늦은 헤드가 Oops가 됨) 헤드 등급 테스트가 잡아낸다", base, _fail_count())
	w["Good"] = old

	old = GameBalance.gauge_delta["Good"]
	GameBalance.gauge_delta["Good"] = 0.5
	_expect_detected("자체 점검(모듈 9): Good 게이지 +0.25→+0.5로 바꾸면 틱 게이지 테스트가 잡아낸다", base, _fail_count())
	GameBalance.gauge_delta["Good"] = old

	old = GameBalance.gauge_delta["Miss"]
	GameBalance.gauge_delta["Miss"] = -5.0
	_expect_detected("자체 점검(모듈 9): Miss 게이지 -6→-5로 바꾸면 Miss 틱 테스트가 잡아낸다", base, _fail_count())
	GameBalance.gauge_delta["Miss"] = old

	var again := _fail_count()
	results.append({"name": "자체 점검(모듈 9): 모든 값을 되돌린 뒤 실패 건수가 처음과 같다(되돌림 확인)", "pass": again == base, "detail": "처음 %d / 되돌린 뒤 %d" % [base, again]})
	return results
