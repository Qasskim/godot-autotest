extends RefCounted
# 모듈 4 — 레인믹스 상태·진입 안내·노트 랜덤 (기준: Godot/docs/DESIGN.md §9 레인믹스, §7 노트 랜덤)
#   LaneMixState  : 섹션 목록, 키모드 랜덤(-1)/슈퍼랜덤(-2) 결정, 구간 경계, 활성화·폐기
#   LaneMixEntry  : 안내 시작 시각(2마디 전), 수락, 원복·단계 미리보기(3초 전)
#   NoteRandomizer: RANDOM(곡 전체 고정 섞기) / S-RANDOM(노트마다, 드래그 체인 점유 그룹 회피)
# 기대값은 DESIGN.md의 문장과 손으로 계산한 시각이다. 무작위가 섞인 부분은 여러 번 반복해 성질(범위·최소 1회·중복 없음)을 확인한다.

const TOL := 1e-6
const SPEC_GROUPS := {
	4:  [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]],
	5:  [[0, 1, 2], [3, 4, 5], [6, 7, 8, 9], [10, 11, 12], [13, 14, 15]],
	6:  [[0, 1, 2], [3, 4], [5, 6, 7], [8, 9, 10], [11, 12], [13, 14, 15]],
	8:  [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9], [10, 11], [12, 13], [14, 15]],
	16: [[0], [1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11], [12], [13], [14], [15]],
}
const MODES := [4, 5, 6, 8, 16]
const TRIALS := 200   # 무작위 성질을 확인하는 반복 횟수

var results: Array = []
var _free_nodes: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	for n in _free_nodes:
		if is_instance_valid(n):
			n.free()
	_free_nodes.clear()


func run() -> Array:
	_constants()
	_sections()
	_section_idx()
	_random_targets()
	_super_random()
	_activation()
	_entry_notice()
	_entry_offer_arm()
	_entry_previews()
	_randomizer_none()
	_randomizer_random()
	_randomizer_s_random()
	return results


func _state(sections: Array) -> LaneMixState:
	var lm := LaneMixState.new()
	lm.sections = sections
	return lm


func _sec(start: float, end: float, target: int = 8, pool: Array = []) -> Dictionary:
	return {"start": start, "end": end, "target_mode": target, "random_pool": pool}


# ── 수치 ──────────────────────────────────────────────────────────
func _constants() -> void:
	eq("수치: 레인믹스 안내는 시작 2마디 전부터 (DESIGN §9)", GameBalance.LANEMIX_NOTICE_MEASURES, 2)
	eq("수치: 진입·원복 카운트다운은 3박 전부터 (DESIGN §9)", GameBalance.LANEMIX_COUNTDOWN_BEATS, 3)
	eq("수치: 원복 미리보기는 3초 전부터 (DESIGN §9)", GameBalance.LANEMIX_RETURN_PREVIEW_SEC, 3.0)
	eq("수치: 키 수 변경(step) 미리보기는 3초 전부터 (DESIGN §9)", GameBalance.LANEMIX_STEP_PREVIEW_SEC, 3.0)
	eq("수치: 키모드 랜덤 -1, 슈퍼랜덤 -2 (DESIGN §9)", [LaneMixState.RANDOM_TARGET, LaneMixState.SUPER_RANDOM_TARGET], [-1, -2])
	eq("수치: 슈퍼랜덤은 5~8회 (DESIGN §9)", [LaneMixState.SUPER_RANDOM_MIN_STEPS, LaneMixState.SUPER_RANDOM_MAX_STEPS], [5, 8])
	eq("수치: 랜덤 기본 풀은 4·5·6·8·16키", LaneMixState.DEFAULT_RANDOM_POOL, [4, 5, 6, 8, 16])
	eq("수치: 노트 랜덤이 미리 계산하는 키모드는 4·5·6·8·16", NoteRandomizer.KEY_MODES, [4, 5, 6, 8, 16])


