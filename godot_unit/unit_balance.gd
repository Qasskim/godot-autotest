extends RefCounted
# 모듈 1 — 판정·점수·등급·게이지·콤보·마크 (기준: Godot/docs/DESIGN.md §5. §6은 게이지 20% 비중만 포함 — 롱/드래그 이탈·재진입 등은 아직 검증하지 않음)
# 기대값은 게임 코드를 읽어 만든 값이 아니라 DESIGN.md에 확정된 수치를 이 파일에 직접 적은 것이다.
# (코드 값을 읽어 비교하면 코드가 틀렸을 때 기대값도 같이 틀려져서 못 잡는다.)

const TOL := 1e-6        # 0.2 배율처럼 이진수로 딱 떨어지지 않는 값을 비교할 때 허용 오차
const LOOP_CAP := 5000   # 게이지를 끝까지 내리거나 올리는 반복의 안전 상한

var results: Array = []
var _nodes: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float) -> void:
	check(name, absf(actual - expected) <= TOL, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	for n in _nodes:
		if is_instance_valid(n):
			n.free()
	_nodes.clear()


func _score(note_count: int) -> ScoreSystem:
	var s := ScoreSystem.new()
	_nodes.append(s)
	s.setup(note_count)
	return s


func _gauge(value: float, worst_zone_idx: int) -> GaugeSystem:
	var g := GaugeSystem.new()
	_nodes.append(g)
	g.gauge = value
	g._worst_zone_idx = worst_zone_idx
	return g


func run() -> Array:
	_balance_values()
	_judgment_windows()
	_judgment_signals()
	_ex_score()
	_grades()
	_gauge_zones()
	_gauge_deltas()
	_gauge_no_regress()
	_combo()
	_marks()
	return results


# ── GameBalance 수치 = DESIGN.md ─────────────────────────────────
func _balance_values() -> void:
	var w = GameBalance.judgment_windows
	eq("수치: 판정 창 Wow 32 / Great 70 / Good 170 / Oops 250ms (DESIGN §5)",
		[w["Wow"], w["Great"], w["Good"], w["Oops"]], [32.0, 70.0, 170.0, 250.0])
	eq("수치: 동시치기 허용 2ms (DESIGN §5)", GameBalance.CHORD_TOLERANCE_MS, 2.0)
	eq("수치: EX 가중치 Wow 3 / Great 2 / Good 0 / Oops 0 / Miss 0 (DESIGN §5)",
		GameBalance.ex_weight, {"Wow": 3, "Great": 2, "Good": 0, "Oops": 0, "Miss": 0})
	var got: Array = []
	for e in GameBalance.grade_thresholds:
		got.append([e["grade"], float(e["min_accuracy"])])
	eq("수치: 등급 커트라인 MAX 100 / S++ 98.5 / S+ 97 / S 95 / A 90 / B 80 / C 70 / D 50 (DESIGN §5)",
		got, [["MAX", 100.0], ["S++", 98.5], ["S+", 97.0], ["S", 95.0], ["A", 90.0], ["B", 80.0], ["C", 70.0], ["D", 50.0]])
	eq("수치: 50% 미만 등급 F (DESIGN §5)", GameBalance.GRADE_FALLBACK, "F")
	eq("수치: 게이지 최대·시작 300 (DESIGN §5)", [GameBalance.gauge_max, GameBalance.gauge_start], [300.0, 300.0])
	eq("수치: 게이지 변화량 Wow +0.75 / Great +0.5 / Good +0.25 / Oops -3 / Miss -6 (DESIGN §5)",
		GameBalance.gauge_delta, {"Wow": 0.75, "Great": 0.5, "Good": 0.25, "Oops": -3.0, "Miss": -6.0})
	var zones: Array = []
	for z in GameBalance.gauge_zones:
		zones.append([z["name"], float(z["floor"]), float(z["decrease_mult"])])
	eq("수치: 게이지 구간 Expert>200 ×2.0 / Hard>100 ×1.5 / Normal>29 ×1.0 / Easy>0 ×0.5 (DESIGN §5)",
		zones, [["Expert", 200.0, 2.0], ["Hard", 100.0, 1.5], ["Normal", 29.0, 1.0], ["Easy", 0.0, 0.5]])
	eq("수치: Easy 구간 회복 보정 ×1.25 (DESIGN §5)", GameBalance.GAUGE_EASY_RECOVERY_MULT, 1.25)


# ── 판정 창 (DESIGN §5: Wow 0~32 / Great 33~70 / Good 71~170 / Oops 171~250 / Miss 251+) ──
func _judgment_windows() -> void:
	var js := JudgmentSystem.new()
	_nodes.append(js)
	var table := [[0, "Wow"], [32, "Wow"], [33, "Great"], [70, "Great"], [71, "Good"], [170, "Good"],
		[171, "Oops"], [250, "Oops"], [251, "Miss"], [999, "Miss"]]
	for row in table:
		for sign in [1, -1]:
			if row[0] == 0 and sign < 0:
				continue
			var label := "늦게" if sign > 0 else "일찍"
			var got: String = js.grade_only(1000.0, 1000.0 + float(row[0] * sign))
			eq("판정 창: 오차 %dms %s → %s" % [row[0], label, row[1]], got, row[1])
	eq("판정 창: 가장 넓은 창(Oops) 250ms", js.get_max_window_ms(), 250.0)


func _judgment_signals() -> void:
	var js := JudgmentSystem.new()
	_nodes.append(js)
	var got: Array = []
	js.judgment_made.connect(func(g, e, l, b): got.append([g, e, l, b]))
	js.judge_ms(1000.0, 1050.0, 3)
	js.force_miss(5)
	eq("판정 신호: judge_ms는 (등급, 오차=입력-노트, 레인, 버스트)를 보낸다", got[0] if got.size() > 0 else null, ["Great", 50.0, 3, true])
	eq("판정 신호: force_miss는 Miss, 오차 999, 버스트 없음", got[1] if got.size() > 1 else null, ["Miss", 999.0, 5, false])
	js.judge_ms(1000.0, 940.0, 1)
	eq("판정 신호: 일찍 친 오차는 음수", got[2][1] if got.size() > 2 else null, -60.0)


# ── EX 점수 (DESIGN §5: 절대값 누적, 최대 EX = 노트 수 × 3, Oops/Miss 감점 없음) ──
func _ex_score() -> void:
	var s := _score(100)
	eq("EX: 최대 EX = 노트 수 × 3 (100노트 → 300)", s.get_max_ex(), 300)
	eq("EX: 시작 점수 0", s.score, 0)
	for j in ["Wow", "Great", "Good", "Oops", "Miss"]:
		var t := _score(10)
		t.add_judgment(j, 0.0)
		eq("EX: %s 한 번의 가점" % j, t.score, {"Wow": 3, "Great": 2, "Good": 0, "Oops": 0, "Miss": 0}[j])
	var m := _score(10)
	for i in 10:
		m.add_judgment("Miss", 0.0)
	eq("EX: Miss 10번에도 점수가 음수가 되지 않음(감점 없음)", m.score, 0)
	var o := _score(10)
	for i in 10:
		o.add_judgment("Oops", 0.0)
	eq("EX: Oops 10번에도 점수가 음수가 되지 않음(감점 없음)", o.score, 0)

	var full := _score(10)
	for i in 10:
		full.add_judgment("Wow", 0.0)
	near("EX: 전부 Wow면 달성률 100%", full.get_accuracy(), 100.0)
	eq("EX: 전부 Wow면 등급 MAX", full.get_grade(), "MAX")
	var half := _score(10)
	for i in 5:
		half.add_judgment("Wow", 0.0)
	for i in 5:
		half.add_judgment("Miss", 0.0)
	near("EX: Wow 5 + Miss 5(10노트)는 달성률 50%", half.get_accuracy(), 50.0)
	eq("EX: 달성률 50%는 등급 D", half.get_grade(), "D")
	var over := _score(10)
	over.score = 999
	near("EX: 달성률은 100%를 넘지 않음(클램프)", over.get_accuracy(), 100.0)
	over.score = -5
	near("EX: 달성률은 0% 아래로 내려가지 않음(클램프)", over.get_accuracy(), 0.0)

	var big := _score(1234)
	eq("EX: 1234노트의 최대 EX는 3702", big.get_max_ex(), 3702)
	var lm := _score(10)
	lm.add_notes(5)
	eq("EX: 레인믹스 활성화로 노트 5개를 더하면 최대 EX가 15 늘어남(30→45)", lm.get_max_ex(), 45)

	var c := _score(20)
	c.add_judgment("Wow", 0.0)
	c.add_judgment("Great", 0.0)
	c.add_judgment("Great", 0.0)
	c.add_judgment("Good", 0.0)
	c.add_judgment("Oops", 0.0)
	c.add_judgment("Miss", 999.0)
	eq("EX: 판정 카운트 집계", c.get_judgment_counts(), {"Wow": 1, "Great": 2, "Good": 1, "Oops": 1, "Miss": 1})

	var fs := _score(10)
	fs.add_judgment("Great", -40.0)
	fs.add_judgment("Great", 40.0)
	fs.add_judgment("Wow", 10.0)
	fs.add_judgment("Good", 0.0)
	fs.add_judgment("Miss", 999.0)
	eq("EX: Fast/Slow 집계(일찍=Fast, 늦게=Slow, Wow와 오차 0은 제외, Miss는 Slow)", fs.get_fast_slow_counts(), {"fast": 1, "slow": 2})


# ── 등급 커트라인 (DESIGN §5) ─────────────────────────────────────
# 기준 판정은 정수 산술(score*1000 >= 커트라인*10 × 만점)로 한다. 부동소수점 비교로 기대값을 만들지 않기 위해서다.
const TIERS := [["MAX", 1000], ["S++", 985], ["S+", 970], ["S", 950], ["A", 900], ["B", 800], ["C", 700], ["D", 500]]


func _oracle_grade(sc: int, max_ex: int) -> String:
	for t in TIERS:
		if sc * 1000 >= t[1] * max_ex:
			return t[0]
	return "F"


func _grades() -> void:
	# 명세 경계를 사람이 읽을 수 있는 형태로: 노트 2000개(만점 6000)에서 각 커트라인 ±1점
	var named := [["MAX", 100.0, 6000, "S++"], ["S++", 98.5, 5910, "S+"], ["S+", 97.0, 5820, "S"], ["S", 95.0, 5700, "A"],
		["A", 90.0, 5400, "B"], ["B", 80.0, 4800, "C"], ["C", 70.0, 4200, "D"], ["D", 50.0, 3000, "F"]]
	for row in named:
		var s := _score(2000)
		s.score = row[2]
		eq("등급 경계: %s%% (6000점 만점 중 %d점) → %s" % [str(row[1]), row[2], row[0]], s.get_grade(), row[0])
		s.score = row[2] - 1
		eq("등급 경계: %s%% 바로 아래 (%d점) → %s" % [str(row[1]), row[2] - 1, row[3]], s.get_grade(), row[3])

	# 작은 노트 수는 0점부터 만점까지 모든 점수를 전수 대조
	for n in [1, 2, 3, 5, 7, 10, 33, 100, 333]:
		var s := _score(n)
		var mx: int = n * 3
		var bad: Array = []
		for sc in range(0, mx + 1):
			s.score = sc
			var got: String = s.get_grade()
			var want := _oracle_grade(sc, mx)
			if got != want:
				bad.append("%d점(%.4f%%) 기대 %s 실제 %s" % [sc, float(sc) / float(mx) * 100.0, want, got])
		check("등급 전수 대조: 노트 %d개(만점 %d), 0~만점 모든 점수" % [n, mx], bad.is_empty(),
			"; ".join(bad.slice(0, 3)) + (" 외 %d건" % (bad.size() - 3) if bad.size() > 3 else ""))

	# 큰 노트 수는 각 커트라인의 정수 경계 -1/0/+1점만
	for n in [1234, 2000, 5000, 9999]:
		var s := _score(n)
		var mx: int = n * 3
		var bad: Array = []
		for t in TIERS:
			var smin: int = (t[1] * mx + 999) / 1000
			for sc in [smin - 1, smin, smin + 1]:
				if sc < 0 or sc > mx:
					continue
				s.score = sc
				var got: String = s.get_grade()
				var want := _oracle_grade(sc, mx)
				if got != want:
					bad.append("%d점 기대 %s 실제 %s" % [sc, want, got])
		check("등급 경계 대조: 노트 %d개(만점 %d), 모든 커트라인 -1/0/+1점" % [n, mx], bad.is_empty(),
			"; ".join(bad.slice(0, 3)) + (" 외 %d건" % (bad.size() - 3) if bad.size() > 3 else ""))


# ── 게이지 (DESIGN §5) ────────────────────────────────────────────
func _gauge_zones() -> void:
	var cases := [[300.0, "Expert"], [201.0, "Expert"], [200.5, "Expert"], [200.0, "Hard"], [101.0, "Hard"], [100.0, "Normal"],
		[30.0, "Normal"], [29.5, "Normal"], [29.0, "Easy"], [1.0, "Easy"], [0.5, "Easy"], [0.0, "GameOver"]]
	for c in cases:
		var g := _gauge(c[0], 0)
		eq("게이지 구간: 게이지 %s → %s" % [str(c[0]), c[1]], g.get_clear_grade(), c[1])
	var g0 := GaugeSystem.new()
	_nodes.append(g0)
	eq("게이지: 시작값 300, Expert", [g0.gauge, g0.get_clear_grade()], [300.0, "Expert"])


func _gauge_deltas() -> void:
	var base := {"Wow": 0.75, "Great": 0.5, "Good": 0.25, "Oops": -3.0, "Miss": -6.0}
	# 구간 한가운데 값을 골라 구간 변화·상한·0 클램프가 섞이지 않게 한다
	var zones := [["Expert", 250.0, 0, 2.0], ["Hard", 150.0, 1, 1.5], ["Normal", 60.0, 2, 1.0], ["Easy", 20.0, 3, 0.5]]
	for z in zones:
		for j in ["Wow", "Great", "Good", "Oops", "Miss"]:
			for cont in [false, true]:
				var g := _gauge(z[1], z[2])
				g.apply_judgment(j, cont)
				var d: float = base[j] * (0.2 if cont else 1.0)
				if d < 0.0:
					d *= z[3]
				elif z[0] == "Easy":
					d *= 1.25
				var label := "롱/드래그 유지 틱(20%)" if cont else "일반 판정"
				near("게이지 변화: %s 구간, %s, %s" % [z[0], j, label], g.gauge, z[1] + d)
	var top := _gauge(300.0, 0)
	top.apply_judgment("Wow")
	near("게이지: 최대 300을 넘지 않음", top.gauge, 300.0)
	var sig := _gauge(250.0, 0)
	var seen: Array = []
	sig.gauge_changed.connect(func(v): seen.append(v))
	sig.apply_judgment("Great")
	eq("게이지: 변화 시 gauge_changed 신호로 새 값을 보냄", seen, [250.5])


func _drive_to(g: GaugeSystem, zone: String) -> bool:
	var i := 0
	while g.get_clear_grade() != zone and i < LOOP_CAP:
		g.apply_judgment("Miss")
		i += 1
	return g.get_clear_grade() == zone


func _recover(g: GaugeSystem) -> void:
	for i in LOOP_CAP:
		g.apply_judgment("Wow")


func _gauge_no_regress() -> void:
	# DESIGN §5: 역진 불가 — 한 번 떨어진 구간의 상한을 넘어 회복할 수 없다
	var h := GaugeSystem.new()
	_nodes.append(h)
	var reached_h := _drive_to(h, "Hard")
	_recover(h)
	check("게이지 역진 불가: Hard로 떨어진 뒤 Wow만 쳐도 Expert로 돌아가지 않음(≤200, Hard)",
		reached_h and h.gauge <= 200.0 and h.get_clear_grade() == "Hard", "도달 %s, 회복 후 게이지 %s, 등급 %s" % [str(reached_h), str(h.gauge), h.get_clear_grade()])
	var n := GaugeSystem.new()
	_nodes.append(n)
	var reached_n := _drive_to(n, "Normal")
	_recover(n)
	check("게이지 역진 불가: Normal로 떨어진 뒤 Wow만 쳐도 Hard로 돌아가지 않음(≤100, Normal)",
		reached_n and n.gauge <= 100.0 and n.get_clear_grade() == "Normal", "도달 %s, 회복 후 게이지 %s, 등급 %s" % [str(reached_n), str(n.gauge), n.get_clear_grade()])
	var e := GaugeSystem.new()
	_nodes.append(e)
	var reached_e := _drive_to(e, "Easy")
	_recover(e)
	check("게이지 역진 불가의 예외: Easy까지 떨어져도 회복하면 Normal로 복귀(≤100) (DESIGN §5 \"Easy→Normal만 예외\")",
		reached_e and e.gauge <= 100.0 and e.get_clear_grade() == "Normal", "도달 %s, 회복 후 게이지 %s, 등급 %s" % [str(reached_e), str(e.gauge), e.get_clear_grade()])
	var o := GaugeSystem.new()
	_nodes.append(o)
	var low := 300.0
	for i in LOOP_CAP:
		o.apply_judgment("Miss")
		low = minf(low, o.gauge)
	check("게이지: Miss만 계속 치면 0에서 멈추고 GameOver (음수 없음)", o.gauge == 0.0 and low == 0.0 and o.get_clear_grade() == "GameOver",
		"최종 %s, 최저 %s, 등급 %s" % [str(o.gauge), str(low), o.get_clear_grade()])
	var r := GaugeSystem.new()
	_nodes.append(r)
	_drive_to(r, "Hard")
	r.reset()
	eq("게이지: reset은 300·Expert·구간 기억 초기화", [r.gauge, r.get_clear_grade(), r._worst_zone_idx], [300.0, "Expert", 0])


# ── 콤보 (DESIGN §5: Miss 시 초기화, 현재/최대 분리) ──────────────
func _combo() -> void:
	var c := ComboSystem.new()
	_nodes.append(c)
	var cur: Array = []
	for j in ["Wow", "Great", "Good", "Oops", "Wow", "Wow", "Miss", "Miss"]:
		c.apply_judgment(j)
		cur.append(c.current_combo)
	eq("콤보: Wow·Great·Good는 이어지고 Oops·Miss는 끊김", cur, [1, 2, 3, 0, 1, 2, 0, 0])
	eq("콤보: 최대 콤보 3", c.best_combo, 3)
	eq("콤보: 끊긴 횟수 2 (이미 0인 상태의 Miss는 세지 않음)", c.break_count, 2)
	eq("콤보: 한 번이라도 끊겼으면 combo_broken", c.combo_broken, true)

	var h := ComboSystem.new()
	_nodes.append(h)
	h.apply_judgment("Wow")
	h.apply_judgment("Wow")
	h.apply_hold_break()
	eq("콤보: 홀드 이탈은 콤보를 0으로 끊고 횟수와 hold_broken을 기록", [h.current_combo, h.break_count, h.hold_broken, h.combo_broken], [0, 1, true, true])
	h.apply_hold_break()
	eq("콤보: 이미 0일 때 홀드 이탈은 끊긴 횟수를 늘리지 않음", h.break_count, 1)
	h.reset()
	eq("콤보: reset은 전부 초기화", [h.current_combo, h.best_combo, h.combo_broken, h.hold_broken, h.break_count], [0, 0, false, false, 0])
	var s := ComboSystem.new()
	_nodes.append(s)
	var seen: Array = []
	s.combo_changed.connect(func(a, b): seen.append([a, b]))
	s.apply_judgment("Wow")
	s.apply_judgment("Miss")
	eq("콤보: combo_changed 신호는 (현재, 최대)", seen, [[1, 1], [0, 1]])


# ── 마크 (DESIGN §5) ──────────────────────────────────────────────
func _mk(counts: Dictionary, score_val: int, full: bool, cleared: bool) -> Array:
	var s := _score(100)
	for j in counts:
		for i in counts[j]:
			s.add_judgment(j, 0.0)
	s.score = score_val   # 점수 모양 마크 시험을 위해 점수를 직접 지정한다
	return s.get_marks(full, cleared)


func _marks() -> void:
	eq("마크: 클리어 실패 → failed (clear 없음)", _mk({"Wow": 3, "Miss": 2}, 1, false, false), ["failed"])
	eq("마크: 클리어, Miss 있고 풀콤보 아님 → clear 만", _mk({"Wow": 3, "Miss": 2}, 1, false, true), ["clear"])
	eq("마크: Good 없이 풀콤보 → perfect", _mk({"Wow": 5, "Great": 5}, 1, true, true), ["clear", "perfect"])
	eq("마크: Good 있으나 Miss 없이 풀콤보 → allcombo", _mk({"Wow": 5, "Good": 2}, 1, true, true), ["clear", "allcombo"])
	eq("마크: 풀콤보는 아니지만 Oops·Miss 없이 클리어 → allgood", _mk({"Wow": 5, "Good": 2}, 1, false, true), ["clear", "allgood"])
	eq("마크: Oops가 있으면 allgood 아님", _mk({"Wow": 5, "Oops": 1}, 1, false, true), ["clear"])

	var bad: Array = []
	var combos := 0
	for good in [0, 3]:
		for oops in [0, 2]:
			for miss in [0, 1]:
				for full in [true, false]:
					for cleared in [true, false]:
						combos += 1
						var counts := {"Wow": 4, "Good": good, "Oops": oops, "Miss": miss}
						var m := _mk(counts, 1, full, cleared)
						var excl := 0
						for x in ["perfect", "allcombo", "allgood"]:
							if x in m:
								excl += 1
						var cf := int("clear" in m) + int("failed" in m)
						if excl > 1 or cf != 1:
							bad.append("good%d oops%d miss%d full=%s cleared=%s → %s" % [good, oops, miss, str(full), str(cleared), str(m)])
	check("마크: perfect·allcombo·allgood는 동시에 둘 이상 붙지 않고 clear/failed는 정확히 하나 (%d조합)" % combos, bad.is_empty(), "; ".join(bad.slice(0, 3)))

	# 점수 모양 마크 — DESIGN §5: 연속된 숫자(123456 등) / 같은 숫자 반복(777777 등) / 정확히 666666
	eq("마크: 점수 123456 → straight", "straight" in _mk({"Wow": 1}, 123456, false, true), true)
	eq("마크: 점수 654321(내림차순) → straight", "straight" in _mk({"Wow": 1}, 654321, false, true), true)
	eq("마크: 점수 234567 → straight", "straight" in _mk({"Wow": 1}, 234567, false, true), true)
	eq("마크: 점수 777777 → luckyroulette", "luckyroulette" in _mk({"Wow": 1}, 777777, false, true), true)
	eq("마크: 점수 111111 → luckyroulette", "luckyroulette" in _mk({"Wow": 1}, 111111, false, true), true)
	eq("마크: 점수 666666 → evil", "evil" in _mk({"Wow": 1}, 666666, false, true), true)
	eq("마크: 점수 123457(연속 아님) → 점수 모양 마크 없음", _mk({"Wow": 1}, 123457, false, true).has("straight") or _mk({"Wow": 1}, 123457, false, true).has("luckyroulette"), false)
	eq("마크: 점수 12345(5자리) → 점수 모양 마크 없음", _mk({"Wow": 1}, 12345, false, true).has("straight"), false)
	# 명세에 적혀 있지 않은 부분 — 지금 구현이 하는 동작을 기록해 둔다(결정은 사용자)
	eq("마크 [구현 동작·명세 없음]: 7자리 점수 1234567은 뒤 6자리(234567)로 판정 → straight", "straight" in _mk({"Wow": 1}, 1234567, false, true), true)
	eq("마크 [구현 동작·명세 없음]: 점수 1666666은 뒤 6자리가 같은 숫자 → luckyroulette (evil 아님)", _mk({"Wow": 1}, 1666666, false, true).has("luckyroulette") and not _mk({"Wow": 1}, 1666666, false, true).has("evil"), true)
	eq("마크 [구현 동작·명세 없음]: 점수 666666은 evil 하나만 붙음(luckyroulette 동시 부여 없음)", _mk({"Wow": 1}, 666666, false, true).has("luckyroulette"), false)
