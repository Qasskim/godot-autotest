extends RefCounted
# 모듈 11 — 스크롤 계산·화면 비례 레이아웃·도트 폰트 크기
#   NotePositionCalculator : 누적 스크롤 테이블, 노트 Y, 원근 배율 (DESIGN §10)
#   ScreenLayout._rebuild  : 모든 화면비에서 레이아웃 비례 계산 (DESIGN §1 전 화면비 대응, §4 레인=터치 구역, §13-3 도트 1칸 3px)
#   ScreenLayout.pixel_font_spec : 글자 크기는 설계 크기(15/12/10/8)의 정수 배수 (DESIGN §13-2)
# 기대값은 손으로 계산한 값이다: 120BPM 한 박 = 500ms = BASE_PIVOT(200px) → 0.4px/ms, 240BPM → 0.8px/ms.

const TOL := 1e-6
const RESOLUTIONS := [Vector2(2400, 1080), Vector2(1920, 1080), Vector2(1600, 720), Vector2(2560, 1080), Vector2(2160, 1080),
	Vector2(1920, 1200), Vector2(1600, 1200), Vector2(1280, 960), Vector2(1440, 900), Vector2(2960, 1440), Vector2(800, 600)]

var needs_frames := true   # ScreenLayout._rebuild 가 get_tree()를 쓰므로 트리가 시작된 뒤에 돈다
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
			n.free()
	_free_nodes.clear()


func _calc(bpm: float, events: Array = []) -> NotePositionCalculator:
	var music := MusicPlayer.new()
	var calc := NotePositionCalculator.new()
	calc._music = music
	calc.setup_chart({"bpm": bpm}, events)
	_free_nodes.append_array([music, calc])
	return calc


func _at(calc: NotePositionCalculator, now: float) -> void:
	calc._frame_now_ms = now
	calc._frame_scroll_pos = calc.get_scroll_pos(now)


func run() -> Array:
	(Engine.get_main_loop() as SceneTree).root.size = Vector2i(2400, 1080)
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))   # 개발 기준 화면(DESIGN §1)
	_scroll_table()
	_note_y_and_scale()
	_screen_layout()
	_pixel_fonts()
	return results


# ── 누적 스크롤 테이블 (DESIGN §10: BPM 구간별 누적 스크롤 테이블, 이진 탐색 조회, 배속은 조회 때 곱함) ──
func _scroll_table() -> void:
	eq("스크롤 수치: BASE_PIVOT = 200 (DESIGN §10)", NotePositionCalculator.BASE_PIVOT, 200.0)
	var c := _calc(120.0)
	near("스크롤: 120BPM — 한 박(500ms)이 BASE_PIVOT 200px, 위치(1000ms) = 400", c.get_scroll_pos(1000.0), 400.0)
	near("스크롤: 곡 시작(0ms) 위치 0", c.get_scroll_pos(0.0), 0.0)
	near("스크롤: 위치는 시각에 비례(120BPM, 3000ms = 1200)", c.get_scroll_pos(3000.0), 1200.0)
	near("스크롤: 곡 시작 전(-3000ms, 카운트다운) 위치는 음수로 이어짐(-1200)", c.get_scroll_pos(-3000.0), -1200.0)
	var c60 := _calc(60.0)
	near("스크롤: 60BPM은 절반 속도 — 1000ms = 200", c60.get_scroll_pos(1000.0), 200.0)

	var ev := _calc(120.0, [{"measure": 4, "bpm": 240.0}])   # 마디4 = 8000ms
	near("스크롤 변속: 변속 전(4000ms) 위치 = 1600", ev.get_scroll_pos(4000.0), 1600.0)
	near("스크롤 변속: 변속 시점(8000ms)까지 누적 = 3200", ev.get_scroll_pos(8000.0), 3200.0)
	near("스크롤 변속: 변속 후 1000ms는 240BPM(0.8px/ms)으로 +800 → 4000", ev.get_scroll_pos(9000.0), 4000.0)
	var two := _calc(120.0, [{"measure": 2, "bpm": 60.0}, {"measure": 4, "bpm": 240.0}])   # 4000ms에서 60BPM, 12000ms에서 240BPM
	near("스크롤 변속(2번): 4000ms까지 1600, 60BPM(0.2px/ms) 구간은 마디2~3(8000ms)이라 +1600 → 12000ms에서 3200", two.get_scroll_pos(12000.0), 3200.0)
	near("스크롤 변속(2번): 마지막 구간 1000ms는 240BPM(0.8px/ms) → 13000ms에서 4000", two.get_scroll_pos(13000.0), 4000.0)
	var mono := true
	var prev := -INF
	for i in range(0, 20001, 250):
		var p: float = two.get_scroll_pos(float(i))
		if p < prev:
			mono = false
		prev = p
	check("스크롤 변속: 위치는 시각에 대해 줄지 않는다(0~20000ms)", mono)

	c.scroll_multiplier = 2.5
	near("배속: 위치에 배속을 곱함(2.5배속 1000ms = 1000)", c.get_scroll_pos(1000.0), 1000.0)
	ev.scroll_multiplier = 2.0
	near("배속: 변속 구간에도 선형(2배속 9000ms = 8000)", ev.get_scroll_pos(9000.0), 8000.0)
	var plain := NotePositionCalculator.new()
	_free_nodes.append(plain)
	near("스크롤: setup_chart 전 조회는 120BPM으로 계산(1000ms = 400)", plain.get_scroll_pos(1000.0), 400.0)
	eq("스크롤: 마디 테이블은 5000마디", c.get_timing_table().size(), 5000)
	eq("스크롤: BPM 조회는 ChartTiming과 같은 값", [ev.get_bpm_at(7999.0), ev.get_bpm_at(8000.0)], [120.0, 240.0])


