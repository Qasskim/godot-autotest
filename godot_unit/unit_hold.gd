extends RefCounted
# 모듈 9 — 롱노트 처리 (기준: Godot/docs/DESIGN.md §6 롱노트 처리, 2026-11-04 "끝 앞 Oops 창" 항목)
# LongNoteVisual 을 곡 시계(MusicPlayer)와 입력(InputManager)을 직접 움직여 시험한다.
#   - 곡 시계: MusicPlayer._frozen=true 로 두고 _paused_pos_ms 에 원하는 시각(ms)을 넣어 결정적으로 진행한다.
#   - 손가락: InputManager._unhandled_input 에 터치 이벤트를 직접 넣는다(모듈 2와 같은 방식).
# 설정: 120BPM → 16분음표 틱 간격 125ms, 롱노트 시작 1000ms·길이 2000ms(끝 3000ms), 4키의 키1(레인 4).
# 틱은 매 프레임 now >= 다음 틱 시각일 때 처리되고, 끝 시각 프레임은 끝 처리가 먼저라 끝 시각의 틱은 처리되지 않는다(구현 동작).

const TOL := 1e-6
const T := 1000.0        # 롱노트 머리 시각(ms)
const L := 2000.0        # 길이(ms)
const END := 3000.0
const TICK := 125.0      # 120BPM 16분음표 = 60000/120/4
const LANE := 4          # 4키에서 키1의 레인
const STEP := 25.0       # 시계를 움직이는 단위(ms)
const G0 := 250.0        # 시험 시작 게이지(Expert 구간 한가운데)
const MISS_TICK := -2.4  # 틱 Miss: -6 × 20% × Expert 감소 ×2.0
const WOW_TICK := 0.15   # 틱 Wow: +0.75 × 20%
const GOOD_TICK := 0.05  # 틱 Good: +0.25 × 20%

var needs_frames := true   # InputManager 가 뷰포트를 읽으므로 트리가 시작된 뒤에 돈다
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


# ── 시험 환경 ─────────────────────────────────────────────────────
class Env extends RefCounted:
	var music: MusicPlayer
	var calc: NotePositionCalculator
	var judgment: JudgmentSystem
	var score: ScoreSystem
	var gauge: GaugeSystem
	var combo: ComboSystem
	var input: InputManager
	var note: LongNoteVisual
	var log: Array = []          # 판정 신호 [등급, 레인, 버스트]
	var tick_miss: int = 0
	var lw: float = 1.0          # 레인 한 칸의 화면 폭


func _env(length: float = L) -> Env:
	var tree := Engine.get_main_loop() as SceneTree
	var e := Env.new()
	e.music = MusicPlayer.new()
	e.music.is_playing_music = true
	e.music._frozen = true
	e.music._paused_pos_ms = 0.0
	e.calc = NotePositionCalculator.new()
	e.calc._music = e.music            # @onready 는 _ready 가 돌아야 채워지므로 직접 연결
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
	e.lw = e.input.get_viewport().get_visible_rect().size.x / 16.0
	e.judgment.judgment_made.connect(func(g, _err, l, b): e.log.append([g, l, b]))
	e.note = LongNoteVisual.new()      # 부모 없이 둔다 — 홀드 이펙트(화면 효과)는 생성하지 않는다
	e.note.setup(LANE, T, e.calc, e.music)
	e.note.length_ms = length
	e.note.key_mode = 4
	e.note.setup_systems(e.judgment, e.score, e.gauge, e.combo, e.input)
	e.note.tick_miss.connect(func(): e.tick_miss += 1)
	_free_nodes.append_array([e.music, e.calc, e.judgment, e.score, e.gauge, e.combo, e.input, e.note])
	return e


func _step(e: Env, now: float) -> void:
	e.music._paused_pos_ms = now
	e.calc._frame_now_ms = now
	e.calc._frame_scroll_pos = e.calc.get_scroll_pos(now)
	e.note._process(0.0)


func _run(e: Env, from_ms: float, to_ms: float) -> void:
	var t := from_ms
	while t <= to_ms + 0.001:
		_step(e, t)
		t += STEP


func _touch_down(e: Env, finger: int = 0) -> void:
	var ev := InputEventScreenTouch.new()
	ev.index = finger
	ev.position = Vector2(e.lw * 5.5, 300.0)     # 4키의 키1 구역(레인 4~7) 한가운데
	ev.pressed = true
	e.input._unhandled_input(ev)


func _touch_up(e: Env, finger: int = 0) -> void:
	var ev := InputEventScreenTouch.new()
	ev.index = finger
	ev.position = Vector2(e.lw * 5.5, 300.0)
	ev.pressed = false
	e.input._unhandled_input(ev)


func _grades(e: Env) -> Array:
	var g: Array = []
	for r in e.log:
		g.append(r[0])
	return g


func run() -> Array:
	(Engine.get_main_loop() as SceneTree).root.size = Vector2i(2400, 1080)   # 개발 기준 화면(DESIGN §1) — 터치 구역 계산이 화면 폭을 읽는다
	_setup_constants()
	_normal_hold()
	_early_release()
	_release_window()
	_head_miss_and_rescue()
	_reentry_after_leave()
	_autoplay_and_keyboard()
	return results