# ── 섹션 만들기 (lanemix_start/lanemix_end 짝) ─────────────────────
func _sections() -> void:
	var lm := LaneMixState.new()
	lm.events = [
		{"ms": 10000.0, "action": "lanemix_start", "target_mode": 8},
		{"ms": 20000.0, "action": "lanemix_end"},
		{"ms": 30000.0, "action": "lanemix_start", "target_mode": 6, "random_pool": [4, 6]},
		{"ms": 40000.0, "action": "lanemix_end"},
	]
	lm.build_sections()
	eq("섹션: start/end 두 쌍 → 섹션 2개(시작·끝·목표 키모드)", [lm.sections.size(), lm.sections[0].start, lm.sections[0].end, lm.sections[0].target_mode], [2, 10000.0, 20000.0, 8])
	eq("섹션: 두 번째 섹션의 목표와 랜덤 풀", [lm.sections[1].target_mode, lm.sections[1].random_pool], [6, [4, 6]])
	eq("섹션: 섹션마다 노트 집계 칸(base·lanemix 각 notes·ticks)이 0으로 만들어짐",
		lm.note_counts, {0: {"base": {"notes": 0, "ticks": 0}, "lanemix": {"notes": 0, "ticks": 0}}, 1: {"base": {"notes": 0, "ticks": 0}, "lanemix": {"notes": 0, "ticks": 0}}})

	var un := LaneMixState.new()
	un.events = [{"ms": 30000.0, "action": "lanemix_end"}, {"ms": 20000.0, "action": "lanemix_end"}, {"ms": 10000.0, "action": "lanemix_start", "target_mode": 4}]
	un.build_sections()
	eq("섹션: 이벤트 순서가 뒤섞여 있어도 시각순으로 짝을 맞춤(첫 end가 구간을 닫음)", [un.sections.size(), un.sections[0].start, un.sections[0].end], [1, 10000.0, 20000.0])

	var orphan := LaneMixState.new()
	orphan.events = [{"ms": 5000.0, "action": "lanemix_end"}, {"ms": 50000.0, "action": "lanemix_start", "target_mode": 8}]
	orphan.build_sections()
	eq("섹션: 짝 없는 end, 끝나지 않는 start는 섹션이 되지 않음", orphan.sections.size(), 0)

	var adj := LaneMixState.new()
	adj.events = [
		{"ms": 10000.0, "action": "lanemix_start", "target_mode": 8},
		{"ms": 20000.0, "action": "lanemix_start", "target_mode": 6},
		{"ms": 20000.0, "action": "lanemix_end"},
		{"ms": 30000.0, "action": "lanemix_end"},
	]
	adj.build_sections()
	eq("섹션: 같은 시각이면 end를 먼저 처리해 앞 구간을 닫고 바로 다음 구간을 엶(앞 구간이 사라지지 않음)",
		[adj.sections.size(), adj.sections[0].end, adj.sections[1].start, adj.sections[1].target_mode], [2, 20000.0, 20000.0, 6])


# ── 구간 경계 (DESIGN §9: 시작 시각은 항상 포함, 끝 시각은 레인믹스 레이어 노트에만 포함) ──
func _section_idx() -> void:
	var lm := _state([_sec(10000.0, 20000.0), _sec(30000.0, 40000.0)])
	eq("구간 경계: 시작 직전은 구간 밖", lm.get_section_idx(9999.9), -1)
	eq("구간 경계: 시작 시각은 구간 안(포함)", lm.get_section_idx(10000.0), 0)
	eq("구간 경계: 구간 한가운데", lm.get_section_idx(15000.0), 0)
	eq("구간 경계: 끝 시각은 기본 레이어에는 구간 밖(제외)", lm.get_section_idx(20000.0), -1)
	eq("구간 경계: 끝 시각은 레인믹스 레이어 노트에는 구간 안(include_end)", lm.get_section_idx(20000.0, true), 0)
	eq("구간 경계: 끝 시각을 넘으면 include_end여도 구간 밖", lm.get_section_idx(20000.1, true), -1)
	eq("구간 경계: 두 번째 구간 시작·끝", [lm.get_section_idx(30000.0), lm.get_section_idx(40000.0, true), lm.get_section_idx(40000.0)], [1, 1, -1])
	eq("구간 경계: 구간 사이", lm.get_section_idx(25000.0, true), -1)
	var adj := _state([_sec(10000.0, 20000.0), _sec(20000.0, 30000.0)])
	eq("구간 경계: 이어진 구간의 접점(20000)은 기본 레이어에서 다음 구간 시작으로 본다", adj.get_section_idx(20000.0), 1)


