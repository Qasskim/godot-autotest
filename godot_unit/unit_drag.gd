extends RefCounted
# 모듈 10 — 드래그 노트 처리 (기준: Godot/docs/DESIGN.md §6 드래그 노트 처리, 2026-11-04 "끝 앞 Oops 창" 항목)
# DragNoteVisual 을 곡 시계(MusicPlayer)와 손가락 위치를 직접 움직여 시험한다.
# 궤적: 체인 웨이포인트 (1000ms 레인4) → (2000ms 레인6) → (3000ms 레인6). 120BPM → 틱 간격 125ms. 손가락이 궤적 X 근처에 있으면 홀드.

const TOL := 1e-6
const T := 1000.0
const END := 3000.0
const TICK := 125.0
const STEP := 25.0
const G0 := 250.0
const MISS_TICK := -2.4
const WOW_TICK := 0.15
const GOOD_TICK := 0.05
const WAYPOINTS := [{"timing_ms": 1000.0, "lane": 4}, {"timing_ms": 2000.0, "lane": 6}, {"timing_ms": 3000.0, "lane": 6}]

var needs_frames := true   # 노트가 get_viewport()(터치 → 월드 좌표 변환)를 쓰므로 트리가 시작된 뒤에 돈다
var results: Array = []
var _free_nodes: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float) -> void:
	check(name, absf(actual - expected) <= TOL, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	for n in _free_nodes:
		if is_instance_valid(n):
			if n.get_parent() != null:
				n.get_parent().remove_child(n)
			n.free()
	_free_nodes.clear()


class Env extends RefCounted:
	var music: MusicPlayer
	var calc: NotePositionCalculator
	var judgment: JudgmentSystem
	var score: ScoreSystem
	var gauge: GaugeSystem
	var combo: ComboSystem
	var input: InputManager
	var note: DragNoteVisual
	var log: Array = []
	var tick_miss: int = 0


func _env() -> Env:
	var tree := Engine.get_main_loop() as SceneTree
	var e := Env.new()
	e.music = MusicPlayer.new()
	e.music.is_playing_music = true
	e.music._frozen = true
	e.music._paused_pos_ms = 0.0
	e.calc = NotePositionCalculator.new()
	e.calc._music = e.music
	e.calc.setup_chart({"bpm": 120.0}, [])
	e.judgment = JudgmentSystem.new()
	e.score = ScoreSystem.new()
	e.score.setup(10)
	e.gauge = GaugeSystem.new()
	e.gauge.gauge = G0
	e.combo = ComboSystem.new()
	e.input = InputManager.new()
	tree.root.add_child(e.input)
	e.input.set_key_mode(4)
	e.judgment.judgment_made.connect(func(g, _err, l, b): e.log.append([g, l, b]))
	var world := Node2D.new()
	tree.root.add_child(world)
	e.note = DragNoteVisual.new()
	world.add_child(e.note)             # 홀드 이펙트가 부모에 붙고 get_viewport()가 필요하므로 트리 안에 둔다
	e.note.waypoints = WAYPOINTS.duplicate(true)
	e.note.chain_id = 1
	e.note.setup(4, T, e.calc, e.music)
	e.note.setup_systems(e.judgment, e.score, e.gauge, e.combo, e.input)
	e.note.tick_miss.connect(func(): e.tick_miss += 1)
	_free_nodes.append_array([e.music, e.calc, e.judgment, e.score, e.gauge, e.combo, e.input, world])
	return e


func _step(e: Env, now: float) -> void:
	e.music._paused_pos_ms = now
	e.calc._frame_now_ms = now
	e.calc._frame_scroll_pos = e.calc.get_scroll_pos(now)
	e.note._process(0.0)


# 시험에서 따로 계산한 궤적 X(코드의 보간 함수를 쓰지 않고 레인 X를 직접 보간)
func _traj_x(now: float) -> float:
	var wp: Array = WAYPOINTS
	for i in wp.size() - 1:
		var t0: float = wp[i].timing_ms
		var t1: float = wp[i + 1].timing_ms
		if now <= t1 or i == wp.size() - 2:
			var t := clampf((now - t0) / (t1 - t0), 0.0, 1.0)
			return lerpf(LaneSystem.get_lane_x(wp[i].lane), LaneSystem.get_lane_x(wp[i + 1].lane), t)
	return LaneSystem.get_lane_x(wp[wp.size() - 1].lane)


func _touch(e: Env, x: float, pressed: bool) -> void:
	var ev := InputEventScreenTouch.new()
	ev.index = 0
	ev.position = Vector2(x, 300.0)
	ev.pressed = pressed
	e.input._unhandled_input(ev)


func _move(e: Env, x: float) -> void:
	var ev := InputEventScreenDrag.new()
	ev.index = 0
	ev.position = Vector2(x, 300.0)
	e.input._unhandled_input(ev)


# from~to 구간을 STEP 단위로 움직이며 손가락이 궤적에서 offset 만큼 떨어진 곳을 따라가게 한다
func _follow(e: Env, from_ms: float, to_ms: float, offset: float = 0.0) -> void:
	var t := from_ms
	while t <= to_ms + 0.001:
		_move(e, _traj_x(t) + offset)
		_step(e, t)
		t += STEP


func _run_idle(e: Env, from_ms: float, to_ms: float) -> void:
	var t := from_ms
	while t <= to_ms + 0.001:
		_step(e, t)
		t += STEP


func _grades(e: Env) -> Array:
	var g: Array = []
	for r in e.log:
		g.append(r[0])
	return g


func run() -> Array:
	(Engine.get_main_loop() as SceneTree).root.size = Vector2i(2400, 1080)
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))   # 레인 좌표·허용 폭을 개발 기준 화면(DESIGN §1)에 맞춘다
	_trajectory()
	_normal_hold()
	_leave_early()
	_release_window()
	_head_miss_and_rescue()
	_reentry()
	_tolerance()
	_autoplay_and_keyboard()
	return results


