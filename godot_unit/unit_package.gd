extends RefCounted
# 모듈 15 — 곡 패키지(.rgz) 풀기·병합·서명 잠금 (기준: ChartLoader.ensure_rgz_extracted 설명, docs/phase2/PACKAGE_SIGNING_SPEC.md, DESIGN §8 배포 패키지)
# 시험 환경: user:// 아래 시험 폴더에 ZIPPacker 로 .rgz 를 만들어 게임 함수를 그대로 부른다(진짜 공식 서명은 수록곡 폴더의 .sig 를 그대로 가져와 공개키로 검증).
# 규칙(함수 설명): 대상 폴더는 manifest.json 의 song_uid(없으면 zip 이름) / 경로 조작 엔트리가 하나라도 있으면 전체 거부 / 병합 시 manifest 는 기존 유지,
# 음원은 있으면 스킵, 같은 이름의 .rgds 는 내용이 같으면 스킵·다르면 chart_uid 새 이름으로 둘 다 보존 / 유효 서명 패키지가 처음 만든 폴더는 공식 잠금,
# 잠긴 폴더에 서명 없는 패키지는 거부하고 _rejected 로 격리 / 다 쓴 .rgz 는 삭제.
# 이 모듈의 파일 내용(가짜 채보·가짜 음원 바이트)은 시험 작성자가 정했다. 서버는 쓰지 않는다.

const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")

var needs_frames := true
var results: Array = []
var root := ""


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	if root != "":
		ChartLoader._delete_dir_recursive(root)


func chart_json(uid: String, extra: String = "") -> PackedByteArray:
	return ('{"meta": {"chart_uid": "%s", "keymode": 4, "bpm": 120.0%s}, "sounds": [], "score": []}' % [uid, extra]).to_utf8_buffer()


func manifest_json(song_uid: String, tag: String = "") -> PackedByteArray:
	return ('{"song_uid": "%s", "pack_id": "%s"}' % [song_uid, tag]).to_utf8_buffer()


func make_zip(name: String, entries: Dictionary) -> String:
	var path := root.path_join(name)
	var zp := ZIPPacker.new()
	var err := zp.open(path)
	if err != OK:
		check("시험 준비: zip 만들기 (%s)" % name, false, "ZIPPacker.open 오류 %d" % err)
		return path
	for entry_name in entries:
		zp.start_file(entry_name)
		zp.write_file(entries[entry_name])
		zp.close_file()
	zp.close()
	return path


func read_text(path: String) -> String:
	return FileAccess.get_file_as_bytes(path).get_string_from_utf8()


func files_in(dir_path: String) -> Array:
	var out: Array = []
	var d := DirAccess.open(dir_path)
	if d == null:
		return out
	for f in d.get_files():
		out.append(f)
	out.sort()
	return out


