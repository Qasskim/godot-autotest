extends RefCounted
# 모듈 2 — 레인·키 입력·터치 구역·한 번 누름 판정·라인판정 보정 (기준: Godot/docs/DESIGN.md §3·§4·§5의 "키 한 번에 판정되는 노트")
# 기대값(키 모드 그룹표, 물리 키 표)은 DESIGN.md에 적힌 것을 이 파일에 직접 적었다.

const TOL := 1e-6

# DESIGN §3 키모드별 그룹 구성
const SPEC_GROUPS := {
	4:  [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
	5:  [[0, 1, 2], [3, 4, 5], [6, 7, 8, 9], [10, 11, 12], [13, 14, 15]],
	6:  [[0, 1, 2], [3, 4], [5, 6, 7], [8, 9, 10], [11, 12], [13, 14, 15]],
	8:  [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11], [12, 13], [14, 15]],
	16: [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14], [15]],
}
const MODES := [4, 5, 6, 8, 16]

var needs_frames := true   # 뷰포트·오토로드가 필요(터치 구역·입력 시험) — 실행기가 프레임 2번을 기다린 뒤 시작한다
var results: Array = []
var _free_nodes: Array = []
var after_setup: Callable = Callable()   # 자체 점검이 화면 설정 직후 값을 바꿔 보기 위한 훅(평소에는 비어 있음)


class FakeNote extends RefCounted:
	var timing_ms: float = 0.0
	var armed_hidden: bool = false
	func _init(t: float, hidden: bool = false) -> void:
		timing_ms = t
		armed_hidden = hidden


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


func _tree() -> SceneTree:
	return Engine.get_main_loop() as SceneTree


func _new_input() -> InputManager:
	var im := InputManager.new()
	_tree().root.add_child(im)
	_free_nodes.append(im)
	return im


func _key_of(mode: int, lane: int) -> int:
	var groups: Array = SPEC_GROUPS[mode]
	for i in groups.size():
		if lane in groups[i]:
			return i
	return -1


# 헤드리스 창은 100×100이고 ScreenLayout도 기본값이라, 실제 게임과 같은 조건(DESIGN §1 개발 기준 2400×1080)으로 맞춘다.
func _setup_screen() -> void:
	_tree().root.size = Vector2i(2400, 1080)
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))   # 내부에서 LaneSystem.rebuild()까지 호출
	if after_setup.is_valid():
		after_setup.call()


func run() -> Array:
	_setup_screen()
	_groups()
	_lane_positions()
	_physical_keys()
	_touch_zone()
	_touch_events()
	_keyboard_events()
	_lanes_to_judge()
	_pick_press_key()
	return results


# ── DESIGN §3 레인 구조 ───────────────────────────────────────────
func _groups() -> void:
	eq("레인: 레인 수 16 (DESIGN §3)", LaneSystem.LANE_COUNT, 16)
	for m in MODES:
		eq("키 모드 그룹표: %d키 = DESIGN §3 표" % m, LaneSystem.KEY_MODE_MAP[m], SPEC_GROUPS[m])
		var seen: Array = []
		for g in LaneSystem.KEY_MODE_MAP[m]:
			seen.append_array(g)
		seen.sort()
		eq("키 모드 그룹표: %d키는 0~15 레인을 빠짐·겹침 없이 나눔(%d그룹)" % [m, m], seen, range(16))
		eq("키 모드 그룹표: %d키의 그룹 수는 %d" % [m, m], LaneSystem.KEY_MODE_MAP[m].size(), m)

		var bad: Array = []
		for lane in 16:
			var k: int = LaneSystem.get_key_for_lane(m, lane)
			if k != _key_of(m, lane):
				bad.append("레인%d 기대 키%d 실제 %d" % [lane, _key_of(m, lane), k])
			if not (lane in LaneSystem.get_lanes_for_key(m, k)):
				bad.append("레인%d가 키%d의 레인 목록에 없음" % [lane, k])
		for lane in 16:
			if LaneSystem.get_group_lanes(lane, m) != SPEC_GROUPS[m][_key_of(m, lane)]:
				bad.append("get_group_lanes(레인%d) 불일치" % lane)
			if LaneSystem.get_group_span(lane, m) != SPEC_GROUPS[m][_key_of(m, lane)].size():
				bad.append("get_group_span(레인%d) 불일치" % lane)
		check("레인↔키 조회: %d키 모든 레인의 키·그룹·폭 조회가 표와 일치" % m, bad.is_empty(), "; ".join(bad.slice(0, 3)))
		eq("레인 수 조회: %d키의 lane_count_for_mode = 16" % m, LaneSystem.lane_count_for_mode(m), 16)

	eq("레인 조회: 표에 없는 키 모드(7)의 레인→키는 -1", LaneSystem.get_key_for_lane(7, 3), -1)
	eq("레인 조회: 표에 없는 키 모드(7)의 키→레인은 빈 배열", LaneSystem.get_lanes_for_key(7, 0), [])
	eq("레인 조회: 범위를 벗어난 키 번호는 빈 배열", [LaneSystem.get_lanes_for_key(4, -1), LaneSystem.get_lanes_for_key(4, 4)], [[], []])
	eq("레인 조회: 표에 없는 키 모드의 그룹 폭은 1", LaneSystem.get_group_span(5, 7), 1)


