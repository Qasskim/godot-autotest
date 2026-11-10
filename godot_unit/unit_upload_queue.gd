extends RefCounted
# 모듈 14 — 오프라인 업로드 큐 (RecordSupabaseSync.enqueue / process_queue, 기준 docs/phase2/SUPABASE_ADAPTER_SPEC.md, 코드 주석 2026-08-19)
# 규칙(코드 주석에 적힌 설계): 서버 통신이 실패했을 때 큐에 쌓는다 / 같은 곡·난이도·플랫폼은 더 높은 점수 하나만 남긴다 /
# 다시 보낼 때 통신 실패(문자열 응답)는 큐에 남기고, 서버가 답한 영구 실패(딕셔너리 응답)와 성공은 큐에서 뺀다.
# 서버는 쓰지 않는다: 보내기 함수(submit_score)를 시험용으로 바꿔 준비한 응답을 돌려주게 하고, 진짜 클래스는 --no-server 에서 통신 실패로 남는지만 본다.

const RecordSupabaseSync := preload("res://scripts/core/RecordSupabaseSync.gd")

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	RecordSupabaseSync.new().clear_queue()


# 시험용: submit_score 를 부르면 미리 정한 응답을 차례로 돌려준다(서버 안 씀). 부른 곡 이름을 calls 에 남긴다.
class FakeSync extends "res://scripts/core/RecordSupabaseSync.gd":
	var outcomes: Array = []
	var calls: Array = []
	func submit_score(song_id: String, difficulty: String, platform: String,
			record: Dictionary, sequence: Array, lanemix_log: Array, ended_early: bool = false) -> Dictionary:
		calls.append(song_id)
		return outcomes.pop_front()


func rec(ex: int) -> Dictionary:
	return {"ex_score": ex, "ex_max": 300, "grade": "A", "max_combo": 5, "marks": ["clear"], "played_at": "2026-01-01T00:00:00Z"}


func queue_of(sync: RecordSupabaseSync) -> Array:
	return sync._load_queue()


func run() -> Array:
	var sync := RecordSupabaseSync.new()
	sync.clear_queue()
	eq("빈 큐: 파일이 없으면 빈 목록", queue_of(sync), [])
	await sync.process_queue()
	eq("빈 큐 처리: 아무 일도 없이 끝남", queue_of(sync), [])

	# ── 쌓기 ──
	sync.enqueue("songA", "EZ", "android", rec(100), [{"note_index": 0, "judgment": "Wow"}], ["base"], true)
	var q := queue_of(sync)
	eq("한 곡 쌓기: 항목 1개", q.size(), 1)
	eq("쌓은 항목에 곡·난이도·플랫폼·점수·시퀀스·레인믹스 로그·중도 종료가 그대로 저장됨",
		[q[0].song_id, q[0].difficulty, q[0].platform, float(q[0].record.ex_score), q[0].sequence.size(), q[0].lanemix_log, q[0].ended_early],
		["songA", "EZ", "android", 100.0, 1, ["base"], true])
	sync.enqueue("songA", "EZ", "android", rec(80), [], [])
	eq("같은 곡에 낮은 점수: 큐는 그대로(높은 점수 100 유지)", [queue_of(sync).size(), float(queue_of(sync)[0].record.ex_score)], [1, 100.0])
	sync.enqueue("songA", "EZ", "android", rec(120), [], [])
	eq("같은 곡에 높은 점수: 그 항목을 120 으로 교체(항목 수 그대로)", [queue_of(sync).size(), float(queue_of(sync)[0].record.ex_score)], [1, 120.0])
	sync.enqueue("songA", "EZ", "android", rec(120), [], [])
	eq("같은 곡에 같은 점수: 큐는 그대로", [queue_of(sync).size(), float(queue_of(sync)[0].record.ex_score)], [1, 120.0])
	sync.enqueue("songA", "NM", "android", rec(50), [], [])
	sync.enqueue("songA", "EZ", "pc", rec(60), [], [])
	sync.enqueue("songB", "EZ", "android", rec(70), [], [])
	eq("난이도·플랫폼·곡이 다르면 별도 항목(총 4개)", queue_of(sync).size(), 4)
	eq("새 인스턴스도 같은 파일을 읽음(저장은 파일에 남음)", RecordSupabaseSync.new()._load_queue().size(), 4)

	# ── 다시 보내기: 응답 종류별로 큐에서 빼거나 남긴다 ──
	var fake := FakeSync.new()
	fake.outcomes = [
		{"ok": false, "is_best": false, "record": {}, "permanent": false},   # 통신 실패 → 남김
		{"ok": false, "is_best": false, "record": {}, "permanent": true},    # 서버가 거절(영구 실패) → 뺌
		{"ok": true, "is_best": false, "record": {}},                         # 성공했지만 서버 기준 최고 아님 → 뺌
		{"ok": true, "is_best": true, "record": rec(70)},                     # 성공·최고 → 뺌
	]
	await fake.process_queue()
	eq("다시 보내기: 큐의 4개 항목을 차례로 한 번씩 보냄", fake.calls, ["songA", "songA", "songA", "songB"])
	var left := queue_of(sync)
	eq("다시 보내기 뒤: 통신 실패한 첫 항목만 남음", [left.size(), left[0].song_id, left[0].difficulty, left[0].platform], [1, "songA", "EZ", "android"])
	eq("남은 항목의 점수는 그대로", float(left[0].record.ex_score), 120.0)

	# ── 진짜 클래스: --no-server 는 통신 실패와 같아서 항목이 남아야 한다 ──
	await sync.process_queue()
	eq("--no-server 에서 진짜 전송: 통신 실패로 보고 항목을 남김", queue_of(sync).size(), 1)

	# ── 정리·손상 ──
	sync.clear_queue()
	eq("clear_queue: 파일 삭제 → 빈 목록", queue_of(sync), [])
	var f := FileAccess.open(RecordSupabaseSync.QUEUE_PATH, FileAccess.WRITE)
	f.store_string("{깨진 파일")
	f.close()
	eq("손상된 큐 파일: 빈 목록으로 읽음(오류 없이)", queue_of(sync), [])
	f = FileAccess.open(RecordSupabaseSync.QUEUE_PATH, FileAccess.WRITE)
	f.store_string("{\"a\": 1}")
	f.close()
	eq("배열이 아닌 큐 파일: 빈 목록으로 읽음", queue_of(sync), [])
	sync.clear_queue()
	return results
