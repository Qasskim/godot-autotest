# -*- coding: utf-8 -*-
"""풀 테스트 결과를 사람이 읽는 테스트 케이스(TC) 형식의 새 엑셀 파일로 뽑는다 (2026-11-11, 사용자 지시
"저런식으로 케이스를 적으면 사람은 못알아봐 제대로 테스트 케이스를 써야지" → "지금 보여준 예시처럼 만들어줘").

형식(사용자 포폴의 TC 예시와 같은 칸): TC 번호 / 대분류 / 중분류 / 소분류 / 사전 조건 / 테스트 절차 / 순번 / 기대 결과 / 결과 / 비고 / 자동화 시험 이름.
케이스 문장은 tests/tc_catalog/*.json 에 있다(시험 코드를 읽고 사람이 쓴 글). 결과는 tests/reports/test_results.xlsx 에서
마지막 run_all.py 실행(full_run_state.json 의 시작 시각 이후) 시트들을 읽는다. 기존 결과 파일은 고치지 않는다.

풀 테스트(run_all.py)가 끝날 때 자동으로 불려서 이번 실행의 결과 폴더(tests/reports/yyyy_mm_dd_차수)에 TC_결과.xlsx 를 만든다.
따로 다시 뽑기:  python tests/tc_export.py     → 마지막 풀 테스트의 결과 폴더에 다시 만든다
"""
import glob
import json
import os
import re
import sys
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")
BS = chr(92)
UNI = re.compile(re.escape(BS + "u") + "([0-9a-fA-F]{4})")
HEXB = re.compile(re.escape(BS + "x") + "([0-9a-fA-F]{2})")
HEADERS = ["TC 번호", "대분류", "중분류", "소분류", "사전 조건", "테스트 절차", "순번", "기대 결과", "결과", "비고", "자동화 시험 이름"]


def decode(text: str) -> str:
    """pytest 가 시험 이름 안의 한글을 유니코드 번호로 바꿔 적은 것을 다시 글자로 돌린다."""
    text = UNI.sub(lambda m: chr(int(m.group(1), 16)), text)
    return HEXB.sub(lambda m: chr(int(m.group(1), 16)), text)


def load_catalog() -> dict:
    cat = {}
    for path in sorted(glob.glob(os.path.join(HERE, "tc_catalog", "*.json"))):
        cat.update(json.load(open(path, encoding="utf-8")))
    return cat


def last_run_sheets(wb) -> list:
    """마지막 run_all.py 실행이 만든 시트(시작 시각 이후)를 실행 순서대로 돌려준다."""
    state = json.load(open(os.path.join(REPORTS, "full_run_state.json"), encoding="utf-8"))
    started = datetime.strptime(state["started"], "%Y-%m-%d %H:%M:%S")
    out = []
    for ws in wb.worksheets:
        stamp = ws.cell(row=1, column=2).value
        try:
            when = datetime.strptime(str(stamp), "%m/%d/%y %H:%M:%S")
        except ValueError:
            continue
        if when >= started:
            out.append((when, ws))
    return [ws for _, ws in sorted(out, key=lambda x: x[0])], state["started"]