func _lane_positions() -> void:
	# (1) 기본 배치 — ScreenLayout 없이 계산할 때의 값이 DESIGN §3 표(왼쪽 -400~-50, 오른쪽 50~400, 간격 50)다.
	# 헤드리스에서는 오토로드가 트리에 붙기 전이라 ScreenLayout을 못 찾아 이 기본 배치로 계산된다.
	# (한 프레임을 기다려 실제 연결을 보려 하면 SupabaseHTTP._ready가 서버에 익명 로그인하므로 기다리지 않는다.)
	var ls = load("res://scripts/core/LaneSystem.gd").new()
	_free_nodes.append(ls)
	ls.rebuild()
	var xs: Array = []
	for i in 16:
		xs.append(ls.get_lane_x(i))
	var spec: Array = []
	for i in 8:
		spec.append(-400.0 + 50.0 * i)
	for i in 8:
		spec.append(50.0 + 50.0 * i)
	eq("레인 좌표(기본 배치): DESIGN §3 표 — 왼쪽 날개 -400~-50, 오른쪽 날개 50~400, 간격 50", xs, spec)
	var asc := true
	for i in range(1, 8):
		if not (xs[i] > xs[i - 1]) or not (xs[i + 8] > xs[i + 7]):
			asc = false
	check("레인 좌표: 날개 안에서 오른쪽으로 갈수록 X가 커짐", asc, str(xs))
	var spaced := true
	var g: float = xs[1] - xs[0]
	for i in range(1, 8):
		if absf((xs[i] - xs[i - 1]) - g) > TOL or absf((xs[i + 8] - xs[i + 7]) - g) > TOL:
			spaced = false
	check("레인 좌표: 날개 안 레인 간격이 모두 같음(간격 %s)" % str(g), spaced, str(xs))
	check("레인 좌표: 왼쪽 날개(0~7)는 X<0, 오른쪽 날개(8~15)는 X>0 — 중앙 X=0에는 레인이 없음",
		xs[7] < 0.0 and xs[8] > 0.0, "레인7 %s / 레인8 %s" % [str(xs[7]), str(xs[8])])
	var sym := true
	for i in 8:
		if absf(xs[i] + xs[15 - i]) > TOL:
			sym = false
	check("레인 좌표: 좌우 대칭(레인 i 와 15-i 의 X 합이 0)", sym, str(xs))
	eq("레인 좌표: 범위 밖 레인(-1, 16)의 X는 0", [ls.get_lane_x(-1), ls.get_lane_x(16)], [0.0, 0.0])
	var gc_ok := true
	for m in MODES:
		for gl in SPEC_GROUPS[m]:
			var expect: float = (xs[gl[0]] + xs[gl[gl.size() - 1]]) / 2.0
			if absf(ls.get_group_center_x(gl[0], m) - expect) > TOL:
				gc_ok = false
	check("레인 좌표: 그룹 중심 X = 그룹 첫·끝 레인 X의 평균(전 키 모드·전 그룹)", gc_ok)

	# (1-2) 오토로드 LaneSystem 의 실제 좌표 — 트리가 시작된 상태라 ScreenLayout 값으로 계산된다: 레인 i 의 월드 X = 터치 구역 i 의 중심
	var real_bad: Array = []
	for i in 16:
		var want_x: float = (i + 0.5) * 2400.0 / 16.0 - 1200.0
		if absf(LaneSystem.get_lane_x(i) - want_x) > TOL:
			real_bad.append("레인%d 기대 %.3f 실제 %.3f" % [i, want_x, LaneSystem.get_lane_x(i)])
	check("레인 좌표(실제 오토로드): 레인 i의 월드 X = (i+0.5)×화면폭/16 − 화면폭/2 (2400폭, 터치 구역 중심과 일치)", real_bad.is_empty(), "; ".join(real_bad.slice(0, 3)))

	# (2) 화면 비례 배치 — ScreenLayout 주석: "레인 i 월드 X = zone_w × (i − 7.5) → 터치 존 i 중심과 정확히 일치" (DESIGN §4: 터치는 화면 폭/16 칸)
	var vw: float = 2400.0
	var zone: float = vw / 16.0
	near("화면 비례 배치: 레인 간격 = 화면 폭/16 (2400폭 → 150)", ScreenLayout.lane_gap, zone)
	near("화면 비례 배치: 중앙 안쪽 오프셋 = 칸 폭의 절반(75)", ScreenLayout.lane_center_gap, zone * 0.5)
	near("화면 비례 배치: 외곽 레인 중심 X = 칸 폭 × 7.5 (1125)", ScreenLayout.lane_half_span, zone * 7.5)
	var rel_bad: Array = []
	for i in 16:
		var world_x: float = (-ScreenLayout.lane_half_span + i * ScreenLayout.lane_gap) if i < 8 else (ScreenLayout.lane_center_gap + (i - 8) * ScreenLayout.lane_gap)
		var touch_center_x: float = (i + 0.5) * zone - vw / 2.0
		if absf(world_x - touch_center_x) > TOL:
			rel_bad.append("레인%d 월드 %.3f / 터치 중심 %.3f" % [i, world_x, touch_center_x])
	check("화면 비례 배치: 모든 레인의 월드 X가 해당 터치 구역의 중심과 일치", rel_bad.is_empty(), "; ".join(rel_bad.slice(0, 3)))