# ── 궤적 보간 (DESIGN §6: 체인 웨이포인트 (timing_ms, lane)) ─────────────────────
func _trajectory() -> void:
	var e := _env()
	var n: DragNoteVisual = e.note
	near("궤적: 첫 웨이포인트 시각(1000)의 X는 레인4의 X", n.get_trajectory_x_at(1000.0), LaneSystem.get_lane_x(4))
	near("궤적: 첫 웨이포인트보다 이른 시각(500)은 첫 지점에 머문다", n.get_trajectory_x_at(500.0), LaneSystem.get_lane_x(4))
	near("궤적: 두 웨이포인트 사이(1500)는 레인4와 6의 X를 반반 섞은 값", n.get_trajectory_x_at(1500.0), (LaneSystem.get_lane_x(4) + LaneSystem.get_lane_x(6)) / 2.0)
	near("궤적: 둘째 웨이포인트(2000)의 X는 레인6", n.get_trajectory_x_at(2000.0), LaneSystem.get_lane_x(6))
	near("궤적: 같은 레인끼리 이어진 구간(2500)은 레인6에 머문다", n.get_trajectory_x_at(2500.0), LaneSystem.get_lane_x(6))
	near("궤적: 마지막 웨이포인트 뒤(3500)는 마지막 지점", n.get_trajectory_x_at(3500.0), LaneSystem.get_lane_x(6))
	eq("궤적 레인: 시작은 레인4, 중간(1500)은 반올림해 레인5, 끝은 레인6", [n.get_trajectory_lane_at(1000.0), n.get_trajectory_lane_at(1500.0), n.get_trajectory_lane_at(2000.0)], [4, 5, 6])
	eq("궤적 레인: 1250은 레인4→6의 25% 지점(4.5)이라 반올림해 레인5(0.5는 올림)", n.get_trajectory_lane_at(1250.0), 5)
	eq("궤적 레인: 1249는 4.498 → 레인4", n.get_trajectory_lane_at(1249.0), 4)
	eq("궤적 레인: 끝(3000) 이후는 마지막 웨이포인트 레인6", n.get_trajectory_lane_at(4000.0), 6)
	eq("드래그 끝 시각 = 마지막 웨이포인트 시각(3000)", n._get_end_ms(), END)
	eq("드래그는 홀드형 노트", n.is_hold_type(), true)
	var two := _env()
	two.note.waypoints = [{"timing_ms": 1000.0, "lane": 2}, {"timing_ms": 1000.0, "lane": 9}, {"timing_ms": 2000.0, "lane": 9}]
	eq("궤적: 같은 시각의 두 웨이포인트(점프)는 앞 웨이포인트 레인을 돌려줌(0으로 나누지 않음)", two.note.get_trajectory_lane_at(1000.0), 2)


