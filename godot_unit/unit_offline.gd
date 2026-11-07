extends RefCounted
# 모듈 5 — 서버 접속 차단 가드 (--no-server)
# 프레임을 실제로 돌려(오토로드 _ready가 실행되는 상태) 서버에 붙지 않았는지 확인한다.
# 2026-11-08 사고: 모듈이 오류로 멈춰 프레임이 돌았는데 --no-server가 없어서 개발 서버에 익명 계정이 생겼다.
# 이 모듈은 반드시 --no-server와 함께 실행한다(godot_runner.run_unit_module이 항상 붙임).

var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func cleanup() -> void:
	pass


func run() -> Array:
	var tree := Engine.get_main_loop() as SceneTree
	check("가드: --no-server 인자가 인식됨(이 모듈은 반드시 이 인자와 함께 실행)", SupabaseHTTP.is_no_server(), "인자가 없으면 아래 검사를 하지 않고 중단한다")
	if not SupabaseHTTP.is_no_server():
		return results   # 인자가 없는데 프레임을 돌리면 서버에 접속하므로 여기서 멈춘다
	var mtime_before := FileAccess.get_modified_time("user://supabase_session.json") if FileAccess.file_exists("user://supabase_session.json") else 0
	for i in 5:
		await tree.process_frame   # 오토로드 _ready(ensure_session, RemoteConfig 조회)가 실행된다
	check("가드: 프레임이 돈 뒤에도 서버 세션이 없음(session_ready false, 사용자 ID 비어 있음)",
		not SupabaseHTTP.session_ready and SupabaseHTTP.current_user_id == "", "session_ready=%s id=%s" % [str(SupabaseHTTP.session_ready), SupabaseHTTP.current_user_id])
	check("가드: ensure_session이 저장된 세션을 읽거나 갱신하려 하지 않음(토큰 비어 있음)", SupabaseHTTP._access_token == "" and SupabaseHTTP._refresh_token == "")
	check("가드: 차단 사유가 기록됨(last_auth_error = no-server)", SupabaseHTTP.last_auth_error == "no-server", "실제 %s" % SupabaseHTTP.last_auth_error)
	var mtime_after := FileAccess.get_modified_time("user://supabase_session.json") if FileAccess.file_exists("user://supabase_session.json") else 0
	check("가드: 세션 파일이 새로 만들어지거나 수정되지 않음", mtime_before == mtime_after, "전 %d / 후 %d" % [mtime_before, mtime_after])
	check("가드: 원격 설정을 조회하지 않음(전부 OFF 유지)", not RemoteConfig._loaded and not RemoteConfig.is_enabled("any_flag"))
	var r: Array = await SupabaseHTTP.get_rows("app_config", "select=key")
	check("가드: 서버 조회(get_rows)가 차단 메시지로 실패함", r.size() == 2 and r[0] == false and "--no-server" in str(r[1]), str(r))
	var s: Array = await SupabaseHTTP.insert_row("records", {"x": 1})
	check("가드: 서버 쓰기(insert_row)도 차단 메시지로 실패함", s.size() == 2 and s[0] == false and "--no-server" in str(s[1]), str(s))
	return results