# ── DESIGN §4 물리 키 배치 ────────────────────────────────────────
func _physical_keys() -> void:
	var k8 := [KEY_A, KEY_S, KEY_D, KEY_F, KEY_J, KEY_K, KEY_L, KEY_SEMICOLON]
	var names8 := ["A", "S", "D", "F", "J", "K", "L", ";"]
	for i in 8:
		var evs := InputMap.action_get_events("key_%d" % i) if InputMap.has_action("key_%d" % i) else []
		var code: int = (evs[0] as InputEventKey).keycode if evs.size() > 0 else -1
		eq("키 배치: key_%d = %s (DESIGN §4)" % [i, names8[i]], code, k8[i])
	var k16 := [KEY_SHIFT, KEY_Z, KEY_S, KEY_X, KEY_D, KEY_C, KEY_F, KEY_V, KEY_M, KEY_K, KEY_COMMA, KEY_L, KEY_PERIOD, KEY_SEMICOLON, KEY_SLASH, KEY_ENTER]
	var names16 := ["Left Shift", "Z", "S", "X", "D", "C", "F", "V", "M", "K", ",", "L", ".", ";", "/", "Enter"]
	for i in 16:
		var evs16 := InputMap.action_get_events("key16_%d" % i) if InputMap.has_action("key16_%d" % i) else []
		var code16: int = (evs16[0] as InputEventKey).keycode if evs16.size() > 0 else -1
		eq("키 배치: key16_%d = %s (DESIGN §4, BMS DP LR2 표준)" % [i, names16[i]], code16, k16[i])
	var ls := InputMap.action_get_events("key16_0")
	eq("키 배치: key16_0은 왼쪽 Shift만(location 왼쪽)", (ls[0] as InputEventKey).location if ls.size() > 0 else -1, KEY_LOCATION_LEFT)

	# 키 모드별 액션 목록 — 16키는 key16_ 프리픽스, 나머지는 key_ (DESIGN §4). 4·5·6키의 키 배치는 DESIGN에 표가 없고 코드 주석(TASK_LIST #19 양손 분산)이 기준.
	var im := _new_input()
	var expect := {
		4: ["key_0", "key_1", "key_4", "key_5"],
		5: ["key_0", "key_1", "key_2+key_4", "key_5", "key_6"],
		6: ["key_0", "key_1", "key_2", "key_4", "key_5", "key_6"],
		8: ["key_0", "key_1", "key_2", "key_3", "key_4", "key_5", "key_6", "key_7"],
	}
	for m in [4, 5, 6, 8]:
		im.set_key_mode(m)
		var tag := "" if m == 8 else " [DESIGN에 표 없음·코드 주석 기준]"
		eq("키 모드별 액션: %d키 = %s%s" % [m, str(expect[m]), tag], im._actions, expect[m])
	im.set_key_mode(16)
	var a16: Array = []
	for i in 16:
		a16.append("key16_%d" % i)
	eq("키 모드별 액션: 16키는 key16_0~15 (DESIGN §4 prefix 자동 전환)", im._actions, a16)
	eq("키 모드별 액션: 16키의 눌림 배열 크기 16", im._held_keys.size(), 16)