# ── 키모드 랜덤 -1 (DESIGN §9: 트리거 성공 시점에 풀에서 1회 무작위 선택) ──
func _random_targets() -> void:
	var fixed := _state([_sec(0.0, 1000.0, 8)])
	eq("목표 키모드: 고정값(8)은 그대로", fixed.resolve_target_mode(0), 8)
	var seen := {}
	var bad := false
	var cache_bad := false
	for i in TRIALS:
		var lm := _state([_sec(0.0, 1000.0, LaneMixState.RANDOM_TARGET, [4, 6])])
		var v: int = lm.resolve_target_mode(0)
		seen[v] = true
		if not (v in [4, 6]):
			bad = true
		if lm.resolve_target_mode(0) != v or lm.sections[0].target_mode != v:
			cache_bad = true
	check("키모드 랜덤: 지정한 풀(4·6)에서만 고르고 둘 다 나온다(%d회)" % TRIALS, not bad and seen.has(4) and seen.has(6), str(seen.keys()))
	check("키모드 랜덤: 한 번 정해지면 다시 불러도 같은 값이고 섹션에 저장됨(트리거 재시도로 바뀌지 않음)", not cache_bad)
	var seen_default := {}
	var bad_default := false
	for i in TRIALS:
		var lm2 := _state([_sec(0.0, 1000.0, LaneMixState.RANDOM_TARGET)])
		var v2: int = lm2.resolve_target_mode(0)
		seen_default[v2] = true
		if not (v2 in [4, 5, 6, 8, 16]):
			bad_default = true
	check("키모드 랜덤: 풀이 비어 있으면 기본 풀(4·5·6·8·16)에서 고르고 다섯 개가 모두 나온다(%d회)" % TRIALS, not bad_default and seen_default.size() == 5, str(seen_default.keys()))


