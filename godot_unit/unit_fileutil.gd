extends RefCounted
# 모듈 17 — 원자적 파일 저장 (FileUtil.write_atomic, 기준: FileUtil 설명 — 임시파일 path+".tmp"에 먼저 쓰고 끝나면 rename, 저장 도중 강제 종료돼도 파일이 반쯤 쓰인 채 깨지지 않음)
# 확인하는 것: 새 파일 만들기 / 덮어쓰기 / 한글·빈 글자 / 끝난 뒤 .tmp 가 남지 않음 / 실패하면 오류 코드를 돌려주고 기존 파일 내용이 그대로 남음
# (실패 만들기: 임시파일 자리에 폴더를 두거나, 없는 폴더에 쓰기). 서버는 쓰지 않는다. 이 모듈의 글자 내용은 시험 작성자가 정했다.

const FileUtil := preload("res://scripts/core/FileUtil.gd")

var needs_frames := true
var results: Array = []
var dir_user := "user://unit_fileutil_test"


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	_wipe(ProjectSettings.globalize_path(dir_user))


func _wipe(abs_dir: String) -> void:
	var d := DirAccess.open(abs_dir)
	if d == null:
		return
	for sub in d.get_directories():
		_wipe(abs_dir.path_join(sub))
	for f in d.get_files():
		DirAccess.remove_absolute(abs_dir.path_join(f))
	DirAccess.remove_absolute(abs_dir)


func read(path: String) -> String:
	var f := FileAccess.open(path, FileAccess.READ)
	return f.get_as_text() if f != null else "<<없음>>"


func run() -> Array:
	cleanup()
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(dir_user))
	var p := dir_user + "/data.json"

	eq("새 파일: OK 를 돌려주고 내용이 그대로 저장됨", [FileUtil.write_atomic(p, '{"a": 1}'), read(p)], [OK, '{"a": 1}'])
	eq("끝난 뒤 임시파일(.tmp)이 남지 않음", FileAccess.file_exists(p + ".tmp"), false)
	eq("덮어쓰기: 새 내용으로 완전히 바뀜(옛 내용이 섞이지 않음)", [FileUtil.write_atomic(p, "짧게"), read(p)], [OK, "짧게"])
	eq("한글: 저장하고 읽으면 같은 글자", [FileUtil.write_atomic(p, "한글 닉네임 ✓"), read(p)], [OK, "한글 닉네임 ✓"])
	eq("빈 글자: 빈 파일이 만들어짐", [FileUtil.write_atomic(p, ""), FileAccess.file_exists(p), read(p)], [OK, true, ""])
	var big := "x".repeat(200000)
	eq("큰 내용(20만 글자): 잘리지 않고 저장됨", [FileUtil.write_atomic(p, big), read(p).length()], [OK, 200000])

	# ── 실패: 임시파일 자리에 폴더가 있으면 열 수 없다 → 오류 코드, 기존 파일은 그대로 ──
	FileUtil.write_atomic(p, "지켜야 하는 내용")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(p + ".tmp"))
	var err_blocked := FileUtil.write_atomic(p, "덮어쓰면 안 됨")
	check("임시파일을 열 수 없을 때: 오류 코드를 돌려줌", err_blocked != OK, "err=%s" % error_string(err_blocked))
	eq("임시파일을 열 수 없을 때: 기존 파일 내용이 그대로 남음", read(p), "지켜야 하는 내용")
	DirAccess.remove_absolute(ProjectSettings.globalize_path(p + ".tmp"))

	# ── 실패: 없는 폴더에 쓰기 ──
	var missing := dir_user + "/없는폴더/data.json"
	var err_missing := FileUtil.write_atomic(missing, "x")
	check("없는 폴더에 쓰기: 오류 코드를 돌려줌", err_missing != OK, "err=%s" % error_string(err_missing))
	eq("없는 폴더에 쓰기: 파일이 만들어지지 않음", [FileAccess.file_exists(missing), FileAccess.file_exists(missing + ".tmp")], [false, false])

	# ── 정상으로 돌아오기 ──
	eq("실패 뒤에도 다시 저장하면 정상", [FileUtil.write_atomic(p, "복구"), read(p)], [OK, "복구"])
	return results
