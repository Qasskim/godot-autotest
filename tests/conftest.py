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
    global _wb, _ws
    _wb, _ws = init_workbook()


def pytest_sessionfinish(session, exitstatus):
    finalize(_wb)


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
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = item.nodeid.replace("/", "_").replace("::", "_").replace("?", "_")
        candidate = os.path.join(REPORTS_DIR, f"FAIL_{safe_name}_{ts}.png")
        if client.screenshot(candidate):
            screenshot_path = candidate
            note = f"{note}\n[스크린샷] {screenshot_path}"

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


@pytest.fixture(scope="session", autouse=True)
def require_server():
    for _ in range(10):
        if client.ping():
            return
        time.sleep(1)
    pytest.skip("Godot TestServer에 연결할 수 없습니다 (포트 5000). 게임을 먼저 실행하세요.")


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