# ── 터치 구역 (DESIGN §4: 화면 폭을 16등분한 레인 칸 → 그 레인이 속한 키) ─────────
func _touch_zone() -> void:
	var im := _new_input()
	var vp_w: float = im.get_viewport().get_visible_rect().size.x
	eq("터치 구역: 시험 화면 폭은 개발 기준 2400 (DESIGN §1)", vp_w, 2400.0)
	var lane_w: float = vp_w / 16.0
	for m in MODES:
		im.set_key_mode(m)
		var bad: Array = []
		for lane in 16:
			var want := _key_of(m, lane)
			var xs := [(lane + 0.5) * lane_w, lane * lane_w + 0.01]
			for x in xs:
				var got: int = im.key_at_screen_x(x)
				if got != want:
					bad.append("x=%.2f 기대 키%d 실제 %d" % [x, want, got])
			if lane > 0:
				var gl: int = im.key_at_screen_x(lane * lane_w - 0.01)
				if gl != _key_of(m, lane - 1):
					bad.append("경계 바로 왼쪽 x=%.2f 기대 키%d 실제 %d" % [lane * lane_w - 0.01, _key_of(m, lane - 1), gl])
		check("터치 구역: %d키, 16개 레인 칸의 중앙·시작·바로 왼쪽 모두 그룹표대로 키 변환" % m, bad.is_empty(), "; ".join(bad.slice(0, 3)))
		eq("터치 구역: %d키, 화면 왼쪽 밖(x<0)은 첫 키로 고정" % m, im.key_at_screen_x(-50.0), _key_of(m, 0))
		eq("터치 구역: %d키, 화면 오른쪽 밖(x>폭)은 마지막 키로 고정" % m, im.key_at_screen_x(vp_w + 50.0), _key_of(m, 15))
	im.set_key_mode(5)
	eq("터치 구역: 5키 레인3 시작(x=3칸)부터 키1 — 예전 균등분할과 달라진 경계(DESIGN §4 2026-11-01)", im.key_at_screen_x(3.0 * lane_w + 0.01), 1)
	eq("터치 구역: 5키 레인6 시작(x=6칸)부터 키2(키2가 레인 4개로 가장 넓음)", im.key_at_screen_x(6.0 * lane_w + 0.01), 2)
	im.set_key_mode(6)
	eq("터치 구역: 6키 레인3 시작(x=3칸)부터 키1(레인 2개)", im.key_at_screen_x(3.0 * lane_w + 0.01), 1)


func _touch(idx: int, pos: Vector2, pressed: bool) -> InputEventScreenTouch:
	var e := InputEventScreenTouch.new()
	e.index = idx
	e.position = pos
	e.pressed = pressed
	return e


func _drag(idx: int, pos: Vector2) -> InputEventScreenDrag:
	var e := InputEventScreenDrag.new()
	e.index = idx
	e.position = pos
	return e


func _key(code: int, pressed: bool, loc: int = 0, echo: bool = false) -> InputEventKey:
	var e := InputEventKey.new()
	e.keycode = code
	e.pressed = pressed
	e.location = loc
	e.echo = echo
	return e


