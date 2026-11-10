extends RefCounted
# 모듈 22 — 게임 설정 저장·적용 (GameSettings: user://settings.cfg, 기준 DESIGN §12 볼륨/음소거/이퀄라이저, §14 곡별 배속·정렬 저장, §4 노트 랜덤·S-RANDOM 숨김, 2026-11-10)
#   - 볼륨 4종(BGM·SFX·KeySound·EventSfx)은 0~1 로 자르고 실제 오디오 버스에 적용, 음소거도 버스에 적용
#   - 이퀄라이저: 밴드 −6~+6dB 로 자름, 범위 밖 밴드 번호는 무시, 초기화하면 평탄
#   - 곡별 배속: 저장값 없으면 기본, 최소~최대로 자름, 같은 곡 폴더의 채보는 배속을 공유
#   - 저장 → 다시 읽기: 메모리를 기본값으로 되돌린 뒤 파일에서 읽어 모든 항목이 복원됨. S-RANDOM 은 읽을 때 "없음"으로, 크기가 틀린 이퀄라이저는 무시, 범위 밖 값은 자름
#   - 노트 랜덤 시드: 같은 곡·모드는 같은 시드를 저장해 재사용
# 시험이 끝나면 원래 설정 파일과 메모리 값으로 되돌린다. 기대값은 DESIGN·GameBalance 의 문장(배속 0.25~10, 기본 1.0)과 손계산이다. 서버는 쓰지 않는다.

