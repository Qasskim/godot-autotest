extends RefCounted
# 슬라이드 노트 (기준: Godot/docs/DESIGN.md §7 노트 종류 — slide: 방향 슬라이드(direction -1/0/+1))
# 2026-11-10 확인한 구현: SlideNoteVisual 은 모양(화살표)만 방향을 쓰고 판정은 단노트(tap)와 같은 경로다(GameManager._try_judge 의 else 분기:
# 홀드형이 아니면 judge_ms 후 제거, 만료 루프도 같은 force_miss). 방향 입력을 확인하는 판정은 없다 — 방향 판정은 쓸 예정이나 지금 안 쓰므로 구현 보류(사용자 결정, DESIGN §7). 만들 때 이 모듈을 새 기준으로 바꾼다.
# 이 모듈은 그 구현 사실(홀드형 아님, 방향 값 저장, 장면이 SlideNoteVisual 로 만들어짐)을 고정한다. 판정 경로 자체는 엔진 시험이 필요하다(수록 채보에 슬라이드가 없고 튜토리얼 1단계 한 곳뿐).

var needs_frames := true
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
	var scene: PackedScene = load("res://scenes/notes/SlideNote.tscn")
	check("슬라이드 장면 파일을 읽음", scene != null)
	if scene == null:
		return results
	var note = scene.instantiate()
	_free_nodes.append(note)
	check("장면이 SlideNoteVisual(NoteBase)로 만들어짐", note is SlideNoteVisual and note is NoteBase)
	eq("방향 기본값은 0(아무 방향)", note.direction, 0)
	for d in [-1, 0, 1]:
		note.direction = d
		eq("방향 %d 을 저장함" % d, note.direction, d)
	eq("슬라이드는 홀드형이 아님(만료 시 단노트처럼 Miss 처리)", note.is_hold_type(), false)
	var tap = load("res://scenes/notes/TapNote.tscn").instantiate()
	_free_nodes.append(tap)
	eq("단노트도 홀드형이 아님(슬라이드와 같은 경로)", tap.is_hold_type(), false)
	return results