# ── 터치 입력 처리 ────────────────────────────────────────────────
func _touch_events() -> void:
	var im := _new_input()
	im.set_key_mode(4)
	var vp_w: float = im.get_viewport().get_visible_rect().size.x
	var lw: float = vp_w / 16.0
	var evlog: Array = []
	im.key_pressed.connect(func(k): evlog.append(["p", k]))
	im.key_released.connect(func(k): evlog.append(["r", k]))
	var started: Array = []
	im.touch_started.connect(func(i, p): started.append([i, p]))
	var kx := func(k: int) -> float: return lw * (4 * k + 2)   # 4키에서 키 k의 중앙 X

	var p0 := Vector2(kx.call(1), 300.0)
	im._unhandled_input(_touch(0, p0, true))
	eq("터치 입력: 손가락이 키1 구역에 닿으면 key_pressed(1) 한 번", evlog, [["p", 1]])
	eq("터치 입력: 눌린 키는 is_held, 마지막 입력은 터치·위치·손가락 번호가 기록됨",
		[im.is_held(1), im.last_press_touch, im.last_press_pos, im.last_press_finger], [true, true, p0, 0])
	eq("터치 입력: touch_started 신호는 (손가락, 위치)", started, [[0, p0]])
	im._unhandled_input(_touch(1, Vector2(kx.call(1) + lw * 0.3, 300.0), true))
	eq("터치 입력: 같은 키를 두 번째 손가락이 눌러도 key_pressed는 다시 나가지 않음", evlog, [["p", 1]])
	im._unhandled_input(_touch(0, p0, false))
	eq("터치 입력: 두 손가락 중 하나만 떼면 키는 계속 눌림(key_released 없음)", [evlog, im.is_held(1)], [[["p", 1]], true])
	im._unhandled_input(_touch(1, p0, false))
	eq("터치 입력: 마지막 손가락을 떼면 key_released(1)", [evlog, im.is_held(1)], [[["p", 1], ["r", 1]], false])

	evlog.clear()
	im._unhandled_input(_touch(0, Vector2(kx.call(0), 300.0), true))
	im._unhandled_input(_drag(0, Vector2(kx.call(0) + lw * 0.5, 320.0)))
	eq("터치 입력: 같은 구역 안에서 끌면 새 입력이 생기지 않음", evlog, [["p", 0]])
	im._unhandled_input(_drag(0, Vector2(kx.call(2), 320.0)))
	eq("터치 입력: 다른 구역으로 끌면 이전 키를 떼고(r0) 새 키를 누름(p2) — 이 순서", evlog, [["p", 0], ["r", 0], ["p", 2]])
	im._unhandled_input(_touch(0, Vector2(kx.call(2), 320.0), false))
	eq("터치 입력: 끌어간 손가락을 떼면 새 키가 떼짐", evlog[evlog.size() - 1], ["r", 2])

	# 라인판정 보정으로 이웃 키가 배정된 손가락 (DESIGN §4)
	evlog.clear()
	im._unhandled_input(_touch(0, Vector2(kx.call(1), 300.0), true))
	im.reassign_touch_key(0, 0)
	eq("보정 배정: 손가락을 키1에서 키0 소속으로 바꾸면 키1은 떼지고 키0이 눌림(신호는 보내지 않음)",
		[im.is_held(1), im.is_held(0), im.get_touch_for_key(0), im.get_touch_for_key(1), evlog], [false, true, 0, -1, [["p", 1]]])
	im._unhandled_input(_drag(0, Vector2(kx.call(1) + lw * 0.4, 330.0)))
	eq("보정 배정: 원래 구역 안에서 끌어도 배정이 유지됨(키 변화 없음)", [im.is_held(0), im.is_held(1), evlog], [true, false, [["p", 1]]])
	im._unhandled_input(_touch(0, Vector2(kx.call(1), 300.0), false))
	eq("보정 배정: 손을 떼면 배정된 키0이 떼짐(키1 아님)", evlog, [["p", 1], ["r", 0]])
	im.reassign_touch_key(5, 2)
	eq("보정 배정: 누르고 있지 않은 손가락이나 범위 밖 키 배정은 무시됨", [im.is_held(2), im.is_held(0)], [false, false])

	# 레인믹스로 키 모드가 바뀌는 순간 손가락 유지 (DESIGN §9, 2026-08-05 버그 수정)
	evlog.clear()
	im._unhandled_input(_touch(0, Vector2(lw * 5.5, 300.0), true))   # 4키에서 레인5 → 키1
	im.set_key_mode(8)
	eq("키 모드 전환: 4→8키로 바뀌어도 손가락이 선 위치(레인5)의 새 키(8키 키2)가 눌림으로 이어짐",
		[im.is_held(im.key_at_screen_x(lw * 5.5)), im.key_at_screen_x(lw * 5.5), im._held_keys.size()], [true, 2, 8])
	eq("키 모드 전환: 새 키 모드에서 그 손가락의 키 조회", im.get_touch_for_key(2), 0)
	im._unhandled_input(_touch(0, Vector2(lw * 5.5, 300.0), false))
	eq("키 모드 전환: 손을 떼면 새 키가 떼짐", im.is_held(2), false)

	im.set_key_mode(4)
	im.auto_play = true
	eq("is_held: 오토플레이면 항상 true, 터치 목록은 비어 있음", [im.is_held(0), im.is_held(3), im.get_touch_positions()], [true, true, []])
	im.auto_play = false
	eq("is_held: 범위 밖 키 번호는 false", [im.is_held(99), im.is_held(4)], [false, false])
	im._unhandled_input(_touch(7, Vector2(100.0, 100.0), true))
	eq("is_finger_down: 누르고 있는 손가락만 true", [im.is_finger_down(7), im.is_finger_down(8)], [true, false])
	im._unhandled_input(_touch(7, Vector2(100.0, 100.0), false))


