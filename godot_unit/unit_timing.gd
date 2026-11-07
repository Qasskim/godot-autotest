extends RefCounted
# 모듈 3 — 박자와 타이밍 (기준: Godot/docs/DESIGN.md §8 "시퀀서 박자/스냅", §10 스크롤/타이밍)
#   TimeSignature : 박자 값 객체 (meta.meter "3/4", "6/8")
#   ChartTiming   : timing_events 기반 BPM·박자 테이블 (마디 길이 = 4 × 60000 / bpm × measure_length)
# 기대값은 공식에서 손으로 계산한 ms 값을 직접 적었다(코드와 같은 식을 다시 계산해서 비교하지 않는다).

const TOL := 1e-6
const ChartTiming := preload("res://scripts/core/ChartTiming.gd")   # class_name이 없는 스크립트라 게임 코드처럼 preload로 부른다

var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func near(name: String, actual: float, expected: float) -> void:
	check(name, absf(actual - expected) <= TOL, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func run() -> Array:
	_time_signature()
	_table_basics()
	_table_events()
	_table_lookups()
	_iter_measures()
	_convenience()
	return results


# ── 박자 (DESIGN §8: "3/4", "6/8", 숫자만 쓰면 n/4, 4/4 기본, 3/4 = 6/8 = 0.75) ──
func _time_signature() -> void:
	var len_cases := [["3/4", 0.75], ["6/8", 0.75], ["4/4", 1.0], ["5/4", 1.25], ["7/8", 0.875], ["2/2", 1.0], ["5", 1.25], ["4", 1.0], [" 3/4 ", 0.75]]
	for c in len_cases:
		var ts = TimeSignature.parse(c[0])
		check("박자 길이: \"%s\" → 4/4 기준 %s배" % [c[0], str(c[1])], ts != null and absf(ts.length() - c[1]) <= TOL, "실제 %s" % (str(ts.length()) if ts != null else "null"))
	var ts34 = TimeSignature.parse("3/4")
	eq("박자 파싱: \"3/4\"의 분자·분모", [ts34.numerator, ts34.denominator], [3, 4])
	eq("박자 파싱: 숫자만 쓰면 분모 4(\"5\" → 5/4)", [TimeSignature.parse("5").numerator, TimeSignature.parse("5").denominator], [5, 4])
	eq("박자 문자열: 3/4 → \"3/4\"", str(ts34), "3/4")
	for bad in ["", "abc", "0/4", "3/0", "-3/4", "3/4/4", "3/", "/4", "1.5/4", "3/x"]:
		eq("박자 파싱: 잘못된 값 \"%s\"은 null" % bad, TimeSignature.parse(bad), null)
	eq("박자 파싱: 문자열이 아니면(숫자 3, null) null", [TimeSignature.parse(3), TimeSignature.parse(null)], [null, null])
	eq("박자 기본값: 인자 없이 만들면 4/4", str(TimeSignature.new()), "4/4")
	eq("meta 박자: meter가 없으면 4/4", str(TimeSignature.from_meta({})), "4/4")
	eq("meta 박자: meter가 잘못되면 4/4로 돌아감", str(TimeSignature.from_meta({"meter": "abc"})), "4/4")
	eq("meta 박자: meter \"6/8\"", str(TimeSignature.from_meta({"meter": "6/8"})), "6/8")


# ── 테이블 기본 (마디 0부터 5000개, 마디 n 시작 = 앞 마디 길이의 합) ───────────
func _table_basics() -> void:
	var t: Array = ChartTiming.build_table({"bpm": 120.0}, [])
	eq("타이밍 테이블: 항상 마디 5000개", t.size(), 5000)
	near("타이밍 테이블: 120BPM 4/4 — 마디0 시작 0ms", t[0].ms, 0.0)
	near("타이밍 테이블: 120BPM 4/4 — 마디1 시작 2000ms (한 마디 2000ms)", t[1].ms, 2000.0)
	near("타이밍 테이블: 120BPM 4/4 — 마디10 시작 20000ms", t[10].ms, 20000.0)
	eq("타이밍 테이블: 각 행은 시작 ms·BPM·마디 길이 배수", [t[3].bpm, t[3].length], [120.0, 1.0])
	var t60: Array = ChartTiming.build_table({"bpm": 60.0}, [])
	near("타이밍 테이블: 60BPM 4/4 — 마디3 시작 12000ms (한 마디 4000ms)", t60[3].ms, 12000.0)
	var t34: Array = ChartTiming.build_table({"bpm": 120.0, "meter": "3/4"}, [])
	near("타이밍 테이블: 120BPM 3/4 — 마디4 시작 6000ms (한 마디 1500ms)", t34[4].ms, 6000.0)
	eq("타이밍 테이블: 3/4 곡의 마디 길이 배수 0.75", t34[0].length, 0.75)
	var t68: Array = ChartTiming.build_table({"bpm": 120.0, "meter": "6/8"}, [])
	near("타이밍 테이블: 6/8은 3/4와 같은 길이(마디2 시작 3000ms)", t68[2].ms, 3000.0)
	var t_nobpm: Array = ChartTiming.build_table({}, [])
	near("타이밍 테이블: BPM이 없으면 120 (마디1 시작 2000ms)", t_nobpm[1].ms, 2000.0)
	var mono := true
	for i in range(1, 5000):
		if not (t[i].ms > t[i - 1].ms):
			mono = false
	check("타이밍 테이블: 마디 시작 시각이 항상 증가", mono)


# ── timing_events (DESIGN §8: bpm?, measure_length? — 해당 마디부터 적용) ────────
func _table_events() -> void:
	var t: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 4, "bpm": 240.0}])
	near("이벤트: 마디4에서 240BPM — 마디4 시작은 변속 전 길이로 8000ms", t[4].ms, 8000.0)
	near("이벤트: 240BPM 마디는 1000ms — 마디5 시작 9000ms", t[5].ms, 9000.0)
	near("이벤트: 마디8 시작 12000ms (4마디 × 1000ms)", t[8].ms, 12000.0)
	eq("이벤트: 마디3은 변속 전 BPM 그대로, 마디4부터 새 BPM", [t[3].bpm, t[4].bpm], [120.0, 240.0])

	var tm: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 2, "measure_length": 0.75}])
	near("이벤트: 마디2에서 3/4(0.75) — 마디3 시작은 4000+1500=5500ms", tm[3].ms, 5500.0)
	near("이벤트: 3/4 마디가 이어지면 마디4 시작 7000ms", tm[4].ms, 7000.0)
	eq("이벤트: BPM만 바뀌면 마디 길이는 그대로", ChartTiming.build_table({"bpm": 120.0, "meter": "3/4"}, [{"measure": 2, "bpm": 60.0}])[3].length, 0.75)

	var both: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 1, "bpm": 60.0, "measure_length": 0.5}])
	near("이벤트: BPM과 마디 길이가 같은 마디에서 같이 바뀜 — 마디1 길이 4×60000/60×0.5=2000ms", both[2].ms - both[1].ms, 2000.0)

	var unsorted: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 4, "bpm": 240.0}, {"measure": 2, "bpm": 60.0}])
	near("이벤트: 순서가 뒤섞여 있어도 마디 순으로 적용 — 마디2에서 60BPM(4000ms), 마디4에서 240BPM", unsorted[4].ms, 2.0 * 2000.0 + 2.0 * 4000.0)
	near("이벤트: 뒤섞인 이벤트 — 마디5 시작 = 4000+8000+1000", unsorted[5].ms, 13000.0)

	var first: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 0, "bpm": 60.0}])
	near("이벤트: 마디0 이벤트는 곡 시작부터 적용 — 마디1 시작 4000ms", first[1].ms, 4000.0)
	var meter_over: Array = ChartTiming.build_table({"bpm": 120.0, "meter": "3/4"}, [{"measure": 2, "measure_length": 1.0}])
	near("이벤트: 곡 초기 박자 3/4 위에 마디2에서 4/4로 변경 — 마디3 시작 3000+2000=5000ms", meter_over[3].ms, 5000.0)
	var same: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 3, "bpm": 100.0}, {"measure": 3, "bpm": 200.0}])
	eq("이벤트: 같은 마디에 이벤트가 둘이면 나중 값이 적용됨", same[3].bpm, 200.0)


