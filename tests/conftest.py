# -*- coding: utf-8 -*-
import os
import time
import pytest
import client
from result_writer import init_workbook, record, finalize

SONG_ID    = "sample"
DIFFICULTY = "normal"
PLATFORM   = "android"

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

_wb = None
_ws = None
_case_num = 0


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: 게임 플레이 대기가 필요한 느린 테스트")
    config.addinivalue_line("markers", "no_server: TestServer(게임 실행) 없이 도는 테스트 — 서버 연결 확인과 실패 스크린샷을 건너뜀")
    config.addinivalue_line("markers", "server: 개발 서버(Supabase)에 그대로 접속하는 테스트 — 게임을 --no-server 없이 띄운다. 만든 계정은 server_ledger.jsonl 에 적힌다")
    global _wb, _ws
    _wb, _ws = init_workbook()


def pytest_collection_modifyitems(config, items):
    """서버 테스트를 맨 뒤로 보낸다 — 게임을 --no-server 로 먼저 쓰고, 서버 모드로는 한 번만 바꿔 띄우기 위해."""
    items.sort(key=lambda it: 1 if it.get_closest_marker("server") else 0)


def pytest_sessionfinish(session, exitstatus):
    finalize(_wb)
    if _game_proc is not None:
        from godot_runner import stop_game
        stop_game(_game_proc)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" and not (report.when == "setup" and report.outcome != "passed"):
        return
    global _case_num
    _case_num += 1
    if report.passed:
        result = "PASS"
    elif report.skipped:
        result = "SKIP"
    else:
        result = "FAIL"

    note = ""
    screenshot_path = None
    if result == "FAIL":
        note = str(report.longrepr)[:300]
        if not item.get_closest_marker("no_server"):
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_name = item.nodeid.replace("/", "_").replace("::", "_").replace("?", "_")
            candidate = os.path.join(REPORTS_DIR, f"FAIL_{safe_name}_{ts}.png")
            if client.screenshot(candidate):
                screenshot_path = candidate
                note = f"{note}\n[스크린샷] {screenshot_path}"
    elif result == "SKIP":
        note = str(getattr(report, "wasxfail", "") or "")[:300]

    record(_wb, _ws, _case_num, item.nodeid, result, note, screenshot_path)


def record_case(case_name: str, passed: bool, note: str = "") -> None:
    """test_full_scenario.py처럼 한 테스트 함수 안에서 세부 항목별로 직접 행을 남길 때 사용."""
    global _case_num
    _case_num += 1
    result = "PASS" if passed else "FAIL"
    screenshot_path = None
    if not passed:
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = case_name.replace("/", "_").replace(" ", "_").replace("?", "_")[:80]
        candidate = os.path.join(REPORTS_DIR, f"FAIL_{safe_name}_{ts}.png")
        if client.screenshot(candidate):
            screenshot_path = candidate
            note = f"{note}\n[스크린샷] {screenshot_path}" if note else f"[스크린샷] {screenshot_path}"
    record(_wb, _ws, _case_num, case_name, result, note, screenshot_path)


def record_na(case_name: str, note: str) -> None:
    """법칙 2: 재현 불가능한 예외 케이스, 미구현 기능 등을 N/A로 남길 때 사용."""
    global _case_num
    _case_num += 1
    record(_wb, _ws, _case_num, case_name, "N/A", note)


_server_ok = None  # None=아직 확인 안 함, True/False=세션 안에서 한 번 확인한 결과
_game_proc = None  # 이 세션이 직접 띄운 게임(없으면 None) — 세션이 끝나면 종료한다
_game_server_mode = False  # 직접 띄운 게임이 서버 모드(--no-server 없음)인지


def _switch_game(allow_server: bool) -> None:
    """직접 띄운 게임을 종료하고 다른 모드로 다시 띄운다. 포트 5000이 비기를 기다린다."""
    global _game_proc, _game_server_mode
    from godot_runner import start_game, stop_game
    stop_game(_game_proc)
    for _ in range(20):
        if not client.ping():
            break
        time.sleep(0.5)
    _game_proc = start_game(allow_server=allow_server)
    _game_server_mode = allow_server


def _ensure_game(wants_server: bool) -> bool:
    """게임이 떠 있게 한다(세션에서 처음 한 번만 확인). 떠 있는 게임이 있으면 쓰고, 없으면 PC에서 직접 띄운다. 쓸 게임이 있으면 True."""
    global _server_ok, _game_proc, _game_server_mode
    if _server_ok is None:
        _server_ok = False
        for _ in range(10):                       # 이미 떠 있는 게임(폰 adb 포워딩 등)이 있으면 그것을 쓴다
            if client.ping():
                _server_ok = True
                break
            time.sleep(1)
        if not _server_ok and os.environ.get("AUTOTEST_AUTOLAUNCH", "1") != "0":
            # 없으면 PC에서 직접 띄운다. start_game 은 기본으로 --no-server 로 띄워 개발 서버에 계정·기록을 만들지 않는다(2026-11-07 사고).
            try:
                from godot_runner import start_game
                _game_proc = start_game(allow_server=wants_server)
                _game_server_mode = wants_server
                _server_ok = True
            except Exception as e:
                print(f"\n[conftest] 게임을 직접 띄우지 못했습니다: {e}")
    return bool(_server_ok)


@pytest.fixture(scope="session", autouse=True)
def game_for_session(request):
    """세션 시작 때 게임을 먼저 띄운다. 모듈 범위 fixture(예: test_autoplay 의 결과 fixture)가 테스트별 fixture(require_server)보다 먼저 만들어지기 때문에,
    파일 실행 순서가 달라지면 게임이 없는 채로 fixture가 접속해 오류가 났다(2026-11-08 run_all 의 integration 단계에서 발견)."""
    first = next((it for it in request.session.items if not it.get_closest_marker("no_server")), None)
    if first is not None:
        _ensure_game(bool(first.get_closest_marker("server")))


@pytest.fixture(autouse=True)
def require_server(request):
    if request.node.get_closest_marker("no_server"):
        return
    wants_server = bool(request.node.get_closest_marker("server"))
    if _server_ok and wants_server != _game_server_mode:
        if _game_proc is None:
            pytest.skip("이미 떠 있는 게임(폰 등)은 서버 접속 여부를 바꿀 수 없어 서버 테스트를 건너뜁니다")
        _switch_game(wants_server)
    if _ensure_game(wants_server):
        return
    pytest.skip("Godot TestServer에 연결할 수 없습니다 (포트 5000). 게임을 먼저 실행하거나 AUTOTEST_AUTOLAUNCH=1(기본)로 두세요.")


def play_one_round() -> dict:
    """오토플레이로 한 판 플레이하고 result 반환. 게임 종료를 game_state로 감지."""
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15), "SongSelect 전환 실패"
    client.autoplay(True)
    client.tap("first_song")
    client.tap("play")
    assert client.wait_for_scene("GameScene", timeout=15), "GameScene 전환 실패"
    client.wait_game_finished()
    assert client.wait_for_scene("ResultScreen", timeout=15), "ResultScreen 전환 실패"
    res = client.result()
    client.autoplay(False)
    return res
