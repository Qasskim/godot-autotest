extends RefCounted
# 자체 점검 — 단위 테스트(unit_balance.gd)가 수치 변경을 실제로 잡아내는지 확인한다.
# 게임 파일은 건드리지 않는다. 실행 중인 프로세스의 GameBalance 메모리 값만 잠깐 바꿨다가 바로 되돌린다.

var results: Array = []


func cleanup() -> void:
	pass


func _fail_count() -> int:
	var body = load(get_script().resource_path.get_base_dir() + "/unit_balance.gd").new()
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
	var old = w["Wow"]
	w["Wow"] = 33.0
	_expect_detected("자체 점검: Wow 판정 창 32→33ms로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	w["Wow"] = old

	old = w["Great"]
	w["Great"] = 71.0
	_expect_detected("자체 점검: Great 판정 창 70→71ms로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	w["Great"] = old

	old = w["Oops"]
	w["Oops"] = 251.0
	_expect_detected("자체 점검: Oops 판정 창 250→251ms로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	w["Oops"] = old

	old = GameBalance.ex_weight["Great"]
	GameBalance.ex_weight["Great"] = 1
	_expect_detected("자체 점검: Great EX 가중치 2→1로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	GameBalance.ex_weight["Great"] = old

	var tier: Dictionary = GameBalance.grade_thresholds[1]   # S++
	old = tier["min_accuracy"]
	tier["min_accuracy"] = 98.4
	_expect_detected("자체 점검: S++ 커트라인 98.5→98.4로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	tier["min_accuracy"] = old

	old = GameBalance.gauge_delta["Miss"]
	GameBalance.gauge_delta["Miss"] = -5.0
	_expect_detected("자체 점검: Miss 게이지 -6→-5로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	GameBalance.gauge_delta["Miss"] = old

	var hard: Dictionary = GameBalance.gauge_zones[1]
	old = hard["decrease_mult"]
	hard["decrease_mult"] = 1.4
	_expect_detected("자체 점검: Hard 구간 감소 배율 1.5→1.4로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	hard["decrease_mult"] = old

	var easy: Dictionary = GameBalance.gauge_zones[3]
	old = easy["floor"]
	easy["floor"] = 1.0
	_expect_detected("자체 점검: Easy 구간 하한 0→1로 바꾸면 테스트가 잡아낸다", base, _fail_count())
	easy["floor"] = old

	var again := _fail_count()
	results.append({"name": "자체 점검: 모든 값을 되돌린 뒤 실패 건수가 처음과 같다(되돌림 확인)", "pass": again == base, "detail": "처음 %d / 되돌린 뒤 %d" % [base, again]})
	return results
