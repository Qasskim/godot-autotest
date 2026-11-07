# -*- coding: utf-8 -*-
"""테스트 결과 엑셀 기록. <LOCAL_PATH> 방식 참고."""
import os
from datetime import datetime

import openpyxl
from openpyxl.drawing.image import Image as XLImage

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "reports", "test_results.xlsx")


def init_workbook():
    global EXCEL_PATH
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)
    wb = None
    if os.path.exists(EXCEL_PATH):
        try:
            wb = openpyxl.load_workbook(EXCEL_PATH)
            # 불러온 이미지는 두 번째 save부터 "I/O operation on closed file"로 죽고 파일까지 깨뜨린다
            # (2026-11-07 재현). 이전 실행의 삽입 이미지는 버리고(스크린샷 원본은 reports/의 png로 남아 있음) 글자 기록만 이어 쓴다.
            for old_ws in wb.worksheets:
                old_ws._images = []
        except Exception as e:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            broken = EXCEL_PATH + f".broken_{stamp}"
            try:
                os.replace(EXCEL_PATH, broken)
                print(f"\n[result_writer] 기존 결과 파일을 읽지 못해 {broken} 로 옮기고 새로 만듭니다: {e}")
            except OSError as move_err:
                # 옛 파일이 다른 프로세스에 잡혀 있으면 옮기지 못한다 — 멈추지 말고 이번 실행은 새 이름으로 기록한다.
                EXCEL_PATH = os.path.join(os.path.dirname(EXCEL_PATH), f"test_results_{stamp}.xlsx")
                print(f"\n[result_writer] 기존 결과 파일을 읽지도 옮기지도 못해({e} / {move_err}) 이번 실행은 {EXCEL_PATH} 에 기록합니다.")
            wb = None
    if wb is None:
        wb = openpyxl.Workbook()

    sheet_name = _unique_sheet_name(wb, datetime.now().strftime("%d-%m-%Y"))
    ws = wb.create_sheet(title=sheet_name)
    wb.active = wb.sheetnames.index(sheet_name)

    # 새로 만든 워크북이면 비어있는 기본 시트("Sheet") 정리
    if "Sheet" in wb.sheetnames and wb["Sheet"] is not ws \
            and wb["Sheet"].max_row == 1 and wb["Sheet"].max_column == 1 \
            and wb["Sheet"]["A1"].value is None:
        wb.remove(wb["Sheet"])

    ws.append(["test date/time", datetime.now().strftime("%x %X")])
    ws.append(["Test Number", "Test Case", "Result", "Note", "Screenshot"])
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 24
    _save(wb)
    return wb, ws


def _unique_sheet_name(wb, base_name: str) -> str:
    if base_name not in wb.sheetnames:
        return base_name
    n = 2
    while f"{base_name} ({n})" in wb.sheetnames:
        n += 1
    return f"{base_name} ({n})"


# (ws, row, path) 대기열 — 이미지는 세션 끝에 한 번만 삽입한다.
# openpyxl은 wb.save() 때마다 이미 삽입된 이미지까지 다시 직렬화하는데,
# PIL이 연 파일 핸들이 첫 save 이후 닫혀서 두 번째 save부터 "I/O operation on closed file"로 죽음.
_pending_images: list = []


def record(wb, ws, case_num: int, case_name: str, result: str, note: str = "",
           screenshot_path: str = None) -> None:
    row = ws.max_row + 1
    ws.cell(row=row, column=1, value=case_num)
    ws.cell(row=row, column=2, value=case_name)
    ws.cell(row=row, column=3, value=result)
    ws.cell(row=row, column=4, value=note)
    if screenshot_path and os.path.exists(screenshot_path):
        _pending_images.append((ws, row, screenshot_path))
        ws.row_dimensions[row].height = 70
    _save(wb)


def finalize(wb) -> None:
    """세션 종료 시 1회 호출 — 대기 중인 스크린샷을 전부 삽입하고 마지막으로 저장."""
    for ws, row, path in _pending_images:
        try:
            img = XLImage(path)
            img.width, img.height = 160, 90
            ws.add_image(img, f"E{row}")
        except Exception as e:
            print(f"\n[result_writer] 이미지 삽입 실패: {e}")
    _pending_images.clear()
    _save(wb)


def _save(wb) -> None:
    try:
        wb.save(EXCEL_PATH)
    except PermissionError:
        print(f"\n[result_writer] {EXCEL_PATH} 저장 실패 — 엑셀에서 파일을 열어놓은 상태면 닫고 다시 실행하세요.")