# ── 키모드 슈퍼랜덤 -2 (DESIGN §9: 5~8회, 모든 키모드 최소 1회 보장) ──────────────
func _super_random() -> void:
	var len_bad: Array = []
	var cover_bad: Array = []
	var adj_bad: Array = []
	var pop_bad: Array = []
	var first_bad := 0
	var lengths := {}
	for i in TRIALS:
		var lm := _state([_sec(0.0, 1000.0, LaneMixState.SUPER_RANDOM_TARGET)])
		var before: bool = lm.is_super_section(0)
		var first: int = lm.resolve_target_mode(0)
		var seq: Array = lm.super_sequences.get(0, [])
		lengths[seq.size()] = true
		if before or not lm.is_super_section(0):
			first_bad += 1
		if seq.size() < 5 or seq.size() > 8:
			len_bad.append(seq.size())
		if first != seq[0]:
			first_bad += 1
		for m in [4, 5, 6, 8, 16]:
			if not (m in seq):
				cover_bad.append("%s 에 %d 없음" % [str(seq), m])
				break
		for j in range(1, seq.size()):
			if seq[j] == seq[j - 1]:
				adj_bad.append(str(seq))
				break
		if lm.resolve_target_mode(0) != first:
			first_bad += 1
		var popped: Array = []
		for j in range(1, seq.size()):
			popped.append(lm.pop_super_step(0))
		if popped != seq.slice(1) or lm.pop_super_step(0) != 0:
			pop_bad.append(str(seq))
	check("슈퍼랜덤: 전환 횟수는 항상 5~8회(%d회 시행)" % TRIALS, len_bad.is_empty() and lengths.size() >= 3, "벗어난 길이 %s, 나온 길이 %s" % [str(len_bad.slice(0, 3)), str(lengths.keys())])
	check("슈퍼랜덤: 풀의 모든 키모드(4·5·6·8·16)가 최소 1회 포함", cover_bad.is_empty(), "; ".join(cover_bad.slice(0, 2)))
	check("슈퍼랜덤: 같은 키모드가 연달아 나오지 않음", adj_bad.is_empty(), "; ".join(adj_bad.slice(0, 2)))
	check("슈퍼랜덤: 첫 값은 시퀀스 첫 항목이고 다시 불러도 같으며 슈퍼 구간으로 표시됨", first_bad == 0, "어긋난 횟수 %d" % first_bad)
	check("슈퍼랜덤: pop_super_step은 둘째 항목부터 순서대로 돌려주고 소진되면 0", pop_bad.is_empty(), "; ".join(pop_bad.slice(0, 2)))

	var small_adj := 0
	var small_miss := 0
	for i in 50:
		var lm2 := _state([_sec(0.0, 1000.0, LaneMixState.SUPER_RANDOM_TARGET, [4, 6])])
		lm2.resolve_target_mode(0)
		var s2: Array = lm2.super_sequences[0]
		if not (4 in s2 and 6 in s2):
			small_miss += 1
		for j in range(1, s2.size()):
			if s2[j] == s2[j - 1]:
				small_adj += 1
				break
	check("슈퍼랜덤: 풀을 4·6으로 지정하면 둘 다 포함되고 번갈아 나옴", small_adj == 0 and small_miss == 0, "중복 %d / 누락 %d" % [small_adj, small_miss])
	var one := _state([_sec(0.0, 1000.0, LaneMixState.SUPER_RANDOM_TARGET, [8])])
	var one_val = one.resolve_target_mode(0)
	eq("슈퍼랜덤: 풀이 1개(8)뿐이어도 오류 없이 그 값을 돌려줌", one_val, 8)
	eq("슈퍼랜덤: 소진 전 pop_super_step 조회가 없는 구간은 0", _state([_sec(0.0, 1000.0)]).pop_super_step(0), 0)


# ── 활성화·폐기·만료 ──────────────────────────────────────────────
func _activation() -> void:
	var lm := _state([_sec(0.0, 1000.0), _sec(2000.0, 3000.0)])
	var a := Node.new()
	var b := Node.new()
	var c := Node.new()
	_free_nodes.append_array([a, b, c])
	lm.add_pending_node(0, a)
	lm.add_pending_node(0, b)
	lm.add_pending_node(1, c)
	lm.pending_idx = 0
	var got: Array = lm.activate_lanemix(0)
	eq("활성화: 대기 중이던 레인믹스 노드를 돌려주고 대기 목록에서 지움", [got == [a, b], lm.pending_nodes.has(0), lm.pending_nodes.has(1)], [true, false, true])
	eq("활성화: 결정=lanemix, 진행 중 표시, 대기 해제", [lm.resolved[0], lm.is_active, lm.active_idx, lm.pending_idx], ["lanemix", true, 0, -1])
	lm.end_section()
	eq("구간 종료: 진행 중 표시 해제", [lm.is_active, lm.active_idx], [false, -1])
	lm.pending_idx = 1
	var dropped: Array = lm.discard_pending_lanemix(1)
	eq("폐기: 트리거 실패 시 대기 노드를 돌려주고 결정=base, 진행 중 상태는 건드리지 않음", [dropped == [c], lm.resolved[1], lm.pending_idx, lm.is_active], [true, "base", -1, false])
	eq("폐기: 대기 노드가 없는 섹션은 빈 목록", _state([_sec(0.0, 1.0)]).discard_pending_lanemix(0), [])

	var ex := _state([_sec(0.0, 1000.0)])
	eq("만료 확인: 대기 중인 섹션이 없으면 -1", ex.check_trigger_expiry(), -1)
	var trig := Node.new()
	ex.pending_idx = 2
	ex.current_trigger = trig
	eq("만료 확인: 트리거 노드가 살아 있으면 -1(아직 만료 아님)", ex.check_trigger_expiry(), -1)
	trig.free()
	eq("만료 확인: 트리거가 소멸되면 그 섹션 번호 반환(트리거를 안 치면 base로 넘어가는 기준)", ex.check_trigger_expiry(), 2)
	ex.current_trigger = null
	eq("만료 확인: 트리거 참조가 null이어도 섹션 번호 반환", ex.check_trigger_expiry(), 2)

	var rs := _state([_sec(0.0, 1000.0)])
	rs.events = [{"ms": 1.0, "action": "x"}]
	rs.resolved[0] = "base"
	rs.is_active = true
	rs.active_idx = 0
	rs.pending_idx = 0
	rs.super_sequences[0] = [4]
	rs.reset()
	eq("초기화: reset은 섹션·결정·이벤트·슈퍼 시퀀스·진행 상태를 모두 비움", [rs.sections.size(), rs.resolved.size(), rs.events.size(), rs.super_sequences.size(), rs.is_active, rs.active_idx, rs.pending_idx], [0, 0, 0, 0, false, -1, -1])