func run() -> Array:
	root = ProjectSettings.globalize_path("user://unit_package_test")
	cleanup()
	DirAccess.make_dir_recursive_absolute(root)

	# ── 열 수 없는 파일 ──
	var bad := root.path_join("bad.rgz")
	var f := FileAccess.open(bad, FileAccess.WRITE)
	f.store_string("zip 이 아닌 글자")
	f.close()
	var prog := {}
	eq("zip 이 아닌 파일: 빈 문자열을 돌려주고 진행 표시는 끝남", [ChartLoader.ensure_rgz_extracted(bad, prog), prog.get("done")], ["", true])

	# ── 경로 조작(Zip Slip) 엔트리 하나라도 있으면 전체 거부 ──
	var slip_cases := {"slip_dotdot.rgz": "../evil.txt", "slip_abs.rgz": "/abs_evil.txt", "slip_drive.rgz": "C:evil.txt", "slip_inner.rgz": "sub/../evil.txt"}
	for zname in slip_cases:
		var zp := make_zip(zname, {"manifest.json": manifest_json("slipuid"), "a.rgds": chart_json("c1"), slip_cases[zname]: "x".to_utf8_buffer()})
		var got := ChartLoader.ensure_rgz_extracted(zp)
		eq("경로 조작 엔트리(%s): 전체 거부" % slip_cases[zname], got, "")
		check("경로 조작 엔트리(%s): 아무것도 풀리지 않고 원본 zip 은 그대로" % slip_cases[zname],
			not DirAccess.dir_exists_absolute(root.path_join("slipuid")) and not FileAccess.file_exists(root.path_join("evil.txt")) and FileAccess.file_exists(zp))

	# ── 정상 패키지: song_uid 폴더로 풀림 ──
	var zp_a := make_zip("pack_a.rgz", {"manifest.json": manifest_json("uidA", "first"), "a.rgds": chart_json("cA"), "audio.wav": PackedByteArray([1, 2, 3, 4])})
	var prog_a := {}
	var dir_a := ChartLoader.ensure_rgz_extracted(zp_a, prog_a)
	eq("정상 패키지: 대상 폴더는 zip 이름이 아니라 manifest song_uid", dir_a, root.path_join("uidA"))
	eq("정상 패키지: 파일 3개가 풀림", files_in(dir_a), ["a.rgds", "audio.wav", "manifest.json"])
	eq("정상 패키지: 다 쓴 원본 zip 은 삭제됨", FileAccess.file_exists(zp_a), false)
	eq("정상 패키지: 진행 표시 total=current=3, done", [prog_a.get("total"), prog_a.get("current"), prog_a.get("done")], [3, 3, true])
	eq("서명 없는 패키지: 공식 잠금 표시가 생기지 않음", FileAccess.file_exists(dir_a.path_join(ChartLoader.OFFICIAL_LOCK_MARKER)), false)

	# ── 병합: 같은 song_uid 의 두 번째 패키지 ──
	var zp_b := make_zip("pack_b.rgz", {
		"manifest.json": manifest_json("uidA", "second"),               # 기존 manifest 가 유지돼야 함
		"audio.wav": PackedByteArray([9, 9, 9, 9]),                     # 음원은 있으면 스킵(원래 1,2,3,4 유지)
		"a.rgds": chart_json("cA"),                                     # 내용이 완전히 같음 → 중복으로 스킵
		"b.rgds": chart_json("cB"),                                     # 새 채보 → 추가
		"extra.wav": PackedByteArray([7]),                              # 새 음원 → 추가
	})
	var dir_b := ChartLoader.ensure_rgz_extracted(zp_b)
	eq("병합: 같은 폴더를 돌려줌", dir_b, dir_a)
	eq("병합: 새 채보·새 음원이 추가되고 같은 내용 채보는 늘지 않음", files_in(dir_a), ["a.rgds", "audio.wav", "b.rgds", "extra.wav", "manifest.json"])
	check("병합: manifest 는 기존(first) 유지", read_text(dir_a.path_join("manifest.json")).find("first") >= 0)
	eq("병합: 이미 있던 음원은 덮어쓰지 않음", Array(FileAccess.get_file_as_bytes(dir_a.path_join("audio.wav"))), [1, 2, 3, 4])
	eq("병합: 원본 zip 삭제", FileAccess.file_exists(zp_b), false)

	# ── 같은 이름·다른 내용 채보: chart_uid 이름으로 둘 다 보존 ──
	var zp_c := make_zip("pack_c.rgz", {"manifest.json": manifest_json("uidA"), "a.rgds": chart_json("cA2", ', "title": "다른 내용"')})
	ChartLoader.ensure_rgz_extracted(zp_c)
	eq("같은 이름·다른 내용 채보: chart_uid 이름(cA2.rgds)으로 따로 보존", files_in(dir_a).has("cA2.rgds") and files_in(dir_a).has("a.rgds"), true)
	check("같은 이름·다른 내용 채보: 원래 a.rgds 내용은 그대로", read_text(dir_a.path_join("a.rgds")).find("cA2") < 0)

	# ── song_uid 가 없거나 위험하면 zip 이름 폴더 ──
	var zp_d := make_zip("legacy_one.rgz", {"manifest.json": manifest_json("../escape"), "a.rgds": chart_json("cD")})
	var dir_d := ChartLoader.ensure_rgz_extracted(zp_d)
	eq("위험한 song_uid(../): 무시하고 zip 이름 폴더로 풀림", dir_d, root.path_join("legacy_one"))
	check("위험한 song_uid: 바깥 폴더(escape)가 생기지 않음", not DirAccess.dir_exists_absolute(root.get_base_dir().path_join("escape")))
	var zp_e := make_zip("legacy_two.rgz", {"a.rgds": chart_json("cE")})
	var dir_e := ChartLoader.ensure_rgz_extracted(zp_e)
	eq("manifest 없는 구버전 패키지: zip 이름 폴더로 풀림", dir_e, root.path_join("legacy_two"))
	var zp_e2 := make_zip("legacy_two.rgz", {"a.rgds": chart_json("cE_other")})
	var dir_e2 := ChartLoader.ensure_rgz_extracted(zp_e2)
	eq("구버전 패키지가 이미 풀려 있으면 다시 풀지 않고 그 폴더를 돌려줌", [dir_e2, read_text(dir_e.path_join("a.rgds")).find("cE_other") < 0], [dir_e, true])

	# ── 공식 서명: 수록곡의 진짜 서명 파일을 가져와 공개키로 검증 ──
	var src := _find_signed_song_dir()
	if src == "":
		check("공식 서명 시험 준비: 서명된 수록곡 폴더를 찾음", false, "res://charts/keysound 아래에 manifest.json.sig 가 든 폴더가 없음")
	else:
		var rgds := _first_rgds(src)
		var signed := {
			"manifest.json": FileAccess.get_file_as_bytes(src.path_join("manifest.json")),
			"manifest.json.sig": FileAccess.get_file_as_bytes(src.path_join("manifest.json.sig")),
			rgds: FileAccess.get_file_as_bytes(src.path_join(rgds)),
			rgds + ".sig": FileAccess.get_file_as_bytes(src.path_join(rgds + ".sig")),
		}
		var uid := str(JSON.parse_string(signed["manifest.json"].get_string_from_utf8()).get("song_uid", ""))
		check("공식 서명 시험 준비: 수록곡 manifest 에 안전한 song_uid 가 있음", uid != "" and uid.find("/") < 0 and uid.find("..") < 0, "uid=%s" % uid)
		var zp_s := make_zip("signed.rgz", signed)
		var dir_s := ChartLoader.ensure_rgz_extracted(zp_s)
		eq("서명된 공식 패키지: song_uid 폴더로 풀림", dir_s, root.path_join(uid))
		eq("서명된 공식 패키지: 처음 만든 폴더에 공식 잠금 표시가 생김", FileAccess.file_exists(dir_s.path_join(ChartLoader.OFFICIAL_LOCK_MARKER)), true)
		var before := files_in(dir_s)
		var zp_u := make_zip("unsigned_into_locked.rgz", {"manifest.json": manifest_json(uid), "intruder.rgds": chart_json("evil")})
		var got_u := ChartLoader.ensure_rgz_extracted(zp_u)
		eq("공식 잠금 폴더에 서명 없는 패키지: 거부", got_u, "")
		eq("거부된 패키지: 폴더가 바뀌지 않음", files_in(dir_s), before)
		check("거부된 패키지: 원본 zip 이 _rejected 로 격리됨", not FileAccess.file_exists(zp_u) and FileAccess.file_exists(root.path_join("_rejected").path_join("unsigned_into_locked.rgz")))
		# 서명된 채보를 한 바이트 바꾸면 서명이 안 맞아 공식이 되지 못함(풀리긴 하지만 잠금 표시 없음)
		var tampered := signed.duplicate()
		var bytes: PackedByteArray = tampered[rgds].duplicate()
		bytes[bytes.size() / 2] = (bytes[bytes.size() / 2] + 1) % 256
		tampered[rgds] = bytes
		tampered["manifest.json"] = FileAccess.get_file_as_bytes(src.path_join("manifest.json")).get_string_from_utf8().replace(uid, uid + "_t").to_utf8_buffer()
		var zp_t := make_zip("tampered.rgz", tampered)
		var dir_t := ChartLoader.ensure_rgz_extracted(zp_t)
		eq("변조된 패키지: 풀리지만 공식 잠금 표시는 없음", [dir_t != "", FileAccess.file_exists(dir_t.path_join(ChartLoader.OFFICIAL_LOCK_MARKER))], [true, false])
	return results


func _find_signed_song_dir() -> String:
	var base := "res://charts/keysound"
	var d := DirAccess.open(base)
	if d == null:
		return ""
	var names := Array(d.get_directories())
	names.sort()
	for n in names:
		var p: String = base.path_join(n)
		if FileAccess.file_exists(p.path_join("manifest.json")) and FileAccess.file_exists(p.path_join("manifest.json.sig")) and _first_rgds(p) != "":
			return p
	return ""


func _first_rgds(dir_path: String) -> String:
	var d := DirAccess.open(dir_path)
	if d == null:
		return ""
	var names := Array(d.get_files())
	names.sort()
	for n in names:
		if str(n).ends_with(".rgds") and FileAccess.file_exists(dir_path.path_join(str(n) + ".sig")):
			return str(n)
	return ""