# ── 키보드 입력 처리 ──────────────────────────────────────────────
func _keyboard_events() -> void:
	var im := _new_input()
	var evlog: Array = []
	im.key_pressed.connect(func(k): evlog.append(["p", k]))
	im.key_released.connect(func(k): evlog.append(["r", k]))
	var table := {
		4: [[KEY_A, 0], [KEY_S, 1], [KEY_J, 2], [KEY_K, 3]],
		5: [[KEY_A, 0], [KEY_S, 1], [KEY_D, 2], [KEY_J, 2], [KEY_K, 3], [KEY_L, 4]],
		6: [[KEY_A, 0], [KEY_S, 1], [KEY_D, 2], [KEY_J, 3], [KEY_K, 4], [KEY_L, 5]],
		8: [[KEY_A, 0], [KEY_S, 1], [KEY_D, 2], [KEY_F, 3], [KEY_J, 4], [KEY_K, 5], [KEY_L, 6], [KEY_SEMICOLON, 7]],
	}
	for m in [4, 5, 6, 8]:
		im.set_key_mode(m)
		var bad: Array = []
		for pair in table[m]:
			evlog.clear()
			im._unhandled_input(_key(pair[0], true))
			if evlog != [["p", pair[1]]]:
				bad.append("키코드 %d 기대 p%d 실제 %s" % [pair[0], pair[1], str(evlog)])
			evlog.clear()
			im._unhandled_input(_key(pair[0], false))
			if evlog != [["r", pair[1]]]:
				bad.append("뗌 키코드 %d 기대 r%d 실제 %s" % [pair[0], pair[1], str(evlog)])
		var tag := "" if m == 8 else " [코드 주석 기준]"
		check("키보드 입력: %d키, 물리 키 누름·뗌이 키 번호로 변환됨%s" % [m, tag], bad.is_empty(), "; ".join(bad.slice(0, 3)))
	im.set_key_mode(4)
	evlog.clear()
	im._unhandled_input(_key(KEY_D, true))
	eq("키보드 입력: 4키에 배정되지 않은 물리 키(D)는 무시됨", evlog, [])
	im._unhandled_input(_key(KEY_A, true))
	im._unhandled_input(_key(KEY_A, true))
	eq("키보드 입력: 누르고 있는 키를 다시 누른 이벤트는 key_pressed를 중복으로 보내지 않음", evlog, [["p", 0]])
	im._unhandled_input(_key(KEY_A, true, 0, true))
	eq("키보드 입력: 키 반복(echo)은 무시됨", evlog, [["p", 0]])
	eq("키보드 입력: 키보드로 누르면 last_press_touch는 false, 손가락 번호 -1", [im.last_press_touch, im.last_press_finger], [false, -1])
	im._unhandled_input(_key(KEY_A, false))

	im.set_key_mode(5)
	evlog.clear()
	im._unhandled_input(_key(KEY_D, true))
	im._unhandled_input(_key(KEY_J, true))
	eq("키보드 입력: 5키 가운데 키는 D와 J 둘 다 같은 키2이고 한 번만 눌림 처리", evlog, [["p", 2]])

	im.set_key_mode(16)
	var k16 := [KEY_SHIFT, KEY_Z, KEY_S, KEY_X, KEY_D, KEY_C, KEY_F, KEY_V, KEY_M, KEY_K, KEY_COMMA, KEY_L, KEY_PERIOD, KEY_SEMICOLON, KEY_SLASH, KEY_ENTER]
	var bad16: Array = []
	for i in 16:
		var loc: int = KEY_LOCATION_LEFT if i == 0 else 0
		evlog.clear()
		im._unhandled_input(_key(k16[i], true, loc))
		if evlog != [["p", i]]:
			bad16.append("key16_%d 기대 p%d 실제 %s" % [i, i, str(evlog)])
		im._unhandled_input(_key(k16[i], false, loc))
	check("키보드 입력: 16키, 물리 키 16개가 레인 0~15에 1:1 (DESIGN §4)", bad16.is_empty(), "; ".join(bad16.slice(0, 3)))
	evlog.clear()
	im._unhandled_input(_key(KEY_SHIFT, true, KEY_LOCATION_RIGHT))
	eq("키보드 입력: 오른쪽 Shift는 16키 0번(왼쪽 Shift 전용)을 누르지 않음", evlog, [])