# ── 노트 Y·원근 배율 ────────────────────────────────────────────────
func _note_y_and_scale() -> void:
	var c := _calc(120.0)
	var line: float = c.JUDGMENT_LINE_Y
	var spawn: float = c.NOTE_SPAWN_Y
	eq("노트 위치 기준: 판정선 Y는 개발 기준 화면(2400×1080)에서 300 (DESIGN §10)", line, 300.0)
	_at(c, 5000.0)
	near("노트 Y: 지금 시각의 노트는 판정선 위", c.get_note_y(5000.0), line)
	near("노트 Y: 한 박(500ms) 뒤의 노트는 판정선보다 200px 위(위가 음수 방향)", c.get_note_y(5500.0), line - 200.0)
	near("노트 Y: 이미 지난 노트(500ms 전)는 판정선보다 200px 아래", c.get_note_y(4500.0), line + 200.0)
	c.scroll_multiplier = 2.0
	_at(c, 5000.0)
	near("노트 Y: 2배속이면 같은 시간 간격이 2배 멀리(500ms 뒤 = 400px 위)", c.get_note_y(5500.0), line - 400.0)

	near("원근 배율: 스폰 지점은 0.75", c.get_scale(spawn), 0.75)
	near("원근 배율: 판정선은 1.0", c.get_scale(line), 1.0)
	near("원근 배율: 스폰~판정선 한가운데는 0.875", c.get_scale((spawn + line) / 2.0), 0.875)
	near("원근 배율: 스폰 지점보다 위(화면 밖)는 0.75 아래로 내려가지 않음(음수 폭으로 폴리곤이 꼬이는 문제 방지)", c.get_scale(spawn - 1000.0), 0.75)
	check("원근 배율: 판정선 아래로는 1보다 커진다(선형)", c.get_scale(line + 100.0) > 1.0)
	near("원근 X: 레인 X × 배율", c.get_perspective_x(0, spawn), LaneSystem.get_lane_x(0) * 0.75)
	_at(c, 5000.0)
	var pos: Vector2 = c.get_note_position(5000.0, 3)
	near("노트 위치: 판정 시각 노트는 판정선 Y에 레인 X × 1.0", pos.y, line)
	near("노트 위치: X", pos.x, LaneSystem.get_lane_x(3))
	eq("지난 노트 판단: 기본 150ms를 넘으면 지난 것", [c.is_past_judgment(4850.0), c.is_past_judgment(4849.0)], [false, true])


