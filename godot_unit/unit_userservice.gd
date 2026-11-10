extends RefCounted
# 모듈 26 — 유저 프로필·닉네임 (UserService: 닉네임 검증·표시폭, 게스트 로컬 저장, 프로필 저장/복원, 게스트의 로그아웃·탈퇴 — 기준 docs/phase2/USER_SYSTEM.md §4-1 "한글 최대 16자 / 영문 최대 32자", 코드 주석)
#   - 표시폭: 한글(가-힣) 2, 그 외 1, 최대 32 → 한글 16자 / 영문 32자 / 섞어서 폭 합 32 까지
#   - 허용 글자: 한글·영문·숫자·공백·_ - ♥♡★☆♪♫·~ 만, 그 밖(@ ! 이모지 등)은 "chars", 비었거나 폭 초과는 "length"
#   - 게스트(서버 못 쓰는 상태): 닉네임을 로컬에 저장하고 true, 검증 실패는 false 와 원인 코드, 저장은 profile.json 에 남아 다시 읽으면 복원
#   - 온보딩·튜토리얼·프로토 안내 표시 저장
#   - 게스트의 로그아웃은 아무 일 없음, 탈퇴는 false (지울 실계정이 없음)
# 시험이 끝나면 원래 프로필로 되돌린다. 서버는 쓰지 않는다(--no-server → 서버를 쓸 수 없는 상태). 시험 닉네임 글자는 시험 작성자가 정했다.

var needs_frames := true
var results: Array = []
var _backup: Dictionary = {}


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	UserService._profile = _backup
	UserService._save_profile()
	UserService.last_nickname_error = ""


func try_name(name: String) -> Array:
	var ok: bool = await UserService.set_nickname(name)
	return [ok, UserService.last_nickname_error]


func run() -> Array:
	_backup = UserService._profile.duplicate(true)
	UserService._profile = {}
	eq("서버를 쓸 수 없는 상태(--no-server)에서 게스트로 시험", [UserService.can_use_server(), SupabaseHTTP.is_anonymous], [false, true])

	# ── 표시폭 ──
	eq("표시폭: 한글 2·영문/숫자/기호 1", [UserService._name_width("가"), UserService._name_width("a"), UserService._name_width("가a1_")], [2, 1, 5])

	# ── 검증 ──
	eq("빈 이름: 길이 오류", await try_name(""), [false, "length"])
	eq("한글 16자(폭 32): 통과", (await try_name("가".repeat(16)))[0], true)
	eq("한글 17자(폭 34): 길이 오류", await try_name("가".repeat(17)), [false, "length"])
	eq("영문 32자(폭 32): 통과", (await try_name("a".repeat(32)))[0], true)
	eq("영문 33자(폭 33): 길이 오류", await try_name("a".repeat(33)), [false, "length"])
	eq("섞어서 폭 32(한글 15자 + 영문 2자): 통과", (await try_name("가".repeat(15) + "ab"))[0], true)
	eq("섞어서 폭 33(한글 15자 + 영문 3자): 길이 오류", await try_name("가".repeat(15) + "abc"), [false, "length"])
	eq("허용 기호(공백 _ - ♥♡★☆♪♫·~): 통과", (await try_name("Nick _-♥♡★☆♪♫·~ 1"))[0], true)
	for bad in ["a@b", "물음표?", "a!b", "😀", "a/b", "a.b", "탭\t이름"]:
		eq("허용 밖 글자 '%s': 글자 오류" % bad.replace("\t", "\\t"), await try_name(bad), [false, "chars"])

	# ── 저장 ──
	UserService._profile = {}
	eq("검증 실패 때는 프로필이 바뀌지 않음", [(await try_name("a@b"))[0], UserService.has_nickname()], [false, false])
	eq("게스트 로컬 저장: true, 닉네임이 프로필에 들어감", [(await try_name("테스터"))[0], UserService.get_display_name(), UserService.has_nickname()], [true, "테스터", true])
	check("저장 시각(updated_at)이 기록됨", str(UserService.get_profile().get("updated_at", "")) != "")
	eq("게스트는 서버 등록 표시(nickname_server_uid) 없이도 닉네임 준비 완료", UserService.nickname_ready(), true)
	UserService._profile = {}
	UserService._profile = UserService._load_profile()
	eq("파일에서 다시 읽으면 닉네임이 복원됨", UserService.get_display_name(), "테스터")

	# ── 표시 저장 ──
	UserService._profile = {}
	eq("처음에는 온보딩·튜토리얼·프로토 안내 모두 아직", [UserService.has_completed_onboarding(), UserService.has_seen_tutorial(), UserService.has_ack_proto_notice()], [false, false, false])
	UserService.mark_onboarding_done()
	UserService.mark_tutorial_seen()
	UserService.mark_proto_notice_ack()
	UserService._profile = UserService._load_profile()
	eq("표시를 남기면 다시 읽어도 유지", [UserService.has_completed_onboarding(), UserService.has_seen_tutorial(), UserService.has_ack_proto_notice()], [true, true, true])

	# ── 게스트의 로그아웃·탈퇴 ──
	var before := UserService._profile.duplicate(true)
	await UserService.logout()
	eq("게스트 로그아웃: 프로필이 그대로", UserService._profile, before)
	eq("게스트 탈퇴: false (지울 실계정이 없음)", await UserService.delete_account(), false)
	eq("게스트 탈퇴 뒤에도 프로필이 그대로", UserService._profile, before)
	return results
