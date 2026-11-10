extends RefCounted
# 모듈 25 — 공용 팝업 동작 (ErrorPopup·ConfirmPopup·ProtoNoticePopup, 기준 각 스크립트의 설명, DESIGN §14 에러 팝업 2026-07-04, SUPABASE_ADAPTER_SPEC §6-8 프로토타입 안내)
#   - ErrorPopup: 메시지 글자, 확인 버튼 1개, 누르면 콜백 실행·팝업 닫힘·"떠 있는 모달" 표시 해제, 물리 뒤로가기는 확인과 같음, 콜백 없이도 오류 없음
#   - ConfirmPopup: 확인/취소 두 버튼의 글자, 각자 자기 콜백만 실행, 물리 뒤로가기는 취소와 같음
#   - ProtoNoticePopup: 체크 없이 확인하면 동의가 저장되지 않고 닫힘, 체크하고 확인하면 동의가 저장됨, 물리 뒤로가기는 무시(동의 확인을 건너뛰지 못함),
#     itch 게스트 전용 빌드가 아니면 require() 가 팝업을 띄우지 않음(이 PC 실행은 해당)
# 모양은 보지 않는다(글자·버튼·동작만). 서버는 쓰지 않는다. 메시지 글자는 시험 작성자가 정했다.

const ErrorPopup := preload("res://scripts/ui/ErrorPopup.gd")
const ConfirmPopup := preload("res://scripts/ui/ConfirmPopup.gd")
const ProtoNoticePopup := preload("res://scripts/ui/ProtoNoticePopup.gd")

var needs_frames := true
var results: Array = []
var _saved_ack := false
var _nodes: Array = []


func check(name: String, ok: bool, detail: String = "") -> void:
	results.append({"name": name, "pass": ok, "detail": detail})


func eq(name: String, actual, expected) -> void:
	check(name, actual == expected, "기대 %s / 실제 %s" % [str(expected), str(actual)])


func cleanup() -> void:
	for n in _nodes:
		if is_instance_valid(n):
			n.free()
	_nodes.clear()
	UserService._profile["proto_notice_ack"] = _saved_ack
	UserService._save_profile()
	SceneManager.active_modal_popup = null


func root() -> Node:
	return Engine.get_main_loop().root


func find_all(node: Node, type: String, out: Array = []) -> Array:
	for c in node.get_children():
		if c.is_class(type):
			out.append(c)
		find_all(c, type, out)
	return out


func make_holder() -> Node:
	var n := Node.new()
	root().add_child(n)
	_nodes.append(n)
	return n