func _setup_constants() -> void:
	eq("롱노트 수치: 끝 앞 허용 창은 Oops 창(250ms) — DESIGN §6 2026-11-04", GameBalance.judgment_windows["Oops"], 250.0)
	var e := _env()
	eq("시험 설정: 120BPM의 틱 간격은 125ms(16분음표)", 60000.0 / e.calc.get_bpm_at(T) / 4.0, TICK)


# ── 정상 홀드 (DESIGN §6: 헤드 입력 → 홀드 중 틱 → 테일 도달 시 확정) ──────────────
func _normal_hold() -> void:
	var e := _env()
	_touch_down(e)
	e.note.on_press(T + 100.0)         # 100ms 늦게 눌러 헤드 등급 Good
	eq("롱 헤드: 눌렀을 때 헤드 등급(오차 100ms)이 틱 등급으로 저장됨", e.note._tick_judgment, "Good")
	eq("롱 헤드: 홀드 중 상태, 잡은 키는 키1, 손가락 0", [e.note._is_held, e.note._held_key, e.note._held_finger], [true, 1, 0])
	_run(e, T + 100.0, END)
	near("롱 홀드(Good 헤드): 홀드 중 틱마다 게이지 +0.25×20% — 15틱(끝 시각 틱 제외) → 250.75", e.gauge.gauge, G0 + 15.0 * GOOD_TICK)
	eq("롱 홀드: 테일에서 헤드 등급(Good) 판정이 한 번만 나감(버스트 없음)", e.log, [["Good", LANE, false]])
	eq("롱 홀드: 끝까지 쥐면 테일에서 노트가 사라짐", e.note.is_queued_for_deletion(), true)
	eq("롱 홀드: 쥐고 있었으니 틱 Miss 없음·콤보 끊김 없음", [e.tick_miss, e.combo.break_count], [0, 0])

	var w := _env()
	_touch_down(w)
	w.note.on_press(T)                 # 정확히 눌러 헤드 Wow
	_run(w, T, END)
	near("롱 홀드(Wow 헤드): 틱은 헤드 등급 기준 +0.75×20% → 15틱 252.25 (DESIGN §6)", w.gauge.gauge, G0 + 15.0 * WOW_TICK)
	eq("롱 홀드(Wow 헤드): 테일에서 헤드 등급(Wow)이 나감 — 롱노트의 점수 판정은 이 한 번 (DESIGN §6)", w.log, [["Wow", LANE, false]])


# ── 끝 앞 창 밖에서 뗌 = 이탈 (DESIGN §6: Miss·콤보 0) ──────────────────────────
func _early_release() -> void:
	var e := _env()
	for i in 5:
		e.combo.apply_judgment("Wow")
	_touch_down(e)
	e.note.on_press(T)
	_run(e, T, 1475.0)
	_touch_up(e)
	_step(e, 1500.0)
	eq("롱 이탈: 끝 250ms보다 일찍 떼면 Miss 판정이 즉시 한 번", e.log, [["Miss", LANE, false]])
	eq("롱 이탈: 콤보 0, 끊긴 횟수 1, hold_broken", [e.combo.current_combo, e.combo.break_count, e.combo.hold_broken], [0, 1, true])
	_run(e, 1525.0, END)
	eq("롱 이탈: 남은 구간 동안 틱마다 Miss 틱(15틱 중 이탈 전 3틱을 뺀 12틱)", e.tick_miss, 12)
	near("롱 이탈: 게이지 = 홀드 틱 3×(+0.15) + Miss 틱 12×(-6×20%×Expert 2.0)", e.gauge.gauge, G0 + 3.0 * WOW_TICK + 12.0 * MISS_TICK)
	eq("롱 이탈: 테일에서는 추가 판정 없음(Miss가 이미 나감)", e.log, [["Miss", LANE, false]])


# ── 끝 앞 Oops 창(250ms) 안에서 뗌 = 이탈 아님 (DESIGN §6, 2026-11-04) ─────────────
func _release_window() -> void:
	var e := _env()
	for i in 5:
		e.combo.apply_judgment("Wow")
	_touch_down(e)
	e.note.on_press(T)
	_run(e, T, 2725.0)
	_touch_up(e)
	_step(e, 2750.0)      # 끝(3000) - 250 = 2750: 경계 포함
	eq("끝 앞 창(경계 2750ms 포함): 이탈이 아니라 창 안에서 뗌으로 처리", [e.note._released_in_window, e.note._is_held], [true, false])
	_run(e, 2775.0, END)
	eq("끝 앞 창: Miss 없이 테일에서 헤드 등급(Wow)이 나감", e.log, [["Wow", LANE, false]])
	eq("끝 앞 창: 콤보 끊김 없음·틱 Miss 없음", [e.combo.current_combo, e.combo.break_count, e.tick_miss], [5, 0, 0])
	near("끝 앞 창: 남은 틱은 헤드 등급(Wow)으로 게이지에 반영 — 15틱 모두 +0.15", e.gauge.gauge, G0 + 15.0 * WOW_TICK)

	var b := _env()
	_touch_down(b)
	b.note.on_press(T)
	_run(b, T, 2700.0)
	_touch_up(b)
	_step(b, 2749.0)      # 경계보다 1ms 이른 시각에 떼었음을 감지
	eq("끝 앞 창 경계 바로 밖(2749ms): 이탈로 보고 Miss", [b.log, b.note._released_in_window], [[["Miss", LANE, false]], false])