# ── 화면 비례 레이아웃 (DESIGN §1: 모든 화면비에서 레터박스 없이 정상 동작) ─────────────
func _screen_layout() -> void:
	var bad: Array = []
	for r in RESOLUTIONS:
		var vw: float = r.x
		var vh: float = r.y
		ScreenLayout._rebuild(r)
		var zone := vw / 16.0
		# 레인 바깥 가장자리가 화면 가장자리와 딱 맞는다(터치 구역 = 레인, DESIGN §4)
		var edge: float = ScreenLayout.lane_half_span + ScreenLayout.lane_w / 2.0
		if absf(edge - vw / 2.0) > TOL:
			bad.append("%dx%d 레인 가장자리 %.3f ≠ 화면 절반 %.3f" % [vw, vh, edge, vw / 2.0])
		if absf(ScreenLayout.lane_gap - zone) > TOL or absf(ScreenLayout.screen_half_w - vw / 2.0) > TOL:
			bad.append("%dx%d 레인 간격/화면 절반" % [vw, vh])
		# 판정선은 화면 높이에 비례(기준 1080에서 300), 스폰은 화면 위쪽 끝
		if absf(ScreenLayout.judgment_line_y - vh * 300.0 / 1080.0) > TOL:
			bad.append("%dx%d 판정선 %.3f" % [vw, vh, ScreenLayout.judgment_line_y])
		if absf(ScreenLayout.spawn_y + vh / 2.0) > TOL:
			bad.append("%dx%d 스폰 %.3f" % [vw, vh, ScreenLayout.spawn_y])
		if not (ScreenLayout.judgment_line_y < vh / 2.0 and ScreenLayout.spawn_y < ScreenLayout.judgment_line_y):
			bad.append("%dx%d 판정선이 화면 안에 없음" % [vw, vh])
		if ScreenLayout.ui_scale <= 0.0 or ScreenLayout.text_scale <= 0.0 or ScreenLayout.pixel_unit < 1:
			bad.append("%dx%d 배율이 양수가 아님" % [vw, vh])
	check("레이아웃: %d가지 해상도 모두 레인이 화면 폭을 딱 채우고 판정선·스폰이 화면 안에 비례해 놓임" % RESOLUTIONS.size(), bad.is_empty(), "; ".join(bad.slice(0, 3)))
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))
	eq("레이아웃: 기준 화면(2400×1080)의 도트 1칸 = 3px (DESIGN §13-3)", ScreenLayout.pixel_unit, 3)
	eq("레이아웃: 기준 화면에서 판정선 300, 스폰 -540(화면 높이의 절반) [구현 동작·DESIGN §10 문서는 스폰 -420]", [ScreenLayout.judgment_line_y, ScreenLayout.spawn_y], [300.0, -540.0])
	ScreenLayout._rebuild(Vector2(1200.0, 540.0))
	eq("레이아웃: 화면을 절반으로 줄이면 도트 1칸은 3×0.5=1.5 → 정수로 스냅(반올림 2)", ScreenLayout.pixel_unit, 2)
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))
	var before := [ScreenLayout.lane_gap, ScreenLayout.judgment_line_y, ScreenLayout.ui_scale, ScreenLayout.pixel_unit]
	for bad_size in [Vector2(0, 0), Vector2(0, 1080), Vector2(2400, 0), Vector2(-5, -5)]:
		ScreenLayout._rebuild(bad_size)
	eq("레이아웃: 회전 전환 중 비정상 크기(0·음수)는 무시하고 마지막 정상 레이아웃을 유지 (DESIGN §2 함정 2)",
		[ScreenLayout.lane_gap, ScreenLayout.judgment_line_y, ScreenLayout.ui_scale, ScreenLayout.pixel_unit], before)


