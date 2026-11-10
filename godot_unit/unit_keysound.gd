extends RefCounted
# 모듈 23 — 키음 불러오기 (KeySoundManager: load_sounds·has_sound·load_audio_stream·확장자 폴백, 기준 DESIGN §8 sounds 배열·곡 폴더 구조)
#   - 채보의 sounds 목록을 읽으면 이름마다 has_sound 가 참, 목록에 없는 이름은 거짓
#   - 이름이 비었거나 경로가 빈 항목은 건너뜀, 없는 파일은 등록되지 않음(오류 없이 경고)
#   - 상대 경로는 채보 파일 폴더 기준, 다시 읽으면 이전 목록이 지워짐
#   - 요청한 확장자 파일이 없으면 같은 이름의 .ogg/.mp3/.wav 로 대신 찾음(BMS는 .wav 를 적고 실제는 .ogg 인 경우, 코드 주석)
#   - load_audio_stream: 있는 파일은 스트림, 없는 파일은 null
#   - 없는 키음 이름으로 재생해도 오류 없음
# 서버는 쓰지 않는다. 임시 wav 파일은 시험이 만든다.

const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")
const CHART := "res://charts/Tutorial/stage1_basic_notes.rgds"

var needs_frames := true
var results: Array = []
var tmp := "user://unit_keysound_test"


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	var d := DirAccess.open(ProjectSettings.globalize_path(tmp))
	if d != null:
		for f in d.get_files():
			DirAccess.remove_absolute(ProjectSettings.globalize_path(tmp).path_join(f))
		DirAccess.remove_absolute(ProjectSettings.globalize_path(tmp))
	KeySoundManager.load_sounds([], CHART)


func make_wav(path: String) -> void:
	var s := AudioStreamWAV.new()
	s.format = AudioStreamWAV.FORMAT_16_BITS
	s.mix_rate = 22050
	var data := PackedByteArray()
	data.resize(2000)
	s.data = data
	s.save_to_wav(path)


func run() -> Array:
	cleanup()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(tmp))
	var chart := ChartLoader.load_file(CHART)
	var sounds: Array = ChartLoader.get_sounds(chart)
	check("튜토리얼 1단계 채보에 sounds 가 있음", sounds.size() > 0, "개수 %d" % sounds.size())

	KeySoundManager.load_sounds(sounds, CHART)
	var missing: Array = []
	for entry in sounds:
		if not KeySoundManager.has_sound(entry["name"]):
			missing.append(entry["name"])
	check("sounds 의 모든 이름이 불러와짐(%d개)" % sounds.size(), missing.is_empty(), "못 불러온 것 %s" % str(missing.slice(0, 5)))
	eq("목록에 없는 이름은 거짓", KeySoundManager.has_sound("없는_소리"), false)
	KeySoundManager.play("없는_소리", 1.0, 0)
	KeySoundManager.play_event_sfx("없는_소리")
	check("없는 이름으로 재생해도 오류 없음", true)

	# ── 항목 거르기·덮어 읽기 ──
	KeySoundManager.load_sounds([{"name": "", "path": "a.wav"}, {"name": "x", "path": ""}, {"name": "ghost", "path": "res://audio/없는파일.wav"}], CHART)
	eq("이름·경로가 비었거나 파일이 없는 항목은 등록되지 않음", [KeySoundManager.has_sound(""), KeySoundManager.has_sound("x"), KeySoundManager.has_sound("ghost")], [false, false, false])
	eq("다시 읽으면 이전 목록이 지워짐", KeySoundManager.has_sound(sounds[0]["name"]), false)

	# ── 상대 경로와 확장자 폴백 ──
	make_wav(tmp + "/beep.wav")
	var chart_path := tmp + "/dummy.rgds"
	KeySoundManager.load_sounds([{"name": "rel", "path": "beep.wav"}, {"name": "alt", "path": "beep.ogg"}, {"name": "abs", "path": tmp + "/beep.wav"}], chart_path)
	eq("상대 경로: 채보 폴더 기준으로 찾음", KeySoundManager.has_sound("rel"), true)
	eq("확장자 폴백: beep.ogg 가 없으면 beep.wav 로 대신 찾음", KeySoundManager.has_sound("alt"), true)
	eq("절대(user://) 경로도 읽음", KeySoundManager.has_sound("abs"), true)

	# ── load_audio_stream ──
	var existing := KeySoundManager.load_audio_stream(tmp + "/beep.wav")
	check("있는 파일: 스트림을 돌려줌", existing != null and existing is AudioStream)
	eq("없는 파일: null", KeySoundManager.load_audio_stream(tmp + "/없음.wav"), null)
	var first_song := "res://charts/keysound"
	var d := DirAccess.open(first_song)
	var dirs := Array(d.get_directories())
	dirs.sort()
	var preview := ChartLoader.find_preview_path(first_song.path_join(dirs[0]))
	var ogg := KeySoundManager.load_audio_stream(preview)
	check("res:// 안의 미리듣기 ogg: 스트림을 돌려주고 길이가 0보다 큼", ogg != null and ogg.get_length() > 0.0, preview)
	return results