def build_rows(cat: dict, sheets: list) -> tuple:
    """(행 목록, 문장이 없는 시험 목록). 행 = dict(code, big, mid, small, pre, step, n, expect, result, note, auto)."""
    rows, missing = [], []
    unit_map, pmap = cat["_unit"], cat["_pmap"]
    full, na = cat["_full_direct"], cat["_na"]
    for ws in sheets:
        for num, name, result, note, *_ in ws.iter_rows(min_row=3, values_only=True):
            if name is None:
                continue
            name, note = decode(str(name)), str(note or "")
            if "::" not in name:                                    # 시험 안에서 직접 적은 줄(곡별 항목, N/A)
                rows.extend(direct_rows(name, result, note, full, na))
                continue
            file, rest = name.split("::", 1)
            func, param = (rest[:rest.index("[")], rest[rest.index("[") + 1:-1]) if "[" in rest else (rest, "")
            if file == "test_na_user_areas.py":                     # N/A 줄을 실어 나르는 시험이라 TC 가 아니다
                continue
            if file in unit_map:
                big, code, pre, step = unit_map[file]
                mid, expect = param.split(": ", 1) if ": " in param else ("", param)
                rows.append(dict(code=code, big=big, mid=mid, small="", pre=pre, step=step, n=1, expect=expect,
                                 result=result, note=note, auto=f"{file}::{func}"))
                continue
            entry = cat.get(file, {}).get("t", {}).get(func, "없음")
            if entry is None:                                       # 직접 적은 줄이 대신하는 시험
                continue
            if entry == "없음":
                missing.append(name)
                continue
            shown = pmap.get(f"{file}::{func}", {}).get(param, param)
            mid, small, pre, step, expects = entry
            pre = pre or cat[file]["pre"]
            for i, expect in enumerate(expects, 1):
                rows.append(dict(code=cat[file]["code"], big=cat[file]["big"], mid=mid, small=small,
                                 pre=pre.replace("{p}", shown), step=step.replace("{p}", shown), n=i,
                                 expect=expect.replace("{p}", shown), result=result, note=note if i == 1 else "",
                                 auto=name))
    # 읽는 순서: 화면·서버·전체 시나리오 → 데이터·계산(엔진만 실행) → 유저 테스트(N/A). 같은 묶음 안의 순서는 실행 순서 그대로.
    engine_only = set(unit_map) | {f for f in cat if f.startswith("test_data_")} | {"test_cross_formula.py", "test_resume_keys.py", "test_server_ledger.py"}
    rows.sort(key=lambda r: (r["code"] == na["code"], r["auto"].split("::")[0] in engine_only))
    return rows, missing


def direct_rows(name: str, result, note: str, full: dict, na: dict) -> list:
    m = re.match(r"chart\[(\d+)\] (.+?): (.+)$", name)
    if m:                                                           # 곡 전체 순회의 곡별 항목
        title, what = m.group(2), m.group(3)
        small, pre, step, expect = full["chart_steps"][what]
        return [dict(code=full["code"], big=full["big"], mid=f"곡 순회: {title}", small=small, pre=pre, step=step, n=1,
                     expect=expect, result=result, note=note, auto="test_full_scenario.py::test_04_play_every_chart")]
    if name in full["other"]:
        mid, small, pre, step, expect = full["other"][name]
        return [dict(code=full["code"], big=full["big"], mid=mid, small=small, pre=pre, step=step, n=1,
                     expect=expect, result=result, note=note, auto="test_full_scenario.py")]
    mid, expect = name.split(": ", 1) if ": " in name else ("", name)   # 유저 테스트 영역(N/A)
    return [dict(code=na["code"], big=na["big"], mid=mid, small="", pre="", step="사람이 직접 확인", n=1,
                 expect=expect, result=result, note=note, auto="test_na_user_areas.py")]


def write_xlsx(rows: list, started: str, out_path: str) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "TC"
    thin = Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")
    center = Alignment(horizontal="center", vertical="top", wrap_text=True)
    ws.append(HEADERS)
    for c in ws[1]:
        c.font, c.fill, c.border, c.alignment = Font(bold=True), PatternFill("solid", fgColor="D9E1F2"), box, center
    counters, colors = {}, {"PASS": "E2EFDA", "FAIL": "F8CBAD", "N/A": "EDEDED", "SKIP": "FFF2CC"}
    for r in rows:
        counters[r["code"]] = counters.get(r["code"], 0) + 1
        ws.append([f"TC-{r['code']}-{counters[r['code']]:03d}", r["big"], r["mid"], r["small"], r["pre"], r["step"],
                   r["n"], r["expect"], r["result"], r["note"], r["auto"]])
        for c in ws[ws.max_row]:
            c.border, c.alignment = box, wrap
        ws.cell(row=ws.max_row, column=7).alignment = center
        res = ws.cell(row=ws.max_row, column=9)
        res.alignment, res.fill = center, PatternFill("solid", fgColor=colors.get(r["result"], "FFFFFF"))
    merge_runs(ws, rows)
    for letter, width in zip("ABCDEFGHIJK", (16, 20, 20, 16, 34, 44, 6, 60, 8, 40, 46)):
        ws.column_dimensions[letter].width = width
    ws.freeze_panes = "A2"
    summary(wb, rows, started)
    wb.save(out_path)


