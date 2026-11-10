extends RefCounted
# 모듈 20 — 채보 불러오기 보조 함수 (ChartLoader: load_meta_only·read_manifest·곡 폴더 파일 찾기·접근자, 기준 DESIGN §4 "곡 선택 목록 읽기"·§8 곡 폴더 구조)
#   - load_meta_only(곡 선택 목록이 쓰는 앞부분만 읽기)가 채보 전체를 읽은 meta 와 수록 채보 전부에서 똑같다(DESIGN §4: 117개 채보 차이 0)
#   - 특이한 파일(meta 가 맨 앞이 아님, BOM, meta 안의 중괄호·따옴표 글자, 파일 없음)에서도 같은 결과
#   - 곡 폴더 찾기: 수록곡마다 자켓·풀믹스·미리듣기가 실제로 찾아지고, 없는 폴더는 빈 문자열
#   - manifest 읽기: 수록곡마다 song_uid 가 있고, 없거나 깨진 manifest 는 기본값
#   - 접근자 기본값: 빈 채보에서 bpm 120·키 수 4 등
# 서버는 쓰지 않는다. 이 모듈의 가짜 채보 내용은 시험 작성자가 정했다.

const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")

var needs_frames := true
var results: Array = []
var tmp := "user://unit_chartloader_test"


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	_wipe(ProjectSettings.globalize_path(tmp))


func _wipe(abs_dir: String) -> void:
	var d := DirAccess.open(abs_dir)
	if d == null:
		return
	for sub in d.get_directories():
		_wipe(abs_dir.path_join(sub))
	for f in d.get_files():
		DirAccess.remove_absolute(abs_dir.path_join(f))
	DirAccess.remove_absolute(abs_dir)


func write(path: String, text: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)
	f.close()


func chart_files() -> Array:
	var out: Array = []
	for base in ["res://charts/Tutorial", "res://charts/keysound"]:
		var d := DirAccess.open(base)
		if d == null:
			continue
		for f in d.get_files():
			if f.ends_with(".rgds"):
				out.append(base.path_join(f))
		for sub in d.get_directories():
			var d2 := DirAccess.open(base.path_join(sub))
			for f in d2.get_files():
				if f.ends_with(".rgds"):
					out.append(base.path_join(sub).path_join(f))
	out.sort()
	return out


func song_dirs() -> Array:
	var out: Array = []
	var d := DirAccess.open("res://charts/keysound")
	for sub in d.get_directories():
		out.append("res://charts/keysound".path_join(sub))
	out.sort()
	return out