var needs_frames := true
var results: Array = []
var _backup: PackedByteArray = PackedByteArray()
var _had_file := false


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float) -> void:
	check(name, absf(actual - expected) <= 0.01, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	if _had_file:
		var f := FileAccess.open(GameSettings.CFG_PATH, FileAccess.WRITE)
		f.store_buffer(_backup)
		f.close()
	else:
		DirAccess.remove_absolute(ProjectSettings.globalize_path(GameSettings.CFG_PATH))
	GameSettings._load()
	GameSettings._apply_sound_settings()


func bus_db(name: String) -> float:
	return AudioServer.get_bus_volume_db(AudioServer.get_bus_index(name))


func reset_memory() -> void:
	GameSettings.song_dir = ""
	GameSettings.show_touch_zones = false
	GameSettings.auto_orientation_flip = true
	GameSettings.song_scroll_speeds = {}
	GameSettings.song_sort_mode = 0
	GameSettings.song_sort_reverse = false
	GameSettings.ghost_target = {}
	GameSettings.low_spec_mode = false
	GameSettings.note_random_mode = 0
	GameSettings.note_random_reuse_seed = false
	GameSettings.note_random_seeds = {}
	GameSettings.target_grade = ""
	GameSettings.visual_theme = "astral_ocean"
	GameSettings.bgm_volume = 1.0
	GameSettings.bgm_muted = false
	GameSettings.sfx_volume = 1.0
	GameSettings.sfx_muted = false
	GameSettings.keysound_volume = 1.0
	GameSettings.keysound_muted = false
	GameSettings.event_sfx_volume = 1.0
	GameSettings.event_sfx_muted = false
	GameSettings.eq_gains_db = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


func run() -> Array:
	_had_file = FileAccess.file_exists(GameSettings.CFG_PATH)
	if _had_file:
		_backup = FileAccess.get_file_as_bytes(GameSettings.CFG_PATH)

	# ── 볼륨·음소거 (4개 버스) ──
	var setters := [
		["BGM", GameSettings.set_bgm_volume, GameSettings.set_bgm_muted, "bgm_volume", "bgm_muted"],
		["SFX", GameSettings.set_sfx_volume, GameSettings.set_sfx_muted, "sfx_volume", "sfx_muted"],
		["KeySound", GameSettings.set_keysound_volume, GameSettings.set_keysound_muted, "keysound_volume", "keysound_muted"],
		["EventSfx", GameSettings.set_event_sfx_volume, GameSettings.set_event_sfx_muted, "event_sfx_volume", "event_sfx_muted"],
	]
	for s in setters:
		var bus: String = s[0]
		s[1].call(0.5)
		near("%s 볼륨 0.5: 값 0.5, 버스 −6.02dB" % bus, GameSettings.get(s[3]), 0.5)
		near("%s 볼륨 0.5: 실제 버스 음량" % bus, bus_db(bus), -6.0206)
		s[1].call(1.7)
		eq("%s 볼륨 1.7: 1.0 으로 자름" % bus, GameSettings.get(s[3]), 1.0)
		s[1].call(-0.3)
		eq("%s 볼륨 −0.3: 0.0 으로 자름(버스는 바닥 −80dB)" % bus, [GameSettings.get(s[3]), absf(bus_db(bus) + 80.0) < 0.01], [0.0, true])
		s[1].call(1.0)
		s[2].call(true)
		eq("%s 음소거 켜기: 값과 버스" % bus, [GameSettings.get(s[4]), AudioServer.is_bus_mute(AudioServer.get_bus_index(bus))], [true, true])
		s[2].call(false)
		eq("%s 음소거 끄기: 값과 버스" % bus, [GameSettings.get(s[4]), AudioServer.is_bus_mute(AudioServer.get_bus_index(bus))], [false, false])

	# ── 이퀄라이저 ──
	GameSettings.reset_eq()
	GameSettings.set_eq_band(2, 10.0)
	eq("EQ 밴드 +10: +6 으로 자름", GameSettings.eq_gains_db[2], 6.0)
	GameSettings.set_eq_band(2, -10.0)
	eq("EQ 밴드 −10: −6 으로 자름", GameSettings.eq_gains_db[2], -6.0)
	GameSettings.set_eq_band(-1, 3.0)
	GameSettings.set_eq_band(10, 3.0)
	eq("범위 밖 밴드 번호(−1·10): 무시", GameSettings.eq_gains_db.size() == 10 and GameSettings.eq_gains_db.count(3.0) == 0, true)
	GameSettings.reset_eq()
	eq("EQ 초기화: 전 밴드 0", GameSettings.eq_gains_db, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])

	# ── 곡별 배속 ──
	var chart_a := "res://charts/keysound/songX/songX_EZ.rgds"
	var chart_b := "res://charts/keysound/songX/songX_HD.rgds"
	var chart_c := "res://charts/keysound/songY/songY_EZ.rgds"
	eq("저장값이 없는 곡: 기본 배속", GameSettings.get_song_scroll_speed(chart_a), GameBalance.SCROLL_SPEED_DEFAULT)
	eq("기본 배속은 1.0 (DESIGN §14)", GameBalance.SCROLL_SPEED_DEFAULT, 1.0)
	GameSettings.set_song_scroll_speed(chart_a, 2.5)
	eq("저장한 배속을 같은 곡의 다른 난이도도 공유", [GameSettings.get_song_scroll_speed(chart_a), GameSettings.get_song_scroll_speed(chart_b)], [2.5, 2.5])
	eq("다른 곡은 영향 없음", GameSettings.get_song_scroll_speed(chart_c), GameBalance.SCROLL_SPEED_DEFAULT)
	GameSettings.set_song_scroll_speed(chart_a, 99.0)
	eq("배속 최대로 자름(DESIGN 0.25~10)", [GameSettings.get_song_scroll_speed(chart_a), GameBalance.SCROLL_SPEED_MAX], [10.0, 10.0])
	GameSettings.set_song_scroll_speed(chart_a, 0.01)
	eq("배속 최소로 자름", [GameSettings.get_song_scroll_speed(chart_a), GameBalance.SCROLL_SPEED_MIN], [0.25, 0.25])
	GameSettings.set_song_scroll_speed(chart_a, 3.0)

	# ── 노트 랜덤 시드 ──
	var seed1 := GameSettings.get_or_create_note_random_seed("res://x/a.rgds", 1)
	eq("같은 곡·모드의 시드는 재사용", GameSettings.get_or_create_note_random_seed("res://x/a.rgds", 1), seed1)
	check("다른 모드는 별도 시드 항목", GameSettings.note_random_seeds.has("res://x/a.rgds|1") and not GameSettings.note_random_seeds.has("res://x/a.rgds|2"))

	# ── 저장 → 메모리 초기화 → 다시 읽기 ──
	GameSettings.set_show_touch_zones(true)
	GameSettings.set_auto_orientation_flip(false)
	GameSettings.set_song_sort(2, true)
	GameSettings.set_ghost_target({"type": "rival", "rival_user_id": "u-1", "display_name": "닉"})
	GameSettings.set_low_spec_mode(true)
	GameSettings.set_note_random_mode(1)
	GameSettings.set_note_random_reuse_seed(true)
	GameSettings.set_target_grade("S")
	GameSettings.set_visual_theme("cosmic_neon")
	GameSettings.set_bgm_volume(0.3)
	GameSettings.set_sfx_muted(true)
	GameSettings.set_eq_band(0, 4.0)
	GameSettings.set_eq_band(9, -2.0)
	var expect_eq: Array = GameSettings.eq_gains_db.duplicate()
	reset_memory()
	GameSettings._load()
	eq("다시 읽기: 터치 영역·자동 뒤집기·정렬", [GameSettings.show_touch_zones, GameSettings.auto_orientation_flip, GameSettings.song_sort_mode, GameSettings.song_sort_reverse], [true, false, 2, true])
	eq("다시 읽기: 고스트 대상", GameSettings.ghost_target, {"type": "rival", "rival_user_id": "u-1", "display_name": "닉"})
	eq("다시 읽기: 저사양·노트 랜덤·시드 재사용·목표 등급·테마", [GameSettings.low_spec_mode, GameSettings.note_random_mode, GameSettings.note_random_reuse_seed, GameSettings.target_grade, GameSettings.visual_theme], [true, 1, true, "S", "cosmic_neon"])
	near("다시 읽기: BGM 볼륨 0.3", GameSettings.bgm_volume, 0.3)
	eq("다시 읽기: SFX 음소거", GameSettings.sfx_muted, true)
	eq("다시 읽기: 이퀄라이저 값", GameSettings.eq_gains_db, expect_eq)
	eq("다시 읽기: 곡별 배속", GameSettings.get_song_scroll_speed(chart_b), 3.0)
	eq("다시 읽기: 노트 랜덤 시드", GameSettings.get_or_create_note_random_seed("res://x/a.rgds", 1), seed1)

	# ── 읽을 때의 방어 ──
	GameSettings.set_note_random_mode(NoteRandomizer.Mode.S_RANDOM)
	reset_memory()
	GameSettings._load()
	eq("S-RANDOM 으로 저장돼 있어도 읽을 때 '없음'(선택 목록에서 뺐음, DESIGN §7)", GameSettings.note_random_mode, NoteRandomizer.Mode.NONE)
	var cfg := ConfigFile.new()
	cfg.load(GameSettings.CFG_PATH)
	cfg.set_value("sound", "eq_gains_db", [1.0, 2.0, 3.0])
	cfg.save(GameSettings.CFG_PATH)
	reset_memory()
	GameSettings._load()
	eq("크기가 10 이 아닌 이퀄라이저 저장값은 무시(평탄)", GameSettings.eq_gains_db, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
	cfg.set_value("sound", "eq_gains_db", [99.0, -99.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
	cfg.save(GameSettings.CFG_PATH)
	reset_memory()
	GameSettings._load()
	eq("범위 밖 이퀄라이저 저장값은 읽을 때 자름(+6/−6)", [GameSettings.eq_gains_db[0], GameSettings.eq_gains_db[1]], [6.0, -6.0])
	return results
