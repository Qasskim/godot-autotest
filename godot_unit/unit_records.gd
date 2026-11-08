extends RefCounted
# 모듈 13 — 로컬 기록 저장(RecordLocalStore·RecordService): 베스트 갱신 규칙, 시퀀스·레인믹스 로그 저장, 곡/난이도/플랫폼/계정별 분리, 최근 플레이, song_id 규칙.
# 게임 코드 그대로 호출한다(user:// 은 실행기가 격리한 APPDATA). 서버는 쓰지 않는다(--no-server → UserService.can_use_server() 거짓 → 로컬 저장만).

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	var store := RecordLocalStore.new()
	store.clear_all_records()


func rec(ex: int, extra: Dictionary = {}) -> Dictionary:
	var r := {"ex_score": ex, "ex_max": 300, "ex_rate": float(ex) / 300.0, "grade": "A"}
	r.merge(extra, true)
	return r


func seq(n: int, judgment: String = "Wow") -> Array:
	var out: Array = []
	for i in n:
		out.append({"note_index": i, "judgment": judgment, "delta_ms": 0})
	return out


func run() -> Array:
	var store := RecordLocalStore.new()
	store.clear_all_records()
	var uid_before: String = SupabaseHTTP.current_user_id

	eq("없는 곡의 베스트는 빈 값", store.load_best("u_song", "EZ", "pc"), {})
	eq("없는 곡의 시퀀스는 빈 배열", store.load_sequence("u_song", "EZ", "pc"), [])
	eq("없는 곡의 레인믹스 로그는 빈 배열", store.load_lanemix_log("u_song", "EZ", "pc"), [])

	# 첫 기록은 점수가 음수여도 저장된다(2026-07-21 버그 수정 항목)
	check("첫 기록은 음수 점수여도 저장되고 true", store.save_if_best("u_song", "EZ", "pc", rec(-5), seq(3, "Miss"), ["base"]) == true)
	eq("저장한 베스트를 읽으면 같은 점수", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 99)), -5)
	eq("저장한 시퀀스 길이", store.load_sequence("u_song", "EZ", "pc").size(), 3)
	eq("저장한 레인믹스 로그", store.load_lanemix_log("u_song", "EZ", "pc"), ["base"])
	check("저장 실패 표시 없음", store.last_save_failed == false and store.last_save_permission_denied == false)

	# 갱신 규칙: 같거나 낮으면 저장 안 함, 더 높으면 저장
	check("낮은 점수는 저장 안 함(false)", store.save_if_best("u_song", "EZ", "pc", rec(-10), seq(3), []) == false)
	eq("낮은 점수 뒤에도 베스트 그대로", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 99)), -5)
	eq("낮은 점수 뒤에도 시퀀스 그대로(첫 판정이 Miss)", store.load_sequence("u_song", "EZ", "pc")[0]["judgment"], "Miss")
	check("같은 점수는 저장 안 함(false)", store.save_if_best("u_song", "EZ", "pc", rec(-5), seq(3), []) == false)
	check("높은 점수는 저장되고 true", store.save_if_best("u_song", "EZ", "pc", rec(120, {"grade": "C"}), seq(4, "Wow"), ["lanemix"]) == true)
	eq("높은 점수로 베스트가 바뀜", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 0)), 120)
	eq("베스트의 등급 필드도 같이 저장", store.load_best("u_song", "EZ", "pc").get("grade", ""), "C")
	eq("시퀀스도 새 것으로 교체(길이 4)", store.load_sequence("u_song", "EZ", "pc").size(), 4)
	eq("레인믹스 로그도 새 것으로 교체", store.load_lanemix_log("u_song", "EZ", "pc"), ["lanemix"])

	# 곡·난이도·플랫폼 분리
	check("다른 난이도는 따로 첫 기록", store.save_if_best("u_song", "NM", "pc", rec(10), seq(1), []) == true)
	check("다른 플랫폼은 따로 첫 기록", store.save_if_best("u_song", "EZ", "android", rec(10), seq(1), []) == true)
	check("다른 곡은 따로 첫 기록", store.save_if_best("u_other", "EZ", "pc", rec(10), seq(1), []) == true)
	eq("원래 곡 베스트는 그대로 120", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 0)), 120)

	# 계정 분리 — 파일 이름에 사용자 ID 가 들어간다(2026-08-31 수정 항목)
	SupabaseHTTP.current_user_id = "unit-user-b"
	eq("다른 계정은 같은 곡의 베스트가 비어 있음", store.load_best("u_song", "EZ", "pc"), {})
	check("다른 계정의 첫 기록은 낮은 점수여도 저장", store.save_if_best("u_song", "EZ", "pc", rec(1), seq(1), []) == true)
	eq("다른 계정 베스트", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 0)), 1)
	SupabaseHTTP.current_user_id = uid_before
	eq("원래 계정 베스트는 영향 없음", int(store.load_best("u_song", "EZ", "pc").get("ex_score", 0)), 120)

	# 최근 플레이
	eq("한 번도 안 친 채보의 최근 플레이는 0", store.get_last_played("res://charts/none.rgds"), 0.0)
	store.record_played("res://charts/a.rgds")
	var first_time := store.get_last_played("res://charts/a.rgds")
	check("플레이 기록 뒤 최근 플레이 시각이 0보다 큼", first_time > 0.0, str(first_time))
	eq("다른 채보는 여전히 0", store.get_last_played("res://charts/b.rgds"), 0.0)
	OS.delay_msec(1100)
	store.record_played("res://charts/b.rgds")
	check("나중에 친 채보의 시각이 더 큼", store.get_last_played("res://charts/b.rgds") > store.get_last_played("res://charts/a.rgds"))
	OS.delay_msec(1100)
	store.record_played("res://charts/a.rgds")
	check("다시 치면 그 채보 시각이 갱신", store.get_last_played("res://charts/a.rgds") > store.get_last_played("res://charts/b.rgds"))

	# 전체 삭제
	store.clear_all_records()
	eq("전체 삭제 뒤 베스트 없음", store.load_best("u_song", "EZ", "pc"), {})
	eq("전체 삭제 뒤 시퀀스 없음", store.load_sequence("u_song", "EZ", "pc"), [])
	eq("전체 삭제 뒤 최근 플레이도 0", store.get_last_played("res://charts/a.rgds"), 0.0)
	check("전체 삭제 뒤 첫 기록 다시 저장", store.save_if_best("u_song", "EZ", "pc", rec(7), seq(1), []) == true)

	# RecordService (서버 없는 상태 = 로컬만)
	var svc = RecordService
	svc.clear_all_records()
	check("서버 없음 상태에서 첫 기록은 저장(true)", svc.save_if_best("svc_song", "HD", "pc", rec(50), seq(2), []) == true)
	check("서버 없음 상태에서 낮은 점수는 false", svc.save_if_best("svc_song", "HD", "pc", rec(40), seq(2), []) == false)
	check("서버 없음 상태에서 높은 점수는 true", svc.save_if_best("svc_song", "HD", "pc", rec(60), seq(2), []) == true)
	eq("RecordService 로 읽은 베스트", int(svc.load_best("svc_song", "HD", "pc").get("ex_score", 0)), 60)
	eq("RecordService 로 읽은 시퀀스 길이", svc.load_sequence("svc_song", "HD", "pc").size(), 2)
	check("서버 업로드 실패 표시 없음(서버를 쓰지 않았으므로)", svc.last_upload_failed == false)
	svc.record_played("res://charts/c.rgds")
	check("RecordService 최근 플레이", svc.get_last_played("res://charts/c.rgds") > 0.0)
	svc.clear_all_records()
	eq("RecordService 전체 삭제", svc.load_best("svc_song", "HD", "pc"), {})

	# song_id 규칙
	eq("공식 채보 song_id 는 폴더 포함·슬래시는 밑줄", RecordService.song_id_from_path("res://charts/keysound/artcore_Gmin_174_006/artcore_Gmin_174_006_EZ_v8.rgds"), "keysound_artcore_Gmin_174_006_artcore_Gmin_174_006_EZ_v8")
	eq("외부 절대경로 song_id 는 파일명만", RecordService.song_id_from_path("C:/Users/x/songs/my_chart.rgds"), "my_chart")
	eq("공식 채보 두 곡의 song_id 는 서로 다름", RecordService.song_id_from_path("res://charts/a/chart_4k_ez.rgds") != RecordService.song_id_from_path("res://charts/b/chart_4k_ez.rgds"), true)

	return results