# ── 진입 안내 (DESIGN §9: lanemix_start 2마디 전부터 안내, 앞 구간 진행 중엔 안내 없음) ──
func _measures(step: float, count: int) -> Array:
	var arr: Array = []
	for i in count:
		arr.append(step * i)
	return arr


func _new_entry(sections: Array, measures: Array) -> LaneMixEntry:
	var lm := _state(sections)
	var calc := NotePositionCalculator.new()
	_free_nodes.append(calc)
	var entry := LaneMixEntry.new()
	entry.setup(lm, null, calc, measures)
	return entry


func _entry_notice() -> void:
	var ms := _measures(2000.0, 101)   # 120BPM 4/4: 한 마디 2000ms
	var entry := _new_entry([_sec(10000.0, 20000.0), _sec(30000.0, 40000.0), _sec(41000.0, 50000.0)], ms)
	eq("안내 시작: 시작(10000, 마디5)의 2마디 앞 마디 시작 = 6000", entry._notice_ms[0], 6000.0)
	eq("안내 시작: 앞 구간 끝(20000) 뒤라면 그대로 — 30000의 2마디 앞 = 26000", entry._notice_ms[1], 26000.0)
	eq("안내 시작: 앞 구간이 진행 중일 때는 다음 안내를 미룸 — 41000의 2마디 앞(36000)이 앞 구간 끝(40000)보다 이르면 40000", entry._notice_ms[2], 40000.0)
	var early := _new_entry([_sec(3000.0, 9000.0)], ms)
	eq("안내 시작: 곡 시작 2마디 안이면 0(음수로 내려가지 않음)", early._notice_ms[0], 0.0)
	var slack := _new_entry([_sec(9999.7, 19999.0)], ms)
	eq("안내 시작: 마디 시작 0.5ms 이내 오차는 같은 마디로 본다(9999.7 → 마디5 → 6000)", slack._notice_ms[0], 6000.0)
	var none := _new_entry([_sec(10000.0, 20000.0)], [])
	eq("안내 시작: 마디 목록이 비면 0", none._notice_ms[0], 0.0)
	eq("수락 상태: 처음에는 어느 섹션도 수락되지 않음", entry.is_armed(0), false)