# ── 헤드 미스와 구제 (DESIGN §6: 헤드 미스 → 틱마다 Miss, 이후 입력하면 판정선 고정·틱 재개) ──
func _head_missed_ticks_run(e: Env) -> void:
	_run(e, 0.0, 1075.0)
	eq("헤드 미스 전: 아직 판정 없음(헤드 판정 창이 지나기 전)", e.log.size(), 0)


func _head_miss_and_rescue() -> void:
	var e := _env()
	_head_missed_ticks_run(e)
	_step(e, 1125.0)
	eq("헤드 미스: 머리 시각 +100ms를 넘기면 Miss 판정이 한 번 나감", e.log, [["Miss", LANE, false]])
	_run(e, 1150.0, END)
	eq("헤드 미스: 입력이 없으면 끝까지 틱마다 Miss(15틱)", e.tick_miss, 15)
	near("헤드 미스: 게이지 = Miss 틱 15×(-6×20%×Expert 2.0) = 250-36", e.gauge.gauge, G0 + 15.0 * MISS_TICK)
	eq("헤드 미스: 테일에서 추가 판정 없음", e.log.size(), 1)

	var r := _env()
	_run(r, 0.0, 1475.0)
	_touch_down(r)
	_step(r, 1500.0)
	eq("헤드 미스 구제: 미스 뒤 키를 누르면 판정선에 고정되어 홀드 중이 됨", [r.note._judged_head, r.note._is_held, r.note._tick_judgment], [true, true, "Good"])
	_run(r, 1525.0, END)
	near("헤드 미스 구제: Miss 틱 3(구제 전) + Good 틱 11(구제 후 1625~2875)", r.gauge.gauge, G0 + 3.0 * MISS_TICK + 11.0 * GOOD_TICK)
	eq("헤드 미스 구제: 판정은 처음 Miss 하나뿐(테일 추가 판정 없음)", r.log, [["Miss", LANE, false]])


# ── 헤드 판정 뒤 이탈했다가 재진입 (DESIGN §6: Good으로 다운그레이드해 틱 재개) ──────
func _reentry_after_leave() -> void:
	var e := _env()
	_touch_down(e)
	e.note.on_press(T)
	_run(e, T, 1475.0)
	_touch_up(e)
	_run(e, 1500.0, 1775.0)
	_touch_down(e)
	_step(e, 1800.0)
	eq("재진입: 이탈 뒤 다시 누르면 홀드 중이 되고 틱 등급은 Good으로 내려감", [e.note._is_held, e.note._tick_judgment], [true, "Good"])
	_run(e, 1825.0, END)
	near("재진입: 홀드 틱 3×(+0.15) + 이탈 Miss 틱 3×(-2.4) + 재진입 Good 틱 9×(+0.05)", e.gauge.gauge, G0 + 3.0 * WOW_TICK + 3.0 * MISS_TICK + 9.0 * GOOD_TICK)
	eq("재진입: 판정은 이탈 때의 Miss 하나뿐(테일 추가 판정 없음)", e.log, [["Miss", LANE, false]])
	eq("재진입: 콤보는 이탈 때 한 번만 끊김", e.combo.break_count, 0 if e.combo.current_combo == 0 and e.combo.hold_broken == false else e.combo.break_count)


# ── 오토플레이와 키보드 ─────────────────────────────────────────────
func _autoplay_and_keyboard() -> void:
	var a := _env()
	a.input.auto_play = true
	a.note.on_press(T)
	_run(a, T, END)
	eq("오토플레이: 손을 안 대도 끝까지 홀드로 인정되어 헤드 등급(Wow)이 나감", a.log, [["Wow", LANE, false]])
	near("오토플레이: 틱 15개 모두 홀드 틱(+0.15)", a.gauge.gauge, G0 + 15.0 * WOW_TICK)

	var k := _env()
	var press := InputEventKey.new()
	press.keycode = KEY_S               # 4키의 키1은 S
	press.pressed = true
	k.input._unhandled_input(press)
	k.note.on_press(T)
	eq("키보드 홀드: 키로 잡으면 손가락 번호 없이 키 기준으로 홀드", [k.note._held_key, k.note._held_finger], [1, -1])
	_run(k, T, 1475.0)
	var rel := InputEventKey.new()
	rel.keycode = KEY_S
	rel.pressed = false
	k.input._unhandled_input(rel)
	_step(k, 1500.0)
	eq("키보드 홀드: 키를 떼면(끝 창 밖) 이탈로 Miss", k.log, [["Miss", LANE, false]])
