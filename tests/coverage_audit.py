# -*- coding: utf-8 -*-
"""게임 스크립트 전체를 시험과 대조하는 점검 도구 (pytest 아님 — 직접 실행). 2026-11-10.
  python coverage_audit.py
스크립트(Godot/scripts/**/*.gd)마다 (1) 시험 파일(tests/*.py·godot_unit/*.gd)에 스크립트 이름이 나오는지, (2) 공개 함수(밑줄로 시작하지 않는 func) 중 이름이 시험에 나오는 비율을 센다.
이름이 시험에 나오는 것은 '그 함수를 부르거나 확인한다'는 증거일 뿐 줄 단위 실행 범위(커버리지)는 아니다 — Godot 에는 GDScript 줄 단위 측정 도구가 없다.
결과: tests/reports/script_coverage.json 과 화면 표.
"""
import glob
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAME = os.environ.get("GAME_PROJECT", r"D:\Godot\RhythmGame_New\Godot")


def corpus() -> str:
    text = ""
    for f in glob.glob(os.path.join(HERE, "test_*.py")) + glob.glob(os.path.join(HERE, "client.py")) + glob.glob(os.path.join(HERE, "screen_helpers.py")) + glob.glob(os.path.join(ROOT, "godot_unit", "unit_*.gd")):
        text += open(f, encoding="utf-8", errors="replace").read() + "\n"
    return text


def audit() -> list:
    text = corpus()
    rows = []
    base = os.path.join(GAME, "scripts")
    for f in sorted(glob.glob(os.path.join(base, "**", "*.gd"), recursive=True)):
        src = open(f, encoding="utf-8", errors="replace").read()
        name = os.path.basename(f)[:-3]
        funcs = [m.group(1) for m in re.finditer(r"^(?:static )?func ([a-zA-Z]\w*)\(", src, re.M)]
        hit = [fn for fn in funcs if re.search(r"\b" + re.escape(fn) + r"\b", text)]
        named = bool(re.search(r"\b" + re.escape(name) + r"\b", text))
        rows.append({"file": os.path.relpath(f, base).replace(os.sep, "/"), "lines": len(src.splitlines()), "public": len(funcs), "hit": len(hit),
                     "named": named, "missing": [fn for fn in funcs if fn not in hit]})
    return rows


if __name__ == "__main__":
    rows = audit()
    os.makedirs(os.path.join(HERE, "reports"), exist_ok=True)
    json.dump(rows, open(os.path.join(HERE, "reports", "script_coverage.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(rows), "scripts")
    print("\n[이름도 공개 함수도 시험에 안 나옴]")
    for r in rows:
        if not r["named"] and r["hit"] == 0:
            print(f"  {r['file']:42} 줄 {r['lines']:5} 공개 함수 {r['public']}")
    print("\n[공개 함수 중 절반 미만만 시험에 나옴 (함수 3개 이상)]")
    for r in rows:
        if r["public"] >= 3 and r["hit"] / r["public"] < 0.5 and (r["hit"] > 0 or r["named"]):
            print(f"  {r['file']:42} {r['hit']}/{r['public']}  안 나온 함수: {', '.join(r['missing'][:8])}")
