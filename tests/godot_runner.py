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
SERVER_APPDATA_DIR = os.path.join(REPO_ROOT, "tests", "reports", "_appdata_server")   # 서버 모드 전용 — 로그인 세션이 실행 사이에 남는다


def start_game(timeout: int = 90, allow_server: bool = False, fresh_profile: bool = False) -> "subprocess.Popen":
    """게임을 PC에서 띄운다. **기본은 --no-server**(2026-11-07 사고: 그냥 띄우면 게임이 개발 서버에 익명 계정을 만든다 —
    SupabaseHTTP._ready → ensure_session). 사용자 폴더도 건드리지 않게 APPDATA를 격리 폴더로 바꿔 준다.
    TestServer(포트 5000)가 응답할 때까지 기다렸다가 프로세스를 돌려준다.

    allow_server=True 는 서버 검증 테스트 전용 예외다(2026-11-08, 사용자 지시 "테스트를 위해 서버 접속은 예외로"):
    --no-server 를 빼고, 서버 전용 APPDATA(세션이 남는 폴더)로 띄운다. 띄우기 전에 장부에 run_start 를 적고,
    뜬 뒤 게임이 가진 서버 세션의 user_id 를 장부에 적는다. 장부에 없는 실계정으로 로그인돼 있으면 중단한다.

    fresh_profile=True 는 '게임을 처음 설치해 처음 켠 상태'(빈 프로필)로 띄운다 — 처음 실행 흐름(로고→타이틀→로그인→닉네임→튜토리얼)을 확인하는 테스트 전용."""
    import time
    import urllib.request
    import server_ledger
    appdata = SERVER_APPDATA_DIR if allow_server else GAME_APPDATA_DIR
    os.makedirs(appdata, exist_ok=True)

    def _ping() -> bool:
        try:
            with urllib.request.urlopen("http://127.0.0.1:5000/ping", timeout=2) as r:
                return b"ok" in r.read()
        except Exception:
            return False

    if _ping():
        raise RuntimeError("포트 5000에 이미 다른 게임이 떠 있습니다 — 그 게임을 시험 대상으로 착각하지 않도록 중단합니다.")
    _seed_profile(appdata, fresh_profile)
    env = dict(os.environ, APPDATA=appdata)
    cmd = [GODOT_EXE, "--path", GAME_PROJECT, "--windowed", "--resolution", "1920x864", "--position", "0,0"]
    if not allow_server:
        cmd += ["--", "--no-server"]
    else:
        server_ledger.append("run_start", appdata=appdata)
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"게임이 시작 직후 종료됐습니다(종료코드 {proc.returncode})")
        if _ping():
            if allow_server:
                try:
                    _register_launch_session()
                except Exception:
                    stop_game(proc)
                    raise
            return proc
        time.sleep(1)
    stop_game(proc)
    raise RuntimeError(f"게임의 TestServer가 {timeout}초 안에 응답하지 않았습니다")


def _seed_profile(appdata: str, fresh: bool = False) -> None:
    """격리 APPDATA 의 프로필에 '튜토리얼·온보딩을 이미 마친' 표시를 미리 적어 둔다.
    빈 프로필로 시작하면 MainMenu 의 PLAY 가 곡 선택이 아니라 튜토리얼로 가서(MainMenu._activate → has_seen_tutorial),
    풀 시나리오의 'PLAY → SongSelect' 가 이어지지 않는다(2026-11-08 run_all 의 full 단계에서 발견). 폰에서 쓰던 이미 한 번 쓴 프로필과 같은 상태로 맞춘다.
    튜토리얼·온보딩 화면 자체는 이 테스트로 검증하지 않는다(사람이 확인)."""
    path = os.path.join(appdata, "RhythmGame_New", "profile.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 화면 문구를 사양서(한국어)와 비교하므로 언어를 한국어로 고정한다. 없으면 게임이 이 PC의 시스템 언어로 정한다(Locale._detect_system_lang).
    with open(os.path.join(os.path.dirname(path), "lang_pref.txt"), "w", encoding="utf-8") as f:
        f.write("ko")
    if fresh:
        with open(path, "w", encoding="utf-8") as f:
            f.write("{}")
        return
    try:
        with open(path, encoding="utf-8") as f:
            profile = json.load(f)
        if not isinstance(profile, dict):
            profile = {}
    except Exception:
        profile = {}
    if profile.get("tutorial_seen") and profile.get("onboarding_done") and profile.get("display_name"):
        return
    profile["tutorial_seen"] = True
    profile["onboarding_done"] = True
    # 닉네임이 없으면 MainMenu 가 취소할 수 없는 '닉네임 설정' 팝업을 띄워(NicknameGate.require) 뒤로가기가 무시된다 —
    # 풀 시나리오 마지막의 뒤로가기 2번 종료가 안 되던 원인(2026-11-08, 화면 캡처로 확인).
    profile["display_name"] = profile.get("display_name") or "AutoTest"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False)


def _register_launch_session() -> None:
    """서버 모드로 뜬 게임의 세션(새 익명 계정이거나 저장돼 있던 세션)을 장부에 적는다. 장부에 없는 실계정이면 RuntimeError."""
    import client
    import server_ledger
    s = client.supabase_session(wait=30)
    uid = s.get("user_id", "")
    if not s.get("session_ready") or not uid:
        raise RuntimeError(f"서버 모드 게임이 30초 안에 서버 세션을 얻지 못했습니다: {s.get('last_auth_error')}")
    known = server_ledger.accounts().get(uid)
    if known is None and not s.get("is_anonymous"):
        raise RuntimeError(f"장부에 없는 실계정({uid})으로 로그인돼 있습니다 — 서버 전용 폴더의 세션을 확인하세요")
    server_ledger.register(uid, fixed=bool(known and known["fixed"]), label="launch")


def stop_game(proc) -> None:
    """start_game으로 띄운 프로세스 트리만 종료한다(다른 Godot 프로세스는 건드리지 않음)."""
    if proc is None or proc.poll() is not None:
        return
    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)


def run_unit_module(module: str, timeout: int = 180, allow_errors: tuple = ()) -> list:
    """모듈 이름(unit_<module>.gd)을 실행해 [{name, pass, detail}, ...] 를 돌려준다.
    결과가 하나도 없으면(스크립트 오류 등) RuntimeError — 조용히 0건으로 통과시키지 않는다.
    엔진이 낸 SCRIPT ERROR 는 그 함수가 중간에 끝나 뒤의 검사가 만들어지지 않았다는 뜻이다(2026-11-08 모듈 2에서 발견).
    허용 목록(allow_errors: 오류 줄에 들어 있는 글자)에 없는 오류가 있으면 "스크립트 오류 없음" TC를 실패로 추가한다."""
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
    lines = (out + "\n" + err).splitlines()
    errors = []
    for i, line in enumerate(lines):
        if "SCRIPT ERROR" in line or "Parse Error" in line or "@@UNIT_ERROR@@" in line:
            where = lines[i + 1].strip() if i + 1 < len(lines) and "at:" in lines[i + 1] else ""
            text = f"{line.strip()} {where}".strip()
            if not any(a in text for a in allow_errors):
                errors.append(text)
    results.append({"name": f"스크립트 오류 없음: 모듈 {module} (엔진 SCRIPT ERROR가 없어야 검사가 빠짐없이 만들어짐)",
                    "pass": not errors,
                    "detail": f"{len(errors)}건 — " + " | ".join(errors[:3])})
    return results