# ── 조회 (마디→ms, ms→BPM) ───────────────────────────────────────
func _table_lookups() -> void:
	var t: Array = ChartTiming.build_table({"bpm": 120.0}, [{"measure": 4, "bpm": 240.0}])
	near("마디→ms: 마디4 = 8000", ChartTiming.measure_to_ms_table(t, 4), 8000.0)
	near("마디→ms: 음수 마디는 0으로 고정", ChartTiming.measure_to_ms_table(t, -3), 0.0)
	near("마디→ms: 마지막 마디를 넘으면 마지막 마디 시작으로 고정", ChartTiming.measure_to_ms_table(t, 99999), t[4999].ms)
	near("마디→ms: 빈 테이블은 0", ChartTiming.measure_to_ms_table([], 3), 0.0)
	near("ms→BPM: 곡 시작(0ms)은 첫 BPM", ChartTiming.bpm_at_ms_table(t, 0.0), 120.0)
	near("ms→BPM: 변속 직전(7999ms)은 이전 BPM", ChartTiming.bpm_at_ms_table(t, 7999.0), 120.0)
	near("ms→BPM: 변속 시각(8000ms)부터 새 BPM", ChartTiming.bpm_at_ms_table(t, 8000.0), 240.0)
	near("ms→BPM: 변속 이후 아무 시각이나 새 BPM", ChartTiming.bpm_at_ms_table(t, 20000.0), 240.0)
	near("ms→BPM: 음수 시각(곡 시작 전 카운트다운)은 첫 BPM", ChartTiming.bpm_at_ms_table(t, -3000.0), 120.0)
	near("ms→BPM: 빈 테이블은 120", ChartTiming.bpm_at_ms_table([], 1000.0), 120.0)


