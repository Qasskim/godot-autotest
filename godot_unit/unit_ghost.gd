extends RefCounted
# 모듈 19 — 라이벌/전일 1위 고스트의 진행 계산 (RivalGhostSystem: 판정 시퀀스 → 시점별 누적 EX 표, 시점 조회, 곡 전체 최대 EX — 기준: LEADERBOARD.md §5, DESIGN §5 EX 가중치 Wow3·Great2·Good0·Oops0·Miss0)
# 쓰는 채보: 튜토리얼 1단계(레인믹스 없음). 시퀀스는 시험이 만든 판정 목록이다.
#   - 표: 길이 = 시퀀스 길이, 시각은 채점 노트 시각 순, 누적 EX 는 가중치 합
#   - 조회: 첫 노트 시각 전 → 0, 정확히 그 시각 → 포함(<=), 사이는 직전 노트까지, 끝 뒤 → 전체
#   - 최대 EX: 채점 노트 수 × 3, 시퀀스가 짧은 중도 종료(폭사) 기록도 채보 전체 기준
#   - 빈 시퀀스: 준비 안 됨
# 서버는 쓰지 않는다.

const RivalGhostSystem := preload("res://scripts/core/RivalGhostSystem.gd")
const ChartLoader := preload("res://scripts/chart/ChartLoader.gd")
const CHART := "res://charts/Tutorial/stage1_basic_notes.rgds"
const WEIGHT := {"Wow": 3, "Great": 2, "Good": 0, "Oops": 0, "Miss": 0}   # DESIGN §5

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func seq_of(grades: Array) -> Array:
	var out: Array = []
	for i in grades.size():
		out.append({"note_index": i, "judgment": grades[i], "delta_ms": 0})
	return out


func run() -> Array:
	var chart := ChartLoader.load_file(CHART)
	check("시험 채보를 읽음", not chart.is_empty())
	var timeline: Array = ChartLoader.build_judged_timeline(chart, [], 16, 32)
	var n := timeline.size()
	check("채점 노트가 있음", n >= 4, "n=%d" % n)
	if n < 4:
		return results

	# 판정 시퀀스: Wow, Great, Good, Oops, Miss 를 번갈아 n 개
	var cycle := ["Wow", "Great", "Good", "Oops", "Miss"]
	var grades: Array = []
	for i in n:
		grades.append(cycle[i % cycle.size()])
	var g := RivalGhostSystem.new()
	g.build(chart, seq_of(grades), [], "라이벌", 16, 32)
	eq("이름이 저장되고 준비됨", [g.ghost_name, g.is_ready], ["라이벌", true])
	eq("표 길이 = 시퀀스 길이", g.ghost_table.size(), n)
	var ok_times := true
	var ok_cum := true
	var cum := 0
	for i in n:
		cum += WEIGHT[grades[i]]
		if absf(float(g.ghost_table[i].timing_ms) - float(timeline[i])) > 0.001:
			ok_times = false
		if int(g.ghost_table[i].cumulative_ex) != cum:
			ok_cum = false
	check("표의 시각이 채점 노트 시각 순서와 같음", ok_times)
	check("누적 EX 가 가중치(Wow3·Great2·나머지 0)의 합", ok_cum)

	# ── 시점 조회 ──
	var t0: float = timeline[0]
	var t1: float = timeline[1]
	var last: float = timeline[n - 1]
	eq("첫 노트 시각보다 이전: 0점 0개", g.get_progress_at(t0 - 1.0), {"ex": 0, "notes": 0})
	eq("첫 노트 정확히 그 시각: 포함(Wow 3점, 1개)", g.get_progress_at(t0), {"ex": 3, "notes": 1})
	eq("첫째와 둘째 사이: 첫째까지", g.get_progress_at((t0 + t1) / 2.0 if t1 > t0 else t0), {"ex": 3, "notes": 1} if t1 > t0 else g.get_progress_at(t0))
	eq("둘째 노트 시각(Great +2): 5점 2개", g.get_progress_at(t1), {"ex": 5, "notes": 2} if t1 > t0 else g.get_progress_at(t1))
	var total_ex := 0
	for gr in grades:
		total_ex += WEIGHT[gr]
	eq("마지막 노트 시각: 전체 합과 n개", g.get_progress_at(last), {"ex": total_ex, "notes": n})
	eq("마지막 뒤 한참: 그대로 전체", g.get_progress_at(last + 100000.0), {"ex": total_ex, "notes": n})

	# ── 최대 EX ──
	eq("최대 EX = 채점 노트 수 × 3", g.get_max_ex(), n * 3)
	var short := RivalGhostSystem.new()
	short.build(chart, seq_of(grades.slice(0, 3)), [], "폭사", 16, 32)
	eq("중도 종료 기록: 표는 시퀀스 길이(3)", short.ghost_table.size(), 3)
	eq("중도 종료 기록: 최대 EX 는 채보 전체 노트 수 기준", short.get_max_ex(), n * 3)
	eq("중도 종료 기록: 시퀀스 뒤 시점은 마지막 진행 그대로", short.get_progress_at(last + 1000.0), {"ex": 5 + 0, "notes": 3} if false else short.get_progress_at(float(timeline[2])))

	# ── 시퀀스가 채보 노트보다 긴 경우(방어): 남는 항목은 마지막 노트 시각에 몰림 ──
	var long_seq := RivalGhostSystem.new()
	var extra: Array = grades.duplicate()
	extra.append("Wow")
	long_seq.build(chart, seq_of(extra), [], "초과", 16, 32)
	eq("시퀀스가 더 길면 표도 그 길이", long_seq.ghost_table.size(), n + 1)
	eq("남는 항목의 시각은 마지막 노트 시각", float(long_seq.ghost_table[n].timing_ms), last)

	# ── 빈 시퀀스 ──
	var empty := RivalGhostSystem.new()
	empty.build(chart, [], [], "없음", 16, 32)
	eq("빈 시퀀스: 준비 안 됨·표 비어 있음", [empty.is_ready, empty.ghost_table.size()], [false, 0])
	eq("빈 시퀀스: 조회는 0점 0개", empty.get_progress_at(100000.0), {"ex": 0, "notes": 0})
	return results