# ── 키 한 번에 판정되는 노트 (DESIGN §5, 2026-10-09) ─────────────────
func _active(spec: Array) -> Dictionary:
	var d := {}
	for s in spec:
		if not d.has(s[0]):
			d[s[0]] = []
		d[s[0]].append(FakeNote.new(s[1], s.size() > 2 and s[2]))
	return d


func _lanes_to_judge() -> void:
	var g4: Array = [0, 1, 2, 3]
	eq("한 번 누름: 가까운 이웃 노트(+107ms, +214ms)는 같이 판정하지 않고 가장 이른 노트 하나만",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0], [1, 1107.0], [2, 1214.0]]), g4, 1000.0), [0])
	eq("한 번 누름: 같은 시각(동시치기) 노트는 함께 판정(2ms 이내 허용)",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0], [1, 1000.0], [2, 1002.0]]), g4, 1000.0), [0, 1, 2])
	eq("한 번 누름: 2ms를 넘는 어긋남(2.5ms)은 동시치기가 아님",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0], [3, 1002.5]]), g4, 1000.0), [0])
	eq("한 번 누름: 판정 창 안에서 가장 이른 노트 기준(900ms 노트가 있으면 1000ms 노트는 제외)",
		LaneSystem.lanes_to_judge(_active([[1, 900.0], [0, 1000.0]]), g4, 1000.0), [1])
	eq("한 번 누름: 입력이 노트 시각보다 250ms 늦어도(Oops 창 끝) 판정 대상",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0]]), g4, 1250.0), [0])
	eq("한 번 누름: 251ms 이상 늦으면 대상 없음(Miss 범위)",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0]]), g4, 1251.0), [])
	eq("한 번 누름: 250ms 일찍 눌러도 판정 대상",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0]]), g4, 750.0), [0])
	eq("한 번 누름: 레인믹스 진입 대기로 숨겨 둔 노트(armed_hidden)는 건너뜀",
		LaneSystem.lanes_to_judge(_active([[0, 1000.0, true], [1, 1100.0]]), g4, 1000.0), [1])
	eq("한 번 누름: 노트가 없으면 빈 결과", LaneSystem.lanes_to_judge({}, g4, 1000.0), [])
	eq("한 번 누름: 각 레인의 맨 앞 노트만 본다(같은 레인 뒤 노트는 무시)",
		LaneSystem.lanes_to_judge(_active([[0, 1200.0], [0, 1000.0]]), g4, 1000.0), [0])
	eq("한 번 누름: 다른 키 그룹의 레인에 있는 노트는 대상이 아님",
		LaneSystem.lanes_to_judge(_active([[4, 1000.0]]), g4, 1000.0), [])