func _iter_measures() -> void:
	var t: Array = ChartTiming.build_table({"bpm": 120.0}, [])
	var m: Array = ChartTiming.iter_measures_from_table(t, 3000.0, 7000.0)
	var idx: Array = []
	for r in m:
		idx.append(r.measure)
	eq("가시 마디: 3000~7000ms에 걸치는 마디는 1(2000~4000)~3(6000~8000) → [1,2,3]", idx, [1, 2, 3])
	eq("가시 마디: 각 항목의 시작·길이·BPM", [m[0].start_ms, m[0].dur_ms, m[0].bpm], [2000.0, 2000.0, 120.0])
	var edge: Array = ChartTiming.iter_measures_from_table(t, 4000.0, 4000.0)
	var eidx: Array = []
	for r in edge:
		eidx.append(r.measure)
	eq("가시 마디: 4000ms 한 점은 마디1의 끝과 마디2의 시작 — 두 마디 모두 포함", eidx, [1, 2])
	eq("가시 마디: 곡 시작 앞쪽 범위(-5000~-1)는 마디가 없음", ChartTiming.iter_measures_from_table(t, -5000.0, -1.0).size(), 0)
	var v: Array = ChartTiming.iter_measures_from_table(ChartTiming.build_table({"bpm": 120.0}, [{"measure": 2, "bpm": 240.0}]), 4000.0, 5000.0)
	var after_change: Dictionary = {}
	for r in v:
		if r.measure == 2:
			after_change = r
	eq("가시 마디: 마디2(240BPM 변속 후)는 시작 4000ms·길이 1000ms·BPM 240", [after_change.get("start_ms"), after_change.get("dur_ms"), after_change.get("bpm")], [4000.0, 1000.0, 240.0])


# ── 편의 함수 (매번 테이블을 새로 만들어도 같은 값) ─────────────────────
func _convenience() -> void:
	var meta := {"bpm": 120.0}
	var ev := [{"measure": 4, "bpm": 240.0}]
	near("편의 함수: measure_to_ms = 테이블 조회와 같은 값(8000)", ChartTiming.measure_to_ms(meta, ev, 4), 8000.0)
	near("편의 함수: bpm_at_ms = 테이블 조회와 같은 값(240)", ChartTiming.bpm_at_ms(meta, ev, 9000.0), 240.0)
	eq("편의 함수: iter_measures = 테이블 조회와 같은 결과", ChartTiming.iter_measures(meta, ev, 0.0, 5000.0), ChartTiming.iter_measures_from_table(ChartTiming.build_table(meta, ev), 0.0, 5000.0))