func _entry_offer_arm() -> void:
	var ms := _measures(2000.0, 101)
	var entry := _new_entry([_sec(10000.0, 20000.0), _sec(30000.0, 40000.0)], ms)
	eq("안내 창: 안내 시작(6000) 전에는 없음", entry.offer_idx(5999.0), -1)
	eq("안내 창: 안내 시작 시각(6000)부터 첫 구간", entry.offer_idx(6000.0), 0)
	eq("안내 창: 시작 직전(9999)까지 유지", entry.offer_idx(9999.0), 0)
	eq("안내 창: 시작 시각(10000)에는 닫힘", entry.offer_idx(10000.0), -1)
	eq("안내 창: 두 번째 구간의 안내 창", entry.offer_idx(27000.0), 1)
	entry.arm(5000.0)
	eq("수락: 안내가 뜨기 전 입력은 무시", entry.is_armed(0), false)
	entry.arm(10500.0)
	eq("수락: 시작 후 입력은 무시", entry.is_armed(0), false)
	entry.arm(8000.0)
	eq("수락: 안내가 떠 있는 동안 받으면 그 섹션이 수락됨", [entry.is_armed(0), entry.is_armed(1)], [true, false])
	entry._lanemix.resolved[1] = "base"
	entry.arm(27000.0)
	eq("수락: 이미 결정된 섹션은 안내가 뜨지 않아 수락되지 않음", [entry.offer_idx(27000.0), entry.is_armed(1)], [-1, false])
	var upd := LaneMixEntry.new()
	upd.update(1000.0, 4, 4, false, false)
	check("update: setup 전에 불러도 오류 없이 무시", true)


# ── 미리보기 (DESIGN §9: 원복·step 3초 전부터 바뀔 배치를 선으로 미리 보여줌) ───────────
func _entry_previews() -> void:
	var ms := _measures(2000.0, 101)
	var entry := _new_entry([_sec(10000.0, 20000.0)], ms)
	var lm: LaneMixState = entry._lanemix
	lm.is_active = true
	lm.active_idx = 0
	eq("원복 미리보기: 끝 3초 전(17000)부터 돌아갈 기본 키모드(4)", entry.return_preview_mode(17000.0, 8, 4), 4)
	eq("원복 미리보기: 끝 2.5초 전", entry.return_preview_mode(17500.0, 8, 4), 4)
	eq("원복 미리보기: 3초보다 일찍(16999)에는 없음", entry.return_preview_mode(16999.0, 8, 4), 0)
	eq("원복 미리보기: 끝 시각(20000)에는 없음", entry.return_preview_mode(20000.0, 8, 4), 0)
	eq("원복 미리보기: 지금 키모드가 이미 기본이면 없음", entry.return_preview_mode(17500.0, 4, 4), 0)
	lm.is_active = false
	eq("원복 미리보기: 구간 진행 중이 아니면 없음", entry.return_preview_mode(17500.0, 8, 4), 0)
	lm.is_active = true

	lm.events = [
		{"ms": 12000.0, "action": "lanemix_step", "target_mode": 5},
		{"ms": 15000.0, "action": "lanemix_step", "target_mode": 6},
		{"ms": 25000.0, "action": "lanemix_step", "target_mode": 4},
	]
	eq("step 미리보기: 다음 step 3초 전(9000)에는 구간 시작 전이라도 진행 중이면 3.0초 경계 포함 → 5", entry.step_preview_mode(9000.0, 8), 5)
	eq("step 미리보기: 3초보다 이른(8999) 시각에는 없음", entry.step_preview_mode(8999.0, 8), 0)
	eq("step 미리보기: step 직전(11999)", entry.step_preview_mode(11999.0, 8), 5)
	eq("step 미리보기: 시각이 정확히 step(12000)이면 그 step은 지난 것으로 보고 다음 step(15000)까지 정확히 3.0초 → 목표 6", entry.step_preview_mode(12000.0, 8), 6)
	eq("step 미리보기: 첫 step 지난 뒤 다음 step이 3초 안이면 그 목표(12500 → 6)", entry.step_preview_mode(12500.0, 5), 6)
	eq("step 미리보기: 이미 그 키모드면 없음", entry.step_preview_mode(12500.0, 6), 0)
	eq("step 미리보기: 구간 끝 이후의 step(25000)은 보지 않음", entry.step_preview_mode(16000.0, 6), 0)
	lm.super_sequences[0] = [4, 5, 6]
	eq("step 미리보기: 슈퍼랜덤 구간은 다음 목표를 미리 알 수 없어 없음", entry.step_preview_mode(12500.0, 5), 0)
	lm.super_sequences.clear()
	lm.is_active = false
	eq("step 미리보기: 진행 중이 아니면 없음", entry.step_preview_mode(12500.0, 5), 0)