# ── 정상 홀드 ──────────────────────────────────────────────────────
func _normal_hold() -> void:
	var e := _env()
	_touch(e, _traj_x(T), true)
	e.note.on_press(T + 100.0)
	eq("드래그 헤드: 100ms 늦게 눌러 헤드 등급 Good, 홀드 중", [e.note._tick_judgment, e.note._is_held], ["Good", true])
	_follow(e, T + 100.0, END)
	near("드래그 홀드(Good 헤드): 궤적을 따라가면 틱마다 헤드 등급 게이지 — 15틱 × (+0.25×20%)", e.gauge.gauge, G0 + 15.0 * GOOD_TICK)
	eq("드래그 홀드: 테일에서 헤드 등급(Good) 판정 한 번(버스트 없음)", e.log, [["Good", 4, false]])
	eq("드래그 홀드: 끝까지 따라가면 노트가 사라지고 틱 Miss·콤보 끊김 없음", [e.note.is_queued_for_deletion(), e.tick_miss, e.combo.break_count], [true, 0, 0])


# ── 궤적 이탈 (DESIGN §6: Miss·콤보 0) ────────────────────────────────
func _leave_early() -> void:
	var e := _env()
	for i in 5:
		e.combo.apply_judgment("Wow")
	_touch(e, _traj_x(T), true)
	e.note.on_press(T)
	_follow(e, T, 1475.0)
	var off := e.note.TRAJ_TOLERANCE * 3.0       # 궤적에서 허용 폭의 3배 벗어남
	_follow(e, 1500.0, END, off)
	eq("드래그 이탈: 끝 250ms보다 일찍 궤적을 벗어나면 Miss 한 번", e.log, [["Miss", 4, false]])
	eq("드래그 이탈: 콤보 0, 끊긴 횟수 1, hold_broken", [e.combo.current_combo, e.combo.break_count, e.combo.hold_broken], [0, 1, true])
	eq("드래그 이탈: 남은 12틱은 Miss 틱", e.tick_miss, 12)
	near("드래그 이탈: 게이지 = 홀드 틱 3×(+0.15) + Miss 틱 12×(-2.4)", e.gauge.gauge, G0 + 3.0 * WOW_TICK + 12.0 * MISS_TICK)


# ── 끝 앞 Oops 창 안에서 경로를 벗어남 = 이탈 아님 (DESIGN §6, 2026-11-04) ──────────
func _release_window() -> void:
	var e := _env()
	for i in 5:
		e.combo.apply_judgment("Wow")
	_touch(e, _traj_x(T), true)
	e.note.on_press(T)
	_follow(e, T, 2725.0)
	var off := e.note.TRAJ_TOLERANCE * 3.0
	_follow(e, 2750.0, END, off)         # 끝(3000) - 250 = 2750 경계 포함
	eq("끝 앞 창(경계 2750ms 포함): 벗어나도 이탈이 아님 — Miss 없이 테일에서 헤드 등급(Wow)", e.log, [["Wow", 4, false]])
	eq("끝 앞 창: 콤보 끊김 없음·틱 Miss 없음", [e.combo.current_combo, e.combo.break_count, e.tick_miss], [5, 0, 0])
	near("끝 앞 창: 남은 틱도 헤드 등급(Wow)으로 반영 — 15틱 모두 +0.15", e.gauge.gauge, G0 + 15.0 * WOW_TICK)

	var b := _env()
	_touch(b, _traj_x(T), true)
	b.note.on_press(T)
	_follow(b, T, 2725.0)
	_move(b, _traj_x(2749.0) + b.note.TRAJ_TOLERANCE * 3.0)
	_step(b, 2749.0)
	eq("끝 앞 창 경계 바로 밖(2749ms): 이탈로 보고 Miss", b.log, [["Miss", 4, false]])


# ── 헤드 미스와 구제 ─────────────────────────────────────────────────
func _head_miss_and_rescue() -> void:
	var e := _env()
	_run_idle(e, 0.0, 1075.0)
	eq("드래그 헤드 미스 전: 헤드 판정 창이 지나기 전에는 판정 없음", e.log.size(), 0)
	_run_idle(e, 1100.0, 1125.0)
	eq("드래그 헤드 미스: 머리 시각 +100ms를 넘기면 Miss 한 번", e.log, [["Miss", 4, false]])
	_run_idle(e, 1150.0, END)
	eq("드래그 헤드 미스: 입력이 없으면 끝까지 Miss 틱 15개", e.tick_miss, 15)
	near("드래그 헤드 미스: 게이지 = Miss 틱 15×(-2.4)", e.gauge.gauge, G0 + 15.0 * MISS_TICK)
	eq("드래그 헤드 미스: 테일에서 추가 판정 없음", e.log.size(), 1)

	var r := _env()
	_run_idle(r, 0.0, 1475.0)
	_touch(r, _traj_x(1500.0), true)
	_step(r, 1500.0)
	eq("드래그 구제: 미스 뒤 궤적 위에 손을 대면 홀드 중이 되고 틱 등급은 Good", [r.note._judged_head, r.note._is_held, r.note._tick_judgment], [true, true, "Good"])
	_follow(r, 1525.0, END)
	near("드래그 구제: Miss 틱 3(구제 전) + Good 틱 11(구제 후)", r.gauge.gauge, G0 + 3.0 * MISS_TICK + 11.0 * GOOD_TICK)
	eq("드래그 구제: 판정은 처음 Miss 하나뿐", r.log, [["Miss", 4, false]])