func run() -> Array:
	_saved_ack = UserService.has_ack_proto_notice()
	var holder := make_holder()
	var calls := {"ok": 0, "cancel": 0}

	# ── ErrorPopup ──
	var ep := ErrorPopup.show_popup(holder, "시험 오류 메시지", func(): calls.ok += 1)
	_nodes.append(ep)
	var labels := find_all(ep, "Label")
	var buttons := find_all(ep, "Button")
	eq("ErrorPopup: 메시지 글자가 그대로", labels.map(func(l): return l.text), ["시험 오류 메시지"])
	eq("ErrorPopup: 버튼은 확인 하나", buttons.map(func(b): return b.text), [Locale.t("settings_confirm")])
	eq("ErrorPopup: 떠 있는 모달로 등록됨", SceneManager.active_modal_popup, ep)
	buttons[0].pressed.emit()
	eq("ErrorPopup: 확인을 누르면 콜백 1번", calls.ok, 1)
	eq("ErrorPopup: 확인 뒤 모달 등록이 풀리고 닫힘 예약", [SceneManager.active_modal_popup, ep.is_queued_for_deletion()], [null, true])
	var ep2 := ErrorPopup.show_popup(holder, "뒤로가기", func(): calls.ok += 10)
	_nodes.append(ep2)
	ep2.notification(Node.NOTIFICATION_WM_GO_BACK_REQUEST)
	eq("ErrorPopup: 물리 뒤로가기는 확인과 같음(콜백 실행)", calls.ok, 11)
	var ep3 := ErrorPopup.show_popup(holder, "콜백 없음")
	_nodes.append(ep3)
	find_all(ep3, "Button")[0].pressed.emit()
	check("ErrorPopup: 콜백 없이 확인해도 오류 없음", ep3.is_queued_for_deletion())

	# ── ConfirmPopup ──
	var cp := ConfirmPopup.show_popup(holder, "계속할까요", "예", "아니오", func(): calls.ok += 100, func(): calls.cancel += 1)
	_nodes.append(cp)
	var cbuttons := find_all(cp, "Button")
	eq("ConfirmPopup: 버튼 글자(확인·취소)", cbuttons.map(func(b): return b.text), ["예", "아니오"])
	eq("ConfirmPopup: 메시지 글자", find_all(cp, "Label").map(func(l): return l.text), ["계속할까요"])
	cbuttons[0].pressed.emit()
	eq("ConfirmPopup: 확인은 확인 콜백만", [calls.ok, calls.cancel], [111, 0])
	var cp2 := ConfirmPopup.show_popup(holder, "계속할까요", "예", "아니오", func(): calls.ok += 100, func(): calls.cancel += 1)
	_nodes.append(cp2)
	find_all(cp2, "Button")[1].pressed.emit()
	eq("ConfirmPopup: 취소는 취소 콜백만", [calls.ok, calls.cancel], [111, 1])
	var cp3 := ConfirmPopup.show_popup(holder, "뒤로가기", "예", "아니오", func(): calls.ok += 100, func(): calls.cancel += 1)
	_nodes.append(cp3)
	cp3.notification(Node.NOTIFICATION_WM_GO_BACK_REQUEST)
	eq("ConfirmPopup: 물리 뒤로가기는 취소와 같음", [calls.ok, calls.cancel], [111, 2])
	eq("ConfirmPopup: 닫힌 뒤 모달 등록이 풀림", SceneManager.active_modal_popup, null)

	# ── ProtoNoticePopup ──
	eq("이 PC 실행은 itch 게스트 전용 빌드가 아님", UserService.is_guest_only_build(), false)
	var before := holder.get_child_count()
	ProtoNoticePopup.require(holder)
	eq("itch 게스트 전용 빌드가 아니면 require() 는 팝업을 띄우지 않음", holder.get_child_count(), before)

	UserService._profile["proto_notice_ack"] = false
	var pp := ProtoNoticePopup.new()
	holder.add_child(pp)
	pp._build()
	_nodes.append(pp)
	eq("안내 팝업: 체크박스 1개·확인 버튼 1개", [find_all(pp, "CheckBox").size(), find_all(pp, "Button").filter(func(b): return not (b is CheckBox)).size()], [1, 1])
	pp.notification(Node.NOTIFICATION_WM_GO_BACK_REQUEST)
	eq("안내 팝업: 물리 뒤로가기는 무시(닫히지 않음)", [pp.is_queued_for_deletion(), SceneManager.active_modal_popup], [false, pp])
	var ok_btn: Button = find_all(pp, "Button").filter(func(b): return not (b is CheckBox))[0]
	ok_btn.pressed.emit()
	eq("체크 없이 확인: 닫히지만 동의는 저장되지 않음", [pp.is_queued_for_deletion(), UserService.has_ack_proto_notice()], [true, false])

	var pp2 := ProtoNoticePopup.new()
	holder.add_child(pp2)
	pp2._build()
	_nodes.append(pp2)
	find_all(pp2, "CheckBox")[0].button_pressed = true
	find_all(pp2, "Button").filter(func(b): return not (b is CheckBox))[0].pressed.emit()
	eq("체크하고 확인: 닫히고 동의가 저장됨", [pp2.is_queued_for_deletion(), UserService.has_ack_proto_notice()], [true, true])
	eq("동의가 저장된 뒤에는 require() 가 다시 띄우지 않음(게스트 빌드 조건과 무관하게 이미 동의)", UserService.has_ack_proto_notice(), true)
	return results
