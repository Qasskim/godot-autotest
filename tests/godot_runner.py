# -*- coding: utf-8 -*-
"""Godot 헤드리스 단위 테스트 실행기 래퍼.

godot_unit/run_unit.gd 를 `--headless --script` 로 돌려서 모듈 하나의 결과(@@UNIT@@ 줄)를 읽어 온다.
게임 창도 TestServer도 필요 없다. 사용자 폴더(%APPDATA%\\RhythmGame_New)를 건드리지 않도록
게임 프로세스에만 APPDATA를 자동화 저장소 안의 격리 폴더로 바꿔 준다.
"""
import json
import os
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIT_DIR = os.path.join(REPO_ROOT, "godot_unit")

# 이 PC의 기본 위치. 다른 PC에서는 환경변수로 바꾼다.
GODOT_EXE = os.environ.get(
    "GODOT_EXE", r"D:\Godot_v4.7.2-stable_win64.exe\Godot_v4.7.2-stable_win64_console.exe")
GAME_PROJECT = os.environ.get("GAME_PROJECT", r"D:\Godot\RhythmGame_New\Godot")
APPDATA_DIR = os.environ.get(
    "AUTOTEST_APPDATA", os.path.join(REPO_ROOT, "tests", "reports", "_appdata"))

MARK = "@@UNIT@@ "
GAME_APPDATA_DIR = os.path.join(REPO_ROOT, "tests", "reports", "_appdata_game")


def start_game(timeout: int = 90) -> "subprocess.Popen":
    """게임을 PC에서 띄운다. **항상 --no-server를 붙이고, 끄는 옵션은 두지 않는다**(2026-11-07).
    그냥 띄우면 게임이 개발 서버에 익명 계정을 만든다(SupabaseHTTP._ready → ensure_session). 사용자 폴더도 건드리지 않게
    APPDATA를 격리 폴더로 바꿔 준다. TestServer(포트 5000)가 응답할 때까지 기다렸다가 프로세스를 돌려준다."""
    import time
    import urllib.request
    os.makedirs(GAME_APPDATA_DIR, exist_ok=True)

    def _ping() -> bool:
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/ping", timeout=2) as r:
                return b"ok" in r.read()
        except Exception:
            return False

    if _ping():
        raise RuntimeError("포트 5000에 이미 다른 게임이 떠 있습니다 — 그 게임을 시험 대상으로 착각하지 않도록 중단합니다.")
    env = dict(os.environ, APPDATA=GAME_APPDATA_DIR)
    cmd = [GODOT_EXE, "--path", GAME_PROJECT, "--windowed", "--resolution", "1920x864", "--position", "0,0", "--", "--no-server"]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"게임이 시작 직후 종료됐습니다(종료코드 {proc.returncode})")
        if _ping():
            return proc
        time.sleep(1)
    stop_game(proc)
    raise RuntimeError(f"게임의 TestServer가 {timeout}초 안에 응답하지 않았습니다")


def stop_game(proc) -> None:
    """start_game으로 띄운 프로세스 트리만 종료한다(다른 Godot 프로세스는 건드리지 않음)."""
    if proc is None or proc.poll() is not None:
        return
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def run_unit_module(module: str, timeout: int = 180) -> list:
    """모듈 이름(unit_<module>.gd)을 실행해 [{name, pass, detail}, ...] 를 돌려준다.
    결과가 하나도 없으면(스크립트 오류 등) RuntimeError — 조용히 0건으로 통과시키지 않는다."""
    os.makedirs(APPDATA_DIR, exist_ok=True)
    env = dict(os.environ, APPDATA=APPDATA_DIR)
    cmd = [GODOT_EXE, "--headless", "--path", GAME_PROJECT,
           "--script", os.path.join(UNIT_DIR, "run_unit.gd"), "--", f"module={module}",
           "--no-server"]   # 모듈이 오류로 멈춰 프레임이 돌면 오토로드 _ready가 서버에 익명 계정을 만든다(2026-11-08 사고) — 항상 차단
    proc = subprocess.run(cmd, capture_output=True, env=env, timeout=timeout)
    out = proc.stdout.decode("utf-8", errors="replace")
    err = proc.stderr.decode("utf-8", errors="replace")
    results = []
    for line in out.splitlines():
        if line.startswith(MARK):
            results.append(json.loads(line[len(MARK):]))
    if not results:
        tail = "\n".join((out + "\n" + err).strip().splitlines()[-15:])
        raise RuntimeError(f"단위 테스트 모듈 '{module}' 결과가 없습니다 (종료코드 {proc.returncode}):\n{tail}")
    return results
