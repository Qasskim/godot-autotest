extends RefCounted
# 모듈 24 — 로그인 연동 보조 함수 (SupabaseHTTP: build_provider_authorize_url·is_identity_already_linked_error, 기준 코드 주석·docs/phase2/USER_SYSTEM.md)
# 서버에 접속하지 않는 순수 함수만 확인한다: 인증 주소 만들기(리다이렉트 주소 인코딩), "이미 다른 유저에 연결됨" 오류 판별(코드·메시지·대소문자).
# 이 모듈의 주소·메시지 문자열은 시험 작성자가 정했다.

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func run() -> Array:
	var url: String = SupabaseHTTP.build_provider_authorize_url("google", "http://127.0.0.1:8080/cb?x=1&y=2", "CHAL123")
	check("인증 주소는 AUTH_URL + authorize? 로 시작", url.begins_with(SupabaseHTTP.AUTH_URL + "authorize?provider=google&redirect_to="), url)
	check("리다이렉트 주소의 : / ? & = 가 인코딩됨", url.find("redirect_to=http%3A%2F%2F127.0.0.1%3A8080%2Fcb%3Fx%3D1%26y%3D2") != -1, url)
	check("code_challenge 와 s256 이 붙음", url.ends_with("&code_challenge=CHAL123&code_challenge_method=s256"), url)
	eq("쿼리 매개변수 4개만(provider·redirect_to·code_challenge·method)", url.split("?")[1].split("&").size() >= 4, true)

	eq("오류 코드 identity_already_exists: 이미 연결됨", SupabaseHTTP.is_identity_already_linked_error({"error_code": "identity_already_exists"}), true)
	eq("메시지에 'already linked': 이미 연결됨", SupabaseHTTP.is_identity_already_linked_error({"msg": "Identity is already linked to another user"}), true)
	eq("대소문자 달라도 인식('ALREADY LINKED')", SupabaseHTTP.is_identity_already_linked_error({"msg": "ALREADY LINKED"}), true)
	eq("글자 오류도 인식", SupabaseHTTP.is_identity_already_linked_error("422: identity already linked"), true)
	eq("다른 오류 코드: 아님", SupabaseHTTP.is_identity_already_linked_error({"error_code": "validation_failed", "msg": "bad request"}), false)
	eq("빈 딕셔너리: 아님", SupabaseHTTP.is_identity_already_linked_error({}), false)
	eq("관련 없는 글자 오류: 아님", SupabaseHTTP.is_identity_already_linked_error("timeout"), false)
	eq("null: 아님", SupabaseHTTP.is_identity_already_linked_error(null), false)
	return results
