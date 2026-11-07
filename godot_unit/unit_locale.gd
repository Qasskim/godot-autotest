extends RefCounted
# 모듈 7(Godot 쪽) — 임포트된 번역이 CSV와 같은지, Locale 함수(t / tf / has / t_or) 동작
# 2026-11-05 사고: 영어 번역이 비면 엔진이 키 이름을 그대로 돌려줘 영어 타이틀에 title_subtitle이 찍혔다.
# 기대값은 strings.csv 에서 읽는다(CSV가 원본이고 임포트된 .translation 이 따라가는 구조).

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


func _read_csv() -> Array:
	var f := FileAccess.open("res://locale/strings.csv", FileAccess.READ)
	var out: Array = []
	if f == null:
		return out
	while not f.eof_reached():
		var line := f.get_csv_line()
		if line.size() >= 3:
			out.append(line)
	return out


func run() -> Array:
	var rows: Array = _read_csv()
	check("번역 CSV를 읽음(헤더 keys,ko,en 과 1줄 이상)", rows.size() > 1 and rows[0][0] == "keys" and rows[0][1] == "ko" and rows[0][2] == "en", "줄 %d" % rows.size())
	rows = rows.slice(1)
	var col := {"ko": 1, "en": 2}
	for lang in ["ko", "en"]:
		var tr: Translation = load("res://locale/strings.%s.translation" % lang)
		check("임포트된 번역 파일을 불러옴: %s" % lang, tr != null)
		if tr == null:
			continue
		var bad: Array = []
		for r in rows:
			var want: String = String(r[col[lang]]).c_unescape()   # CSV 임포터는 \n 같은 이스케이프를 풀어서 넣는다
			var got := String(tr.get_message(r[0]))
			if got != want:
				bad.append("%s: 기대 %s / 실제 %s" % [r[0], want.substr(0, 20), got.substr(0, 20)])
		check("임포트된 %s 번역 = CSV (%d개 키 모두 같은 값, 최신 상태)" % [lang, rows.size()], bad.is_empty(),
			"%d건 불일치(CSV를 고친 뒤 재임포트가 필요할 수 있음): %s" % [bad.size(), "; ".join(bad.slice(0, 3))])
		# (임포트된 번역은 압축 형식이라 get_message_list()가 키 목록을 돌려주지 않는다 — 항목 수는 셀 수 없고, 위 값 비교가 CSV의 모든 키를 확인한다)

	eq("Locale 지원 언어는 ko·en", load("res://scripts/core/Locale.gd").SUPPORTED_LANGS, ["ko", "en"])
	var loc = load("res://scripts/core/Locale.gd").new()
	_free_nodes.append(loc)
	var by_key := {}
	for r in rows:
		by_key[r[0]] = r

	loc.lang = "en"
	loc._load_translation()
	eq("Locale(en): t(mark_clear) = CSV의 영어 값", loc.t("mark_clear"), String(by_key["mark_clear"][2]).c_unescape())
	eq("Locale(en): 번역이 있는 키는 has = true", loc.has("mark_clear"), true)
	eq("Locale(en): 영어가 일부러 빈 title_subtitle 은 has = false (키 이름 노출을 막는 판단 기준)", loc.has("title_subtitle"), false)
	eq("Locale(en): 없는 키는 has = false 이고 t 는 키 이름을 그대로 돌려줌(엔진 동작)", [loc.has("zz_missing_key"), loc.t("zz_missing_key")], [false, "zz_missing_key"])
	eq("Locale(en): t_or는 번역이 있으면 그 문구", loc.t_or("mark_clear", "mark_failed"), loc.t("mark_clear"))
	eq("Locale(en): t_or는 번역이 없으면 대체 키의 문구(키 이름이 화면에 찍히지 않음)", loc.t_or("zz_missing_key", "mark_failed"), loc.t("mark_failed"))
	eq("Locale(en): t_or는 영어가 빈 키도 대체 키 문구로", loc.t_or("title_subtitle", "mark_failed"), loc.t("mark_failed"))

	var fmt_key := ""
	for r in rows:
		if String(r[2]).contains("%s") or String(r[2]).contains("%d"):
			fmt_key = r[0]
			break
	if fmt_key != "":
		var want := String(by_key[fmt_key][2]).c_unescape()
		var arg: Array = [7] if want.contains("%d") else ["abc"]
		eq("Locale(en): tf는 자리표시자에 값을 채움 (%s)" % fmt_key, loc.tf(fmt_key, arg), want % arg)

	loc.lang = "ko"
	loc._load_translation()
	eq("Locale(ko): t(mark_clear) = CSV의 한국어 값", loc.t("mark_clear"), String(by_key["mark_clear"][1]).c_unescape())
	eq("Locale(ko): 한국어 title_subtitle 은 번역이 있어 has = true", loc.has("title_subtitle"), true)
	return results