# ── 도트 폰트 크기 (DESIGN §13-2: 설계 크기 8/10/12/15의 정수 배수, 오차 8% 이내면 큰 설계 크기 우선) ──
const DESIGN_OF_FILE := {"Galmuri14.ttf": 15, "Galmuri11.ttf": 12, "Galmuri9.ttf": 10, "Galmuri7.ttf": 8, "Galmuri11-Bold.ttf": 12}


func _pixel_fonts() -> void:
	var multiple_bad: Array = []
	var oracle_bad: Array = []
	var null_font := 0
	var order := [["Galmuri14.ttf", 15], ["Galmuri11.ttf", 12], ["Galmuri9.ttf", 10], ["Galmuri7.ttf", 8]]
	var px := 6.0
	while px <= 200.0:
		for bold in [false, true]:
			var spec: Dictionary = ScreenLayout.pixel_font_spec(px, bold)
			var font: FontFile = spec["font"]
			if font == null:
				null_font += 1
				continue
			var file: String = font.resource_path.get_file()
			var design: int = DESIGN_OF_FILE.get(file, 0)
			if design == 0 or int(spec["size"]) % design != 0 or int(spec["size"]) < design:
				multiple_bad.append("px=%s %s file=%s size=%s" % [str(px), "굵게" if bold else "보통", file, str(spec["size"])])
			if not bold:
				# 문서화된 규칙의 독립 계산: 큰 설계 크기부터 보며 오차가 허용(8% 또는 최소 2px) 이내인 첫 후보, 없으면 오차가 가장 작은 후보
				var tol := maxf(2.0, px * 0.08)
				var chosen := ""
				var chosen_size := 0
				var best_err := INF
				var best_file := ""
				var best_size := 0
				for o in order:
					var sz: int = maxi(1, roundi(px / o[1])) * o[1]
					var err := absf(sz - px)
					if chosen == "" and err <= tol:
						chosen = o[0]
						chosen_size = sz
					if err < best_err:
						best_err = err
						best_file = o[0]
						best_size = sz
				if chosen == "":
					chosen = best_file
					chosen_size = best_size
				if file != chosen or int(spec["size"]) != chosen_size:
					oracle_bad.append("px=%s 기대 %s/%d 실제 %s/%d" % [str(px), chosen, chosen_size, file, int(spec["size"])])
		px += 0.5
	eq("도트 폰트: 글꼴 파일 5종이 모두 불러와짐", null_font, 0)
	check("도트 폰트: 어떤 요청 크기(6~200px, 보통·굵게)에도 결과 크기는 그 글꼴 설계 크기의 정수 배수", multiple_bad.is_empty(), "%d건: %s" % [multiple_bad.size(), "; ".join(multiple_bad.slice(0, 3))])
	check("도트 폰트: 보통 글꼴 선택은 문서화된 규칙(큰 설계 크기 우선, 오차 8%% 이내)과 일치 (6~200px 0.5 단위)", oracle_bad.is_empty(), "%d건: %s" % [oracle_bad.size(), "; ".join(oracle_bad.slice(0, 3))])
	var bold_spec: Dictionary = ScreenLayout.pixel_font_spec(30.0, true)
	eq("도트 폰트: 굵게는 항상 Galmuri11-Bold(설계 12) — 30px 요청은 30/12=2.5를 반올림해 3배 = 36", [(bold_spec["font"] as FontFile).resource_path.get_file(), int(bold_spec["size"])], ["Galmuri11-Bold.ttf", 36])
	ScreenLayout._rebuild(Vector2(2400.0, 1080.0))
	var d: Dictionary = ScreenLayout.pixel_font_spec(ScreenLayout.DEFAULT_FONT_BASE_PX * ScreenLayout.text_scale)
	eq("도트 폰트: 기준 화면의 기본 글자 크기(16×text_scale 2.0 = 32px)는 Galmuri14의 정수 배 30", [(d["font"] as FontFile).resource_path.get_file(), int(d["size"])], ["Galmuri14.ttf", 30])