# ── 노트 랜덤 (DESIGN §7) ─────────────────────────────────────────
func _group_of(km: int, lane: int) -> int:
	for i in SPEC_GROUPS[km].size():
		if lane in SPEC_GROUPS[km][i]:
			return i
	return -1


func _randomizer_none() -> void:
	var nr := NoteRandomizer.new()
	nr.build([], NoteRandomizer.Mode.NONE, 1)
	eq("노트 랜덤 없음: 레인은 그대로(16 이상은 %16)", [nr.remap_lane(5, 8, "a"), nr.remap_lane(17, 4, "b"), nr.remap_lane(31, 16, "c")], [5, 1, 15])
	nr.build([], NoteRandomizer.Mode.RANDOM, 1)
	eq("노트 랜덤: 표에 없는 키모드(7)는 레인 그대로", nr.remap_lane(9, 7, "x"), 9)


func _randomizer_random() -> void:
	for km in MODES:
		var nr := NoteRandomizer.new()
		nr.build([], NoteRandomizer.Mode.RANDOM, 4242)
		var groups: Array = SPEC_GROUPS[km]
		var targets: Array = []
		var lane_bad: Array = []
		for g in groups.size():
			var first_res: int = nr.remap_lane(groups[g][0], km, "n")
			var tg: int = _group_of(km, first_res)
			targets.append(tg)
			if first_res != SPEC_GROUPS[km][tg][0]:
				lane_bad.append("그룹%d 결과 레인%d가 목표 그룹 %d의 첫 레인이 아님" % [g, first_res, tg])
			for lane in groups[g]:
				if nr.remap_lane(lane, km, "q") != first_res:
					lane_bad.append("그룹%d 안 레인%d가 다른 곳으로 감" % [g, lane])
			if nr.remap_lane(lane_of_layer(groups[g][0]), km, "z") != first_res:
				lane_bad.append("레인믹스 레이어(16+) 레인이 기본 레이어와 다르게 섞임")
		var sorted_t := targets.duplicate()
		sorted_t.sort()
		check("RANDOM: %d키는 그룹을 1:1로 섞음(모든 그룹이 서로 다른 그룹으로, 빠짐·겹침 없음)" % km, sorted_t == range(groups.size()), "결과 %s" % str(targets))
		check("RANDOM: %d키는 같은 그룹의 레인이 모두 같은 곳으로 가고 결과는 목표 그룹의 첫 레인" % km, lane_bad.is_empty(), "; ".join(lane_bad.slice(0, 3)))
		var nr2 := NoteRandomizer.new()
		nr2.build([], NoteRandomizer.Mode.RANDOM, 4242)
		var same := true
		for lane in 16:
			if nr.remap_lane(lane, km, "a") != nr2.remap_lane(lane, km, "b"):
				same = false
		check("RANDOM: %d키는 같은 시드면 같은 섞기(재현 가능)이고 노트 키가 달라도 곡 전체 고정" % km, same)
	var distinct := {}
	for s in 30:
		var n3 := NoteRandomizer.new()
		n3.build([], NoteRandomizer.Mode.RANDOM, s)
		var key := []
		for lane in 8:
			key.append(n3.remap_lane(lane, 8, "k"))
		distinct[str(key)] = true
	check("RANDOM: 시드가 다르면 섞기도 달라진다(8키, 시드 30개에서 서로 다른 섞기 %d종)" % distinct.size(), distinct.size() >= 5)


func lane_of_layer(lane: int) -> int:
	return lane + 16   # 레인믹스 레이어 레인(L16~31)은 물리 위치가 lane-16