# ── 라인판정 보정 (DESIGN §4, 2026-11-02: 홈 키의 굿 이내 노트가 있으면 항상 홈 키) ──
func _pick_press_key() -> void:
	eq("보정 폭: LINE_JUDGE_MARGIN_LANES = 0.5레인 (DESIGN §4, 사용자 선택)", GameBalance.LINE_JUDGE_MARGIN_LANES, 0.5)
	var vp := 1600.0   # 레인 칸 폭 100이 되는 시험용 화면 폭
	var mg: float = GameBalance.LINE_JUDGE_MARGIN_LANES
	var t := 1000.0
	# 4키: 키0=x[0,400) 키1=[400,800) 키2=[800,1200) 키3=[1200,1600)
	eq("보정: 경계에서 0.5레인(50) 이상 안쪽(x=450)이면 이웃 노트가 있어도 홈 키",
		LaneSystem.pick_press_key(_active([[3, t]]), 4, 450.0, vp, t, mg), 1)
	eq("보정: 경계 안쪽 30(x=430) — 홈 노트가 굿 이내(+100ms)면 이웃 노트가 더 정확해도(0ms) 홈 키",
		LaneSystem.pick_press_key(_active([[4, t + 100.0], [3, t]]), 4, 430.0, vp, t, mg), 1)
	eq("보정: 홈 노트가 굿 경계(170ms)면 홈 키",
		LaneSystem.pick_press_key(_active([[4, t + 170.0], [3, t]]), 4, 430.0, vp, t, mg), 1)
	eq("보정: 홈 노트가 굿보다 나쁨(171ms)이고 이웃이 더 가까우면(20ms) 이웃 키",
		LaneSystem.pick_press_key(_active([[4, t + 171.0], [3, t + 20.0]]), 4, 430.0, vp, t, mg), 0)
	eq("보정: 홈 노트가 없고 이웃에만 있으면 이웃 키",
		LaneSystem.pick_press_key(_active([[3, t + 20.0]]), 4, 430.0, vp, t, mg), 0)
	eq("보정: 홈·이웃 모두 노트가 없으면 홈 키",
		LaneSystem.pick_press_key({}, 4, 430.0, vp, t, mg), 1)
	eq("보정: 이웃에 노트가 없으면 홈 키", LaneSystem.pick_press_key(_active([[4, t + 200.0]]), 4, 430.0, vp, t, mg), 1)
	eq("보정: 시간 차가 2ms 이내로만 이웃이 낫다면 홈 키(198ms vs 200ms)",
		LaneSystem.pick_press_key(_active([[4, t + 200.0], [3, t + 198.0]]), 4, 430.0, vp, t, mg), 1)
	eq("보정: 이웃이 2ms를 넘게 낫다면 이웃 키(197ms vs 200ms)",
		LaneSystem.pick_press_key(_active([[4, t + 200.0], [3, t + 197.0]]), 4, 430.0, vp, t, mg), 0)
	eq("보정: 구역 오른쪽 경계에서 10 안쪽(x=790) — 오른쪽 이웃(키2)이 후보",
		LaneSystem.pick_press_key(_active([[8, t + 20.0]]), 4, 790.0, vp, t, mg), 2)
	eq("보정: 구역 오른쪽 경계 근처에서도 홈 노트가 굿 이내면 홈 키",
		LaneSystem.pick_press_key(_active([[4, t + 100.0], [8, t]]), 4, 790.0, vp, t, mg), 1)
	eq("보정: 맨 왼쪽 키의 화면 가장자리(x=10)에는 왼쪽 이웃이 없어 홈 키",
		LaneSystem.pick_press_key(_active([[4, t]]), 4, 10.0, vp, t, mg), 0)
	eq("보정: 맨 오른쪽 키의 화면 가장자리(x=1590)에는 오른쪽 이웃이 없어 홈 키",
		LaneSystem.pick_press_key(_active([[0, t]]), 4, 1590.0, vp, t, mg), 3)
	eq("보정: 6키 키1(레인3~4, x[300,500)) 안쪽 20(x=320) — 왼쪽 이웃 키0에만 노트가 있으면 키0",
		LaneSystem.pick_press_key(_active([[2, t + 20.0]]), 6, 320.0, vp, t, mg), 0)
	eq("보정: 표에 없는 키 모드(7)는 -1", LaneSystem.pick_press_key({}, 7, 100.0, vp, t, mg), -1)