# ── 이탈 뒤 재진입 ────────────────────────────────────────────────────
func _reentry() -> void:
	var e := _env()
	_touch(e, _traj_x(T), true)
	e.note.on_press(T)
	_follow(e, T, 1475.0)
	var off := e.note.TRAJ_TOLERANCE * 3.0
	_follow(e, 1500.0, 1775.0, off)
	_follow(e, 1800.0, 1800.0)
	eq("드래그 재진입: 이탈 뒤 궤적으로 돌아오면 홀드 중, 틱 등급은 Good으로 내려감", [e.note._is_held, e.note._tick_judgment], [true, "Good"])
	_follow(e, 1825.0, END)
	near("드래그 재진입: 홀드 틱 3×(+0.15) + Miss 틱 3×(-2.4) + Good 틱 9×(+0.05)", e.gauge.gauge, G0 + 3.0 * WOW_TICK + 3.0 * MISS_TICK + 9.0 * GOOD_TICK)
	eq("드래그 재진입: 판정은 이탈 때의 Miss 하나뿐", e.log, [["Miss", 4, false]])


# ── 허용 폭 경계 ───────────────────────────────────────────────────────
# [구현 동작] 궤적 허용 폭은 코드가 레인 간격×1.5 (DESIGN §6 문서는 \"±25px(레인 너비 절반)\")
func _tolerance() -> void:
	var tol: float = _env().note.TRAJ_TOLERANCE
	eq("허용 폭 [구현 동작·DESIGN §6은 ±25px]: 레인 간격(ScreenLayout.lane_gap)의 1.5배", tol, ScreenLayout.lane_gap * 1.5)
	var inside := _env()
	_touch(inside, _traj_x(T), true)
	inside.note.on_press(T)
	_follow(inside, T, 2000.0, tol)                      # 허용 폭 경계 위(포함)
	eq("허용 폭 경계: 궤적에서 정확히 허용 폭만큼 떨어져도 홀드 유지", [inside.note._is_held, inside.log.size()], [true, 0])
	var outside := _env()
	_touch(outside, _traj_x(T), true)
	outside.note.on_press(T)
	_follow(outside, T, 2000.0, tol + 0.5)               # 허용 폭을 0.5 넘음
	eq("허용 폭 경계: 허용 폭을 넘으면 이탈(Miss)", [outside.note._is_held, _grades(outside)], [false, ["Miss"]])


# ── 오토플레이와 키보드 ─────────────────────────────────────────────────
func _autoplay_and_keyboard() -> void:
	var a := _env()
	a.input.auto_play = true
	a.note.on_press(T)
	_run_idle(a, T, END)
	eq("드래그 오토플레이: 손을 안 대도 끝까지 헤드 등급(Wow)으로 확정", a.log, [["Wow", 4, false]])
	near("드래그 오토플레이: 틱 15개 모두 +0.15", a.gauge.gauge, G0 + 15.0 * WOW_TICK)

	var k := _env()
	var press := InputEventKey.new()
	press.keycode = KEY_S               # 4키: 레인4~7은 키1(S) — 궤적 레인(4→6)이 모두 키1 안
	press.pressed = true
	k.input._unhandled_input(press)
	k.note.on_press(T)
	_run_idle(k, T, 1475.0)
	eq("드래그 키보드: 손가락이 없으면 궤적 레인의 키가 눌려 있는 것으로 홀드 유지", [k.note._is_held, k.log.size()], [true, 0])
	var rel := InputEventKey.new()
	rel.keycode = KEY_S
	rel.pressed = false
	k.input._unhandled_input(rel)
	_step(k, 1500.0)
	eq("드래그 키보드: 키를 떼면(끝 창 밖) 이탈로 Miss", k.log, [["Miss", 4, false]])