func _randomizer_s_random() -> void:
	var free_score: Array = []
	for lane in 16:
		free_score.append({"type": "tap", "lane": lane, "timing_ms": 1500.0, "length_ms": 0.0})
	var seed_a := NoteRandomizer.new()
	seed_a.build(free_score, NoteRandomizer.Mode.S_RANDOM, 7)
	var seed_b := NoteRandomizer.new()
	seed_b.build(free_score, NoteRandomizer.Mode.S_RANDOM, 7)
	var valid := true
	var stable := true
	var reproducible := true
	for km in MODES:
		for lane in 16:
			var key := "%d_%.1f" % [lane, 1500.0]
			var r1: int = seed_a.remap_lane(lane, km, key)
			if _group_of(km, r1) < 0 or r1 != SPEC_GROUPS[km][_group_of(km, r1)][0]:
				valid = false
			if seed_a.remap_lane(lane, km, key) != r1:
				stable = false
			if seed_b.remap_lane(lane, km, key) != r1:
				reproducible = false
	check("S-RANDOM: 모든 키모드·레인에서 결과는 유효한 그룹의 첫 레인", valid)
	check("S-RANDOM: 같은 노트는 몇 번을 물어도 같은 결과(노트별 캐시)", stable)
	check("S-RANDOM: 같은 시드면 모든 노트가 같은 결과(재현 가능)", reproducible)
	var unknown := seed_a.remap_lane(3, 4, "없는키")
	eq("S-RANDOM: 모르는 노트 키는 레인 그대로", unknown, 3)

	# 드래그 체인이 점유한 그룹 회피 (DESIGN §7): 체인 웨이포인트 lane 0 @1000, lane 4 @2000
	var chain_score: Array = [
		{"type": "drag", "lane": 0, "timing_ms": 1000.0, "chain_id": 1},
		{"type": "drag", "lane": 4, "timing_ms": 2000.0, "chain_id": 1},
	]
	for lane in 16:
		chain_score.append({"type": "tap", "lane": lane, "timing_ms": 1500.0, "length_ms": 0.0})
		chain_score.append({"type": "tap", "lane": lane, "timing_ms": 2000.0, "length_ms": 0.0})   # 체인 끝 시각 정확히
		chain_score.append({"type": "long", "lane": lane, "timing_ms": 500.0, "length_ms": 600.0})   # 롱이 체인 시작에 걸침
	var bad4 := 0
	var bad8 := 0
	var total := 0
	for seed_value in [1, 2, 3, 4, 5]:
		var nr := NoteRandomizer.new()
		nr.build(chain_score, NoteRandomizer.Mode.S_RANDOM, seed_value)
		for lane in 16:
			for spec in [[1500.0, 0.0], [2000.0, 0.0], [500.0, 600.0]]:
				var key := "%d_%.1f" % [lane, spec[0]]
				var g4: int = _group_of(4, nr.remap_lane(lane, 4, key))
				var g8: int = _group_of(8, nr.remap_lane(lane, 8, key))
				total += 1
				if g4 in [0, 1]:
					bad4 += 1
				if g8 in [0, 2]:
					bad8 += 1
	check("S-RANDOM: 드래그 체인이 쓰는 4키 그룹(0·1)에는 시간이 겹치는 노트를 배정하지 않음(체인 구간 안·끝 시각·롱 걸침, %d건)" % total, bad4 == 0, "어긴 건수 %d" % bad4)
	check("S-RANDOM: 8키에서도 체인이 쓰는 그룹(0·2)을 피함(%d건)" % total, bad8 == 0, "어긴 건수 %d" % bad8)

	# 체인이 모든 그룹을 점유하면 회피를 포기하고 아무 그룹이나 (유효한 결과, 오류 없음)
	var full_score: Array = []
	for lane in [0, 4, 8, 12]:
		full_score.append({"type": "drag", "lane": lane, "timing_ms": 1000.0 + lane, "chain_id": 9})
	full_score.append({"type": "tap", "lane": 2, "timing_ms": 1500.0, "length_ms": 0.0})
	var nf := NoteRandomizer.new()
	nf.build(full_score, NoteRandomizer.Mode.S_RANDOM, 3)
	var fr: int = nf.remap_lane(2, 4, "2_1500.0")
	check("S-RANDOM: 체인이 4키의 모든 그룹을 점유하면 회피를 포기하고 유효한 그룹을 배정", _group_of(4, fr) >= 0 and fr == SPEC_GROUPS[4][_group_of(4, fr)][0], "결과 레인 %d" % fr)