func run() -> Array:
	cleanup()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(tmp))

	# ── meta 만 읽기 = 전체 읽기의 meta (수록 채보 전부) ──
	var files := chart_files()
	check("수록·튜토리얼 채보를 찾음(70개 이상)", files.size() >= 70, "개수 %d" % files.size())
	var diffs: Array = []
	for f in files:
		var a := ChartLoader.load_meta_only(f)
		var b := ChartLoader.read_meta(ChartLoader.load_file(f))
		if a != b or a.is_empty():
			diffs.append(f.get_file())
	check("load_meta_only 와 전체 읽기의 meta 가 채보 %d개 전부에서 같음" % files.size(), diffs.is_empty(), "다른 채보 %d개 %s" % [diffs.size(), str(diffs.slice(0, 4))])
	eq("없는 파일: 빈 딕셔너리", ChartLoader.load_meta_only("res://charts/없는채보.rgds"), {})

	# ── 특이한 파일 ──
	var body := '"sounds": [], "score": [], "gimmick_events": []'
	var meta := '{"title": "a{b}\\"c}", "bpm": 150.5, "keymode": 6, "inner": {"x": [1, 2, {"y": "}"}]}}'
	write(tmp + "/meta_first.rgds", '{\n"meta": %s,\n%s\n}' % [meta, body])
	write(tmp + "/meta_later.rgds", '{\n%s,\n"meta": %s\n}' % [body, meta])
	write(tmp + "/bom.rgds", "﻿" + '{\n"meta": %s,\n%s\n}' % [meta, body])
	write(tmp + "/oneline.rgds", '{"meta": %s, %s}' % [meta, body])
	for n in ["meta_first", "meta_later", "bom", "oneline"]:
		var p := tmp + "/%s.rgds" % n
		var full := ChartLoader.read_meta(ChartLoader.load_file(p))
		var quick := ChartLoader.load_meta_only(p)
		check("특이한 파일(%s): meta 만 읽기가 전체 읽기와 같음" % n, quick == full and not quick.is_empty(), "meta만 %s / 전체 %s" % [str(quick).left(60), str(full).left(60)])
	eq("글자 안의 중괄호·따옴표가 meta 를 끊지 않음", ChartLoader.load_meta_only(tmp + "/meta_first.rgds").get("title", ""), 'a{b}"c}')

	# ── 곡 폴더 찾기 ──
	var dirs := song_dirs()
	check("수록곡 폴더를 찾음(17개)", dirs.size() == 17, "개수 %d" % dirs.size())
	var bad_jacket: Array = []
	var bad_mix: Array = []
	var bad_prev: Array = []
	var bad_manifest: Array = []
	for d in dirs:
		var j := ChartLoader.find_jacket_path(d)
		if j == "" or not ResourceLoader.exists(j):
			bad_jacket.append(d.get_file())
		var m := ChartLoader.find_full_mix_path(d)
		if m == "" or not ResourceLoader.exists(m):
			bad_mix.append(d.get_file())
		var p := ChartLoader.find_preview_path(d)
		if p == "" or not ResourceLoader.exists(p):
			bad_prev.append(d.get_file())
		var chart_in := ""
		var dd := DirAccess.open(d)
		for f in dd.get_files():
			if f.ends_with(".rgds"):
				chart_in = d.path_join(f)
				break
		var man := ChartLoader.read_manifest(chart_in)
		if str(man.get("song_uid", "")) == "":
			bad_manifest.append(d.get_file())
	check("자켓이 찾아짐(곡 17개 전부)", bad_jacket.is_empty(), str(bad_jacket))
	check("풀믹스가 찾아짐(곡 17개 전부)", bad_mix.is_empty(), str(bad_mix))
	check("미리듣기가 찾아짐(곡 17개 전부)", bad_prev.is_empty(), str(bad_prev))
	check("manifest 에 song_uid 가 있음(곡 17개 전부)", bad_manifest.is_empty(), str(bad_manifest))
	eq("없는 폴더: 자켓·풀믹스·미리듣기는 빈 문자열", [ChartLoader.find_jacket_path("res://charts/없는곡"), ChartLoader.find_full_mix_path("res://charts/없는곡"), ChartLoader.find_preview_path("res://charts/없는곡")], ["", "", ""])
	var default_manifest := {"song_uid": "", "pack_id": "base", "sellable_individually": false}
	eq("manifest 가 없으면 기본값", ChartLoader.read_manifest(tmp + "/meta_first.rgds"), default_manifest)
	write(tmp + "/manifest.json", "{깨진")
	eq("manifest 가 깨져 있으면 기본값", ChartLoader.read_manifest(tmp + "/meta_first.rgds"), default_manifest)
	write(tmp + "/manifest.json", '{"song_uid": "uid-1", "pack_id": "pack-x", "sellable_individually": true}')
	var man2 := ChartLoader.read_manifest(tmp + "/meta_first.rgds")
	eq("manifest 값을 그대로 읽음", [man2.get("song_uid"), man2.get("pack_id"), man2.get("sellable_individually")], ["uid-1", "pack-x", true])

	# ── 접근자 기본값 ──
	var empty := {}
	eq("빈 채보: meta·sounds·timing·gimmick·score 는 빈 값", [ChartLoader.read_meta(empty), ChartLoader.get_sounds(empty), ChartLoader.get_timing_events(empty), ChartLoader.get_gimmick_events(empty), ChartLoader.get_score(empty)], [{}, [], [], [], []])
	eq("빈 채보: bpm 120·키 수 4", [ChartLoader.get_bpm(empty), ChartLoader.get_key_mode(empty)], [120.0, 4])
	eq("값이 있으면 그대로", [ChartLoader.get_bpm({"meta": {"bpm": 93.5}}), ChartLoader.get_key_mode({"meta": {"keymode": 8}})], [93.5, 8])
	eq("파일 없음·필수 필드 없음은 빈 딕셔너리", [ChartLoader.load_file("res://charts/없는채보.rgds"), ChartLoader.load_file(tmp + "/manifest.json")], [{}, {}])
	return results
