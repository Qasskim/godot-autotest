# -*- coding: utf-8 -*-
"""풀 테스트 한 번에 돌리기 (2026-11-08, 사용자 확정 "진입점 하나, 이어하기 지원, 앞 단계가 실패해도 끝까지").

    python tests/run_all.py                    # 전부: unit → integration → server → full 순서로 끝까지 돈다 (몇 시간)
    python tests/run_all.py --quick            # unit 만 (게임 창·서버 없이 헤드리스, 분 단위)
    python tests/run_all.py --stages unit,server   # 원하는 단계만
    python tests/run_all.py --resume           # 이전 실행에서 통과한 단계는 건너뛰고, full 은 끝까지 통과한 곡도 건너뛴다
    python tests/run_all.py --cleanup          # server 단계가 끝나면 장부에 적힌 테스트 데이터를 실제로 지운다 (없으면 목록만 보여준다)

단계 (각각 별도 pytest 프로세스 — 게임을 --no-server 로 쓰는 단계, 서버에 접속하는 단계, 게임을 종료시키는 단계가 섞이지 않게):
- unit        : 마커 no_server 전부 (헤드리스 모듈 1~12, 데이터, 교차 비교, 장부 규칙)
- integration : 게임 창이 필요한 통합 테스트 (test_flow·autoplay·marks·best_record·no_server). 게임은 conftest 가 --no-server 로 띄움
- server      : 마커 server (개발 서버에 그대로 접속, 계정은 장부에 적힘)
- full        : test_full_scenario.py — 모든 화면·버튼·곡 전체 순회, 마지막에 게임을 종료시킴 (몇 시간)

결과는 실행마다 새 폴더 tests/reports/yyyy_mm_dd_차수 (차수는 그날 몇 번째 실행인지, 숫자만) 에 모인다 (2026-11-11 사용자 지시):
  TC_결과.xlsx (사람이 읽는 테스트 케이스 형식), test_results.xlsx (시험 이름 그대로, 단계마다 시트), 실패 스크린샷 FAIL_*.png,
  run_log.txt (실행 로그), full_run_state.json (단계별 통과/실패 요약), full_run_<단계>.xml.
이어하기용 상태는 tests/reports/full_run_state.json 에도 그대로 남는다.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")
STATE_PATH = os.path.join(REPORTS, "full_run_state.json")
PROGRESS_PATH = os.path.join(REPORTS, "full_scenario_progress.json")

STAGES = {
    "unit": ["-m", "no_server"],
    "integration": ["-m", "not no_server and not server", "--ignore=test_full_scenario.py"],
    "server": ["-m", "server"],
    "full": ["test_full_scenario.py"],
}
ORDER = list(STAGES)


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"stages": {}}


def save_state(state: dict) -> None:
    os.makedirs(REPORTS, exist_ok=True)
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def junit_counts(path: str) -> dict:
    try:
        root = ET.parse(path).getroot()
        suite = root if root.tag == "testsuite" else root.find("testsuite")
        return {k: int(suite.attrib.get(k, 0)) for k in ("tests", "failures", "errors", "skipped")}
    except Exception:
        return {}


class Tee:
    """화면에 찍는 글을 이번 실행의 결과 폴더 안 실행 로그 파일에도 같이 적는다."""

    def __init__(self, stream, path: str):
        self.stream, self.file = stream, open(path, "a", encoding="utf-8")

    def write(self, text: str) -> int:
        self.stream.write(text)
        self.file.write(text)
        self.file.flush()
        return len(text)

    def flush(self) -> None:
        self.stream.flush()


def new_run_dir() -> str:
    """reports/yyyy_mm_dd_차수 폴더를 만든다(2026-11-11 사용자 지시: 차수는 숫자만, 풀 테스트를 돌릴 때만 생김). 차수는 그날 이미 있는 폴더의 다음 번호."""
    day = time.strftime("%Y_%m_%d")
    used = [int(n[len(day) + 1:]) for n in os.listdir(REPORTS) if n.startswith(day + "_") and n[len(day) + 1:].isdigit()]
    path = os.path.join(REPORTS, f"{day}_{max(used, default=0) + 1}")
    os.makedirs(path)
    return path


def call_logged(cmd: list, env: dict) -> int:
    """하위 프로세스의 출력을 한 줄씩 받아 화면과 실행 로그에 같이 적는다."""
    proc = subprocess.Popen(cmd, cwd=HERE, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        print(line, end="", flush=True)
    return proc.wait()


def run_stage(name: str, run_dir: str) -> dict:
    junit = os.path.join(run_dir, f"full_run_{name}.xml")
    cmd = [sys.executable, "-m", "pytest", "-v", f"--junitxml={junit}", *STAGES[name]]
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["AUTOTEST_RUN_DIR"] = run_dir                # 결과 엑셀과 실패 스크린샷이 이 폴더에 들어간다 (conftest·result_writer)
    if name == "full":
        env["AUTOTEST_PROGRESS"] = PROGRESS_PATH
    print(f"\n{'=' * 70}\n단계 [{name}] 시작 {time.strftime('%H:%M:%S')} — {' '.join(cmd[3:])}\n{'=' * 70}", flush=True)
    t0 = time.time()
    code = call_logged(cmd, env)
    counts = junit_counts(junit)
    bad = counts.get("failures", 0) + counts.get("errors", 0)
    status = "passed" if code == 0 and counts and bad == 0 else "failed"
    return {"status": status, "exit": code, "counts": counts, "seconds": round(time.time() - t0),
            "finished": time.strftime("%Y-%m-%d %H:%M:%S")}


def run_cleanup(apply: bool) -> None:
    cmd = [sys.executable, os.path.join(HERE, "cleanup_server.py")] + (["--apply"] if apply else [])
    print(f"\n[server 정리] {'삭제 실행' if apply else '목록만 (삭제하려면 --cleanup)'}", flush=True)
    call_logged(cmd, dict(os.environ, PYTHONIOENCODING="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="풀 테스트 한 번에 돌리기")
    ap.add_argument("--quick", action="store_true", help="unit 단계만")
    ap.add_argument("--stages", help="쉼표로 구분한 단계 이름 (unit,integration,server,full)")
    ap.add_argument("--resume", action="store_true", help="통과한 단계·곡은 건너뛴다")
    ap.add_argument("--cleanup", action="store_true", help="server 단계 뒤 장부에 적힌 테스트 데이터를 실제로 삭제")
    args = ap.parse_args()

    chosen = ["unit"] if args.quick else (args.stages.split(",") if args.stages else list(ORDER))   # ORDER 를 복사한다 — 같은 리스트를 정렬하면 정렬 도중 ORDER 가 변해 ValueError
    unknown = [s for s in chosen if s not in STAGES]
    if unknown:
        print(f"알 수 없는 단계: {unknown} (가능: {ORDER})")
        return 2
    chosen.sort(key=ORDER.index)

    state = load_state() if args.resume else {"stages": {}}
    if not args.resume:
        os.makedirs(REPORTS, exist_ok=True)
        with open(PROGRESS_PATH, "w", encoding="utf-8") as f:       # 곡 진행 기록 초기화 (지우지 않고 비운다)
            json.dump({"charts": []}, f)
    state["started"] = state.get("started") if args.resume and state.get("started") else time.strftime("%Y-%m-%d %H:%M:%S")
    # 이번 실행의 결과 폴더. 이어하기(--resume)는 이전 실행의 폴더를 그대로 쓴다(없어졌으면 새로 만든다).
    os.makedirs(REPORTS, exist_ok=True)
    run_dir = state.get("run_dir") if args.resume and os.path.isdir(state.get("run_dir") or "") else new_run_dir()
    state["run_dir"] = run_dir
    save_state(state)
    sys.stdout = Tee(sys.stdout, os.path.join(run_dir, "run_log.txt"))
    print(f"결과 폴더: {run_dir}", flush=True)

    for name in chosen:
        prev = state["stages"].get(name, {})
        if args.resume and prev.get("status") == "passed":
            print(f"\n단계 [{name}] 이전 실행에서 통과 — 건너뜀 ({prev.get('finished')})", flush=True)
            continue
        state["stages"][name] = run_stage(name, run_dir)       # 앞 단계가 실패해도 다음 단계로 간다
        save_state(state)
        if name == "server":
            run_cleanup(apply=args.cleanup)

    print(f"\n{'=' * 70}\n풀 테스트 요약 (시작 {state['started']})\n{'=' * 70}")
    print(f"{'단계':<14}{'결과':<10}{'전체':>6}{'실패':>6}{'오류':>6}{'건너뜀':>8}{'시간(초)':>10}")
    all_ok = True
    for name in ORDER:
        s = state["stages"].get(name)
        if s is None:
            continue
        c = s.get("counts", {})
        all_ok = all_ok and s["status"] == "passed"
        print(f"{name:<14}{s['status']:<10}{c.get('tests', '?'):>6}{c.get('failures', '?'):>6}{c.get('errors', '?'):>6}{c.get('skipped', '?'):>8}{s['seconds']:>10}")
    summary_copy = os.path.join(run_dir, "full_run_state.json")
    with open(summary_copy, "w", encoding="utf-8") as f:                # 단계별 통과/실패 요약도 결과 폴더에 같이 둔다
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"\n결과 폴더: {run_dir}\n단계별 요약: {summary_copy}\n시험 이름 그대로의 엑셀: {os.path.join(run_dir, 'test_results.xlsx')}")
    # 사람이 읽는 테스트 케이스 형식의 엑셀을 같이 뽑는다(2026-11-11 사용자 지시). 뽑기에 실패해도 풀 테스트의 통과/실패 결과는 바꾸지 않는다.
    try:
        import tc_export
        tc_export.main(run_dir)
    except Exception as e:
        print(f"TC 형식 엑셀을 뽑지 못했습니다: {e}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