def merge_runs(ws, rows: list) -> None:
    """같은 값이 이어지는 칸을 합친다(사용자 TC 예시와 같은 모양): 한 시험의 사전 조건·절차, 이어지는 대/중/소분류."""
    def merge(col: int, key) -> None:
        start = 0
        for i in range(1, len(rows) + 1):
            if i == len(rows) or key(rows[i]) != key(rows[start]):
                if i - start > 1:
                    ws.merge_cells(start_row=start + 2, start_column=col, end_row=i + 1, end_column=col)
                start = i
    merge(2, lambda r: r["big"])
    merge(3, lambda r: (r["big"], r["mid"]))
    merge(4, lambda r: (r["big"], r["mid"], r["small"]))
    merge(5, lambda r: (r["auto"], r["mid"], r["pre"]))
    merge(6, lambda r: (r["auto"], r["mid"], r["pre"], r["step"]))


def summary(wb, rows: list, started: str) -> None:
    ws = wb.create_sheet("요약", 0)
    ws.append(["풀 테스트 시작", started])
    ws.append(["TC 줄 수(기대 결과 1개 = 1줄)", len(rows)])
    ws.append([])
    ws.append([])
    ws.append(["대분류", "PASS", "FAIL", "N/A", "SKIP", "합계"])
    order, table = [], {}
    for r in rows:
        if r["big"] not in table:
            order.append(r["big"])
            table[r["big"]] = {"PASS": 0, "FAIL": 0, "N/A": 0, "SKIP": 0}
        table[r["big"]][r["result"]] = table[r["big"]].get(r["result"], 0) + 1
    for big in order:
        t = table[big]
        ws.append([big, t["PASS"], t["FAIL"], t["N/A"], t["SKIP"], sum(t.values())])
    ws.append(["합계"] + [sum(table[b][k] for b in order) for k in ("PASS", "FAIL", "N/A", "SKIP")] + [len(rows)])
    for c in ws[5]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 44


def main(run_dir: str = "") -> int:
    """run_dir(이번 실행의 결과 폴더)가 있으면 그 안의 결과로 그 안에 뽑는다. 없으면 마지막 풀 테스트의 결과 폴더를 쓰고,
    결과 폴더가 생기기 전(2026-11-10)의 실행이면 reports 의 공용 결과 파일에서 시작 시각 이후 시트를 읽는다."""
    state = json.load(open(os.path.join(REPORTS, "full_run_state.json"), encoding="utf-8"))
    run_dir = run_dir or state.get("run_dir") or ""
    if run_dir:
        wb = openpyxl.load_workbook(os.path.join(run_dir, "test_results.xlsx"), read_only=True)
        sheets, started = list(wb.worksheets), state["started"]
    else:
        wb = openpyxl.load_workbook(os.path.join(REPORTS, "test_results.xlsx"), read_only=True)
        sheets, started = last_run_sheets(wb)
    rows, missing = build_rows(load_catalog(), sheets)
    if missing:
        print("TC 문장이 없는 시험이 있습니다(tc_catalog 에 추가 필요):")
        for m in missing:
            print("  ", m)
        return 1
    if run_dir:
        out = os.path.join(run_dir, "TC_결과.xlsx")                     # 폴더 이름이 날짜와 차수라 파일 이름은 고정
    else:
        out = os.path.join(REPORTS, f"TC_결과_{started[:16].replace(' ', '_').replace(':', '')}.xlsx")
    write_xlsx(rows, started, out)
    print(f"시트 {len(sheets)}개에서 TC {len(rows)}줄을 뽑았습니다: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
