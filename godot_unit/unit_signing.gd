extends RefCounted
# 모듈 8 — 공식 채보 서명 검증 (기준: Godot/docs/phase2/PACKAGE_SIGNING_SPEC.md)
# 게임이 쓰는 검증 함수(ChartLoader._verify_signature, RSASSA-PKCS1-v1_5 + SHA-256, 내장 공개키)로
# 수록 곡 폴더의 manifest.json 과 *_v8.rgds 가 각자의 .sig 와 맞는지 확인한다. 읽기 전용(파일을 쓰지 않음).

const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")
const RSA_3072_SIG_BYTES := 384   # 스펙 §2-1 RSA-3072

var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func _read_sig(path: String) -> String:
	return FileAccess.get_file_as_string(path).strip_edges()


func run() -> Array:
	var key = ChartLoader._get_public_key()
	check("서명: 내장 공개키가 파싱됨(공개키 전용)", key != null and key.is_public_only())

	var songs_root := "res://charts/keysound"
	var songs: Array = []
	for d in DirAccess.get_directories_at(songs_root):
		songs.append(songs_root + "/" + d)
	songs.sort()
	check("서명: 검사할 수록 곡 폴더가 있음(%d곡)" % songs.size(), songs.size() > 0)

	# 음성 대조 — 검증 함수가 아무거나 통과시키지 않는지
	var sample_dir: String = songs[0]
	var sample_manifest := FileAccess.get_file_as_bytes(sample_dir + "/manifest.json")
	var sample_sig := _read_sig(sample_dir + "/manifest.json.sig")
	check("서명(음성 대조): 올바른 manifest 서명은 통과", ChartLoader._verify_signature(sample_manifest, sample_sig))
	var tampered := sample_manifest.duplicate()
	tampered[0] = (tampered[0] + 1) % 256
	check("서명(음성 대조): 내용을 1바이트 바꾸면 거부", not ChartLoader._verify_signature(tampered, sample_sig))
	check("서명(음성 대조): 빈 서명은 거부", not ChartLoader._verify_signature(sample_manifest, ""))
	check("서명(음성 대조): base64가 아닌 서명은 거부", not ChartLoader._verify_signature(sample_manifest, "이것은 서명이 아닙니다!!"))
	var other_chart := FileAccess.get_file_as_bytes(sample_dir + "/" + _first_chart_name(sample_dir))
	check("서명(음성 대조): 다른 파일의 서명(manifest 서명으로 채보 검증)은 거부", not ChartLoader._verify_signature(other_chart, sample_sig))

	var bad_manifest: Array = []
	var bad_chart: Array = []
	var bad_len: Array = []
	var chart_count := 0
	for song in songs:
		var sname: String = song.get_file()
		var msig := _read_sig(song + "/manifest.json.sig")
		if Marshalls.base64_to_raw(msig).size() != RSA_3072_SIG_BYTES:
			bad_len.append(sname + "/manifest")
		if not ChartLoader._verify_signature(FileAccess.get_file_as_bytes(song + "/manifest.json"), msig):
			bad_manifest.append(sname)
		for f in DirAccess.get_files_at(song):
			if not f.ends_with("_v8.rgds"):
				continue
			chart_count += 1
			var sig_path: String = song + "/" + f + ".sig"
			if not FileAccess.file_exists(sig_path):
				bad_chart.append(f + " (서명 파일 없음)")
				continue
			var csig := _read_sig(sig_path)
			if Marshalls.base64_to_raw(csig).size() != RSA_3072_SIG_BYTES:
				bad_len.append(f)
			if not ChartLoader._verify_signature(FileAccess.get_file_as_bytes(song + "/" + f), csig):
				bad_chart.append(f)
	check("서명: 수록 곡의 manifest.json 서명이 모두 유효 (%d곡)" % songs.size(), bad_manifest.is_empty(),
		"%d곡 불일치: %s" % [bad_manifest.size(), ", ".join(bad_manifest.slice(0, 4))])
	check("서명: 수록 난이도 채보의 서명이 모두 유효 (%d채보 — 서명 이후 채보가 바뀌었으면 여기서 어긋남)" % chart_count, bad_chart.is_empty(),
		"%d건 불일치: %s" % [bad_chart.size(), ", ".join(bad_chart.slice(0, 4))])
	check("서명: 서명 길이는 RSA-3072의 384바이트 (PACKAGE_SIGNING_SPEC §2-1)", bad_len.is_empty(), "%d건: %s" % [bad_len.size(), ", ".join(bad_len.slice(0, 3))])
	return results


func _first_chart_name(song: String) -> String:
	for f in DirAccess.get_files_at(song):
		if f.ends_with("_v8.rgds"):
			return f
	return ""
