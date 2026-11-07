# -*- coding: utf-8 -*-
"""--no-server 스위치 회귀 테스트 — 자동화가 게임을 띄워도 서버에 접속하지 않는다.

2026-11-07 사고: 게임을 그냥 띄웠더니 SupabaseHTTP._ready()가 개발 서버에 익명 계정을 만들었다.
godot_runner.start_game()은 항상 --no-server를 붙여 게임을 띄우고, 이 테스트가 그 효과를 확인한다.
(게임을 직접 띄우고 포트 5000을 쓰므로 이미 떠 있는 게임이 있으면 중단한다.)
"""
import json
import os
import subprocess
import time
import urllib.request

import pytest
from godot_runner import GAME_APPDATA_DIR, start_game, stop_game

pytestmark = pytest.mark.no_server   # 기존 서버 연결 확인 fixture를 건너뜀(이 파일이 게임을 직접 띄움)


def _get(path: str, method: str = "GET") -> dict:
    req = urllib.request.Request("http://127.0.0.1:5000" + path, method=method)
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


@pytest.fixture(scope="module")
def game():
    proc = start_game()
    time.sleep(10)   # 시작 시 오토로드가 서버에 붙으려는 시도가 끝날 시간을 준다
    yield proc
    stop_game(proc)


def test_game_runs_with_test_server(game):
    assert _get("/ping").get("status") == "ok"


def test_no_session_file_created(game):
    path = os.path.join(GAME_APPDATA_DIR, "RhythmGame_New", "supabase_session.json")
    assert not os.path.exists(path), "익명 로그인 세션 파일이 생겼습니다 — 서버에 접속한 것입니다"


def test_server_calls_are_blocked(game):
    _get("/supabase_test", "POST")
    result = {}
    for _ in range(10):
        time.sleep(1)
        result = _get("/supabase_test")
        if result.get("status") != "running":
            break
    assert result.get("status") == "error" and "--no-server" in result.get("result", ""), f"서버 호출이 차단되지 않았습니다: {result}"


def test_no_external_tcp_connections(game):
    ps = (
        f"$ids=@({game.pid})+@(Get-CimInstance Win32_Process|Where-Object{{$_.ParentProcessId -eq {game.pid}}}|ForEach-Object{{$_.ProcessId}});"
        "$c=Get-NetTCPConnection -ErrorAction SilentlyContinue|Where-Object{$ids -contains $_.OwningProcess -and $_.RemoteAddress -notin '127.0.0.1','::1','0.0.0.0','::'};"
        "@($c).Count"
    )
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip()
    assert out == "0", f"게임 프로세스에 외부 TCP 연결이 {out}개 있습니다"
