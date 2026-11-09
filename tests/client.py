# -*- coding: utf-8 -*-
"""Godot TestServer HTTP 클라이언트 래퍼"""

import base64
import time
import urllib.request
import urllib.parse
import json

HOST = "http://127.0.0.1:5000"
DEFAULT_TIMEOUT = 5


def _req(method: str, path: str, timeout=DEFAULT_TIMEOUT) -> dict:
    req = urllib.request.Request(HOST + path, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def ping() -> bool:
    try:
        return _req("GET", "/ping").get("status") == "ok"
    except Exception:
        return False


def post_json(path: str, body: dict, timeout=DEFAULT_TIMEOUT) -> dict:
    """JSON 본문을 보내는 POST. 본문이 bytes 라서 http.client 가 헤더와 한 번에 보낸다(TestServer 는 처음 도착한 바이트만 읽는다)."""
    req = urllib.request.Request(HOST + path, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def debug_submit_score(payload: dict, timeout: float = 30.0) -> dict:
    """submit_score 엣지 함수에 payload 를 그대로 보내고 {"ok": bool, "response": ...} 를 돌려준다 (TestServer /debug_submit_score)."""
    post_json("/debug_submit_score", payload)
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _req("GET", "/debug_submit_score")
        if st.get("status") == "done":
            return json.loads(st["result"])
        time.sleep(0.3)
    raise AssertionError(f"submit_score 응답이 {timeout}초 안에 오지 않았습니다")


def screen() -> dict:
    """지금 화면에 실제로 보이는 글자 — {"scene": 씬 이름, "items": [{"kind": label|button|edit, "text": ...}]} (TestServer /screen_texts)."""
    return _req("GET", "/screen_texts")


def screen_labels() -> list:
    return [i["text"] for i in screen()["items"] if i["kind"] == "label"]


def screen_images() -> list:
    """화면에 보이는 그림(TextureRect) 중 파일 경로가 있는 것의 res:// 경로 목록."""
    return [i["path"] for i in screen()["items"] if i["kind"] == "image"]


def screen_buttons() -> list:
    return [i["text"] for i in screen()["items"] if i["kind"] == "button"]


def press_text(text: str) -> bool:
    """화면에 보이는 버튼을 글자로 찾아 누른다. 그 글자의 보이는 버튼이 없으면 False."""
    return bool(_req("POST", "/screen_press?" + urllib.parse.urlencode({"text": text})).get("ok"))


def back() -> dict:
    """안드로이드 뒤로가기 키와 같은 신호를 지금 화면에 보낸다."""
    return _req("POST", "/back")


def press_nth_button(n: int) -> bool:
    """글자가 없는 아이콘 버튼용 — 화면에 보이는 버튼 중 n번째(트리 순서)를 누른다."""
    return bool(_req("POST", f"/screen_press_nth?n={n}").get("ok"))


def click(x: float, y: float, no_release: bool = False, release_only: bool = False) -> dict:
    """화면 좌표에 터치를 보낸다. no_release=True 면 누르기만, release_only=True 면 떼기만(스와이프 끝점). 응답에 화면 크기(viewport_w/h)."""
    q = f"/debug_click?x={x}&y={y}&touch=1&no_release={int(no_release)}&release_only={int(release_only)}"
    return _req("POST", q)


def viewport() -> tuple:
    r = click(-5, -5)                                    # 화면 밖 좌표라 아무 데도 닿지 않는다
    return r["viewport_w"], r["viewport_h"]


def fill_input(text: str) -> bool:
    """화면에 보이는 입력창에 글자를 채운다."""
    return bool(_req("POST", "/screen_input?" + urllib.parse.urlencode({"text": text})).get("ok"))


def select_tab(title: str) -> bool:
    """화면에 보이는 탭 묶음에서 제목이 같은 탭으로 옮긴다."""
    return bool(_req("POST", "/screen_tab?" + urllib.parse.urlencode({"text": title})).get("ok"))


def set_slider(n: int, value: float) -> dict:
    """화면에 보이는 n번째 슬라이더의 값을 바꾼다 (value_changed 가 나간다)."""
    return _req("POST", "/screen_slider?" + urllib.parse.urlencode({"n": n, "value": value}))


def tabs() -> list:
    """화면에 보이는 탭 제목 목록 [(제목, 선택됨)]."""
    return [(i["text"], i["selected"]) for i in screen()["items"] if i["kind"] == "tab"]


def sliders() -> list:
    return [i["value"] for i in screen()["items"] if i["kind"] == "slider"]


def slider_alphas() -> list:
    """슬라이더별 실제 투명도(조상까지 곱함) — 접힌 줄은 0."""
    return [i["alpha"] for i in screen()["items"] if i["kind"] == "slider"]


def pick_option(n: int, item: str = "") -> dict:
    """화면에 보이는 n번째 드롭다운에서 항목 글자를 고른다. item 이 비면 항목 목록·현재 값만 돌려준다 ({"ok","count","items","selected"})."""
    return _req("POST", "/screen_option?" + urllib.parse.urlencode({"n": n, "item": item}))


def service(op: str, timeout: float = 30.0, **params) -> dict:
    """라이벌·리더보드 서비스 함수를 게임 안에서 호출한다 (TestServer /debug_service). op 와 인자는 TestServer.gd 의 설명 참고. 결과 dict 를 돌려준다."""
    qs = urllib.parse.urlencode({"op": op, **params})
    _req("POST", f"/debug_service?{qs}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _req("GET", "/debug_service")
        if st.get("status") == "done":
            return json.loads(st["result"])
        time.sleep(0.3)
    raise AssertionError(f"서비스 호출 {op} 응답이 {timeout}초 안에 오지 않았습니다")


def clear_server_records() -> bool:
    """현재 로그인한 계정의 서버 기록(records·sequences)을 모두 지운다 (본인 행만 — RLS). 고정 테스트 계정 전용."""
    return bool(_req("POST", "/debug_clear_server_records").get("ok"))


def supabase_session(wait: float = 0.0) -> dict:
    """게임의 서버 세션 상태. wait>0 이면 session_ready 가 될 때까지(또는 --no-server 로 막힐 때까지) 기다린다."""
    deadline = time.time() + wait
    while True:
        s = _req("GET", "/supabase_session")
        if s.get("session_ready") or s.get("last_auth_error") == "no-server" or time.time() >= deadline:
            return s
        time.sleep(0.5)


def debug_login(account: int, timeout: float = 20.0) -> dict:
    """고정 테스트 계정 N(debug_test_account{N}.local.json)으로 로그인한다. 성공하면 세션 상태를 돌려주고 실패하면 AssertionError."""
    _req("POST", f"/supabase_debug_login?account={account}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = _req("GET", "/supabase_debug_login")
        if st.get("status") == "success":
            return supabase_session()
        if st.get("status") == "error":
            raise AssertionError(f"테스트 계정 {account} 로그인 실패: {st.get('result')}")
        time.sleep(0.5)
    raise AssertionError(f"테스트 계정 {account} 로그인이 {timeout}초 안에 끝나지 않았습니다")


def scene() -> str:
    return _req("GET", "/scene").get("scene", "")


def game_state() -> dict:
    return _req("GET", "/game_state")


def result() -> dict:
    return _req("GET", "/result")


def best(song_id: str, difficulty: str, platform: str = "android") -> dict:
    qs = urllib.parse.urlencode({"song_id": song_id, "difficulty": difficulty, "platform": platform})
    return _req("GET", f"/best?{qs}")


def navigate(target: str) -> dict:
    return _req("POST", f"/navigate/{target}")


def tap(action: str) -> dict:
    return _req("POST", f"/tap/{action}")


def judge_note(offset_ms: float, press: bool = True) -> dict:
    """플레이 중 다음 단노트 하나를 골라 '노트 시각 + offset_ms' 에 그 레인을 터치한다(곡 시계 기준). press=False 면 안 치고 지나가게 둔다(Miss)."""
    return _req("POST", f"/debug_judge_note?offset_ms={offset_ms}&press={int(press)}")


def judge_note_state() -> dict:
    """judge_note 의 진행 상태 {state: waiting|armed|done, grade, error_ms, lane, note_ms}."""
    return _req("GET", "/debug_judge_note")


def play_state() -> dict:
    """플레이 중 점수 상태 {ex, max_ex, judged(지금까지 판정된 노트 수), target_accuracy(0~1, 목표 없으면 0), ghost_active}."""
    return _req("GET", "/debug_play_state")


def autoplay(on: bool) -> dict:
    return _req("POST", f"/autoplay/{'on' if on else 'off'}")


def autoremix(on: bool) -> dict:
    return _req("POST", f"/autoremix/{'on' if on else 'off'}")


# ── MainMenu ──────────────────────────────────────────────────────
def tap_mainmenu_play() -> dict:
    return _req("POST", "/tap/mainmenu_play")


def tap_mainmenu_settings() -> dict:
    return _req("POST", "/tap/mainmenu_settings")


def tap_mainmenu_back() -> dict:
    return _req("POST", "/tap/mainmenu_back")


def tap_mainmenu_quit() -> dict:
    return _req("POST", "/tap/mainmenu_quit")


# ── Settings ──────────────────────────────────────────────────────
def tap_settings_back() -> dict:
    return _req("POST", "/tap/settings_back")


def tap_settings_calibrate_open() -> dict:
    return _req("POST", "/tap/settings_calibrate_open")


def tap_settings_calibrate_tap() -> dict:
    return _req("POST", "/tap/settings_calibrate_tap")


def tap_settings_calibrate_retry() -> dict:
    return _req("POST", "/tap/settings_calibrate_retry")


def tap_settings_calibrate_apply() -> dict:
    return _req("POST", "/tap/settings_calibrate_apply")


def tap_settings_calibrate_close() -> dict:
    return _req("POST", "/tap/settings_calibrate_close")


# ── SongSelect ────────────────────────────────────────────────────
def tap_songselect_tab_world() -> dict:
    return _req("POST", "/tap/songselect_tab_world")


def tap_songselect_tab_my() -> dict:
    return _req("POST", "/tap/songselect_tab_my")


def tap_songselect_tab_rival() -> dict:
    return _req("POST", "/tap/songselect_tab_rival")


def tap_songselect_debug_open() -> dict:
    return _req("POST", "/tap/songselect_debug_open")


def tap_songselect_debug_close() -> dict:
    return _req("POST", "/tap/songselect_debug_close")


def tap_songselect_back() -> dict:
    return _req("POST", "/tap/songselect_back")


def songs() -> dict:
    """SongSelect 화면이 지금 렌더링한 곡 목록을 그 자리에서 라이브 조회 (캐싱 없음)."""
    return _req("GET", "/songs")


def tap_song_at(index: int) -> dict:
    return _req("POST", f"/tap/song_at?index={index}")


# ── GameScene 포즈 오버레이 ──────────────────────────────────────────
def tap_pause_toggle() -> dict:
    return _req("POST", "/tap/pause_toggle")


def tap_pause_speed_up() -> dict:
    return _req("POST", "/tap/pause_speed_up")


def tap_pause_speed_down() -> dict:
    return _req("POST", "/tap/pause_speed_down")


def pause_calibration(value: float) -> dict:
    return _req("POST", f"/pause/calibration?value={value}")


def tap_pause_quit() -> dict:
    return _req("POST", "/tap/pause_quit")


# ── GameScene 터치존 ─────────────────────────────────────────────────
def touchzone(on: bool) -> dict:
    return _req("POST", f"/touchzone/{'on' if on else 'off'}")


def screenshot(save_path: str) -> bool:
    try:
        data = _req("GET", "/screenshot", timeout=10)
        b64 = data.get("png_base64", "")
        if not b64:
            return False
        with open(save_path, "wb") as f:
            f.write(base64.b64decode(b64))
        return True
    except Exception as e:
        print(f"[screenshot] 실패: {e}")
        return False


def wait_for_scene(expected: str, timeout: float = 15.0, interval: float = 0.5) -> bool:
    """씬이 expected로 전환될 때까지 대기. 타임아웃 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if scene() == expected:
            return True
        time.sleep(interval)
    return False


def tap_until_scene(action: str, expected: str, timeout: float = 15.0, interval: float = 1.5) -> bool:
    """action을 탭하고 expected 씬으로 바뀔 때까지 interval마다 다시 탭한다. 타임아웃 시 False.

    ResultScreen처럼 씬 이름이 먼저 보고된 뒤 버튼 연결이 늦게 끝나는 화면에서는 첫 탭이
    버려진다(2026-11-07 실측: 결과 화면 등장 직후 탭이 무시되고 약 2초 뒤 재탭에서 동작).
    같은 화면 이동 탭은 여러 번 보내도 결과가 같아서 재탭해도 안전하다."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        tap(action)
        if wait_for_scene(expected, timeout=interval):
            return True
    return False


def wait_for_shutdown(timeout: float = 15.0, interval: float = 0.5) -> bool:
    """QUIT 이후 서버가 응답을 멈출 때까지(=프로세스 정상 종료) 대기. 타임아웃 시 False."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not ping():
            return True
        time.sleep(interval)
    return False


def wait_game_finished(interval: float = 1.0) -> None:
    """/game_state가 finished=true 될 때까지 타임아웃 없이 폴링."""
    while True:
        try:
            if game_state().get("finished") is True:
                return
        except Exception:
            pass
        time.sleep(interval)
