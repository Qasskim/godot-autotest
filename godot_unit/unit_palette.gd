extends RefCounted
# 모듈 16 — 비주얼 테마(팔레트 .tres 3개) 데이터 (기준: Godot/docs/DESIGN.md §11 판정 이펙트·비주얼 컨셉 시스템, §13-3 도트 팔레트 30색, §5 마크 8종, 2026-11-10)
#   - 테마 3개(astral_ocean·cosmic_neon·abyss_ether): PaletteManager 경로·파일이 가리키는 팔레트의 theme_id 가 맞음, 표시 이름이 있고 서로 다름
#   - 키빔 모드가 테마마다 다름(sine_wobble·hard_flicker·aurora_cycle, DESIGN §11)
#   - 판정 이펙트 5등급(Wow·Great·Good·Oops·Miss)이 모두 채워져 있고 연출 종류가 허용 목록 안이며, Wow > Great > Good 으로 규모(연출 길이·입자 수)가 줄어든다(DESIGN §11, Wow·Great·Good 은 같은 종류일 수 있음)
#   - 노트 색: 키모드별 그룹 순서 흰(W)/파랑(B) — 4키 WBBW, 5키 WBWBW, 6키 WBWWBW, 8키 WBWBBWBW, 16키 WBWBWBWBBWBWBWBW (DESIGN §11, 2026-09-30 사용자 지정)
#   - 마크 배경/글자색 8종, 등급·게이지 색 조회 함수, 투명도 있는 색의 투명도
#   (astral_ocean 의 30색 검사는 파일에 직접 적힌 색만 봐야 해서 test_data_palette.py 가 한다 — 안 적힌 필드는 기본값을 물려받는다, DESIGN §11)
# 기대값은 DESIGN.md 문장을 그대로 옮긴 것이다. 서버는 쓰지 않는다.

const THEMES := ["astral_ocean", "cosmic_neon", "abyss_ether"]
const KEYBEAM_MODES := ["sine_wobble", "hard_flicker", "aurora_cycle"]
const TIER_MOTIONS := ["none", "shudder", "crack", "hard_flicker", "reverse_cutout", "hard_cut_off", "double_ripple", "ripple_single", "inward_ripple", "quiet_fade"]   # DESIGN §11 / JudgmentTierConfig 주석
const GRADES := ["Wow", "Great", "Good", "Oops", "Miss"]
const MARKS := ["perfect", "allcombo", "allgood", "clear", "failed", "straight", "luckyroulette", "evil"]   # DESIGN §5
const NOTE_PATTERN := {4: "WBBW", 5: "WBWBW", 6: "WBWWBW", 8: "WBWBBWBW", 16: "WBWBWBWBBWBWBWBW"}

var needs_frames := true
var results: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	pass


func palette(id: String) -> GameplayPalette:
	return load("res://resources/palette/palette_%s.tres" % id) as GameplayPalette


# 팔레트가 가진 모든 색(속성 + 딕셔너리 값 + 하위 리소스의 속성)을 {이름: Color} 로 모은다.
func all_colors(res: Resource, prefix: String = "") -> Dictionary:
	var out := {}
	for p in res.get_property_list():
		if not (p.usage & PROPERTY_USAGE_SCRIPT_VARIABLE):
			continue
		var v = res.get(p.name)
		var key: String = prefix + str(p.name)
		if v is Color:
			out[key] = v
		elif v is Dictionary:
			for k in v:
				if v[k] is Color:
					out["%s[%s]" % [key, str(k)]] = v[k]
		elif v is Resource:
			out.merge(all_colors(v, key + "."))
	return out


func run() -> Array:
	var seen_names := {}
	var seen_beams := []
	for id in THEMES:
		var pal := palette(id)
		check("%s: 팔레트 파일을 GameplayPalette 로 읽음" % id, pal != null)
		if pal == null:
			continue
		eq("%s: PaletteManager 경로가 그 파일을 가리킴" % id, PaletteManager.PALETTE_PATHS.get(id, ""), "res://resources/palette/palette_%s.tres" % id)
		eq("%s: 파일 안의 theme_id 가 파일 이름과 같음" % id, pal.theme_id, id)
		check("%s: 표시 이름이 있음" % id, pal.theme_name != "")
		check("%s: 표시 이름이 다른 테마와 겹치지 않음" % id, not seen_names.has(pal.theme_name), pal.theme_name)
		seen_names[pal.theme_name] = true
		seen_beams.append(pal.keybeam_mode)

		# ── 판정 이펙트 5등급 ──
		var motions := []
		for g in GRADES:
			var tier := pal.get_tier(g)
			check("%s: %s 연출 설정이 채워져 있음" % [id, g], tier != null and pal.get("judge_" + g.to_lower()) == tier)
			if tier == null:
				continue
			check("%s: %s 연출 종류가 허용 목록 안(%s)" % [id, g, tier.motion_type], TIER_MOTIONS.has(tier.motion_type))
			check("%s: %s 연출 길이·입자 수·퍼짐 각도가 정상 범위" % [id, g], tier.effect_dur_ms > 0.0 and tier.particle_count >= 0 and tier.spawn_cone_deg > 0.0 and tier.spawn_cone_deg <= 360.0 and tier.particle_life_ms > 0.0,
				"dur=%s count=%s cone=%s life=%s" % [tier.effect_dur_ms, tier.particle_count, tier.spawn_cone_deg, tier.particle_life_ms])
			motions.append(tier.motion_type)
		# 연출 규모 순서(DESIGN §11, 2026-11-10 사용자 지시로 지금 구현에 맞춤): Great·Good 은 Wow 와 같은 구조의 규모 축소판 — 연출 길이는 Wow > Great > Good 으로 엄격히 줄고 입자 수는 같거나 줄어든다.
		var w := pal.judge_wow
		var gr := pal.judge_great
		var go := pal.judge_good
		check("%s: 연출 길이가 Wow > Great > Good 으로 줄어듦" % id, w.effect_dur_ms > gr.effect_dur_ms and gr.effect_dur_ms > go.effect_dur_ms, "%s > %s > %s" % [w.effect_dur_ms, gr.effect_dur_ms, go.effect_dur_ms])
		check("%s: 입자 수가 Wow ≥ Great ≥ Good" % id, w.particle_count >= gr.particle_count and gr.particle_count >= go.particle_count, "%s, %s, %s" % [w.particle_count, gr.particle_count, go.particle_count])
		eq("%s: 알 수 없는 등급 이름은 Good 연출로 대신함" % id, pal.get_tier("???"), pal.judge_good)

		# ── 노트 색 흰/파랑 순서 ──
		for km in NOTE_PATTERN:
			var groups: Array = LaneSystem.KEY_MODE_MAP[km]
			var want: String = NOTE_PATTERN[km]
			var ok := groups.size() == want.length()
			var bad := []
			for i in groups.size():
				for lane in groups[i]:
					var c := pal.get_lane_color(lane, km)
					var expect := pal.note_1p_odd if want[i] == "W" else pal.note_1p_even
					if c != expect:
						ok = false
						bad.append("%d키 레인%d" % [km, lane])
			check("%s: %d키 노트 색 순서가 %s" % [id, km, want], ok, "어긋난 곳 %s / 그룹 수 %d" % [str(bad.slice(0, 4)), groups.size()])
		check("%s: 흰(note_1p_odd)과 파랑(note_1p_even)이 서로 다른 색" % id, pal.note_1p_odd != pal.note_1p_even)
		check("%s: 흰 노트 색이 파랑 노트 색보다 밝음" % id, pal.note_1p_odd.get_luminance() > pal.note_1p_even.get_luminance(),
			"흰 %.3f / 파랑 %.3f" % [pal.note_1p_odd.get_luminance(), pal.note_1p_even.get_luminance()])

		# ── 마크·등급·게이지 ──
		eq("%s: 마크 배경색 키 8종" % id, pal.mark_bg.keys().size() == MARKS.size() and MARKS.all(func(m): return pal.mark_bg.has(m)), true)
		eq("%s: 마크 글자색 키 8종" % id, pal.mark_fg.keys().size() == MARKS.size() and MARKS.all(func(m): return pal.mark_fg.has(m)), true)
		var grade_cols := []
		for g in GRADES:
			grade_cols.append(pal.get_grade_color(g))
		eq("%s: 등급 5색 조회가 grade_* 필드와 같음" % id, grade_cols, [pal.grade_wow, pal.grade_great, pal.grade_good, pal.grade_oops, pal.grade_miss])
		var uniq_grade := {}
		for c in grade_cols:
			uniq_grade[c.to_html()] = true
		check("%s: 등급 5색이 모두 서로 다름" % id, uniq_grade.size() == 5)
		var zones := ["Expert", "Hard", "Normal", "Easy", "GameOver"]
		var zone_cols := []
		for z in zones:
			zone_cols.append(pal.get_gauge_color(z))
		eq("%s: 게이지 5구간 색 조회가 gauge_* 필드와 같음" % id, zone_cols, [pal.gauge_expert, pal.gauge_hard, pal.gauge_normal, pal.gauge_easy, pal.gauge_gameover])
		var uniq_zone := {}
		for c in zone_cols:
			uniq_zone[c.to_html()] = true
		check("%s: 게이지 5구간 색이 모두 서로 다름" % id, uniq_zone.size() == 5)
		eq("%s: 알 수 없는 등급·구간 이름은 light 색" % id, [pal.get_grade_color("???"), pal.get_gauge_color("???")], [pal.light, pal.light])
		eq("%s: shade_a/light_a 는 색을 유지하고 투명도만 바꿈" % id, [pal.shade_a(0.25), pal.light_a(0.5)], [Color(pal.shade, 0.25), Color(pal.light, 0.5)])

		# ── 투명하면 안 되는 색 ──
		var cols := all_colors(pal)
		var seethrough := []
		for k in cols:
			if (k.begins_with("grade_") or k.begins_with("gauge_") or k.begins_with("note_") or k.begins_with("mark_")) and cols[k].a < 1.0:
				seethrough.append(k)
		check("%s: 등급·게이지·노트·마크 색은 불투명" % id, seethrough.is_empty(), str(seethrough))

	var sorted_beams := seen_beams.duplicate()
	sorted_beams.sort()
	var want_beams := KEYBEAM_MODES.duplicate()
	want_beams.sort()
	eq("키빔 모드가 테마마다 하나씩 다름(sine_wobble·hard_flicker·aurora_cycle)", sorted_beams, want_beams)
	eq("테마 선택지 목록이 3개 ID 와 같은 순서", PaletteManager.get_theme_list().map(func(t): return t.id), THEMES)
	check("PaletteManager.PALETTE_PATHS 에 테마 3개뿐", PaletteManager.PALETTE_PATHS.size() == THEMES.size(), str(PaletteManager.PALETTE_PATHS.keys()))
	eq("기본 테마는 astral_ocean", PaletteManager.DEFAULT_THEME, "astral_ocean")
	return results
