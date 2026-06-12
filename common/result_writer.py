import openpyxl
import os
import psutil
from datetime import datetime

excel_file = 'test_results.xlsx'


def close_excel_if_open(file_name: str) -> None:
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if 'EXCEL' in proc.info['name'].upper():
                for f in proc.open_files():
                    if file_name in f.path:
                        proc.terminate()
                        proc.wait()
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


def init_workbook(device_name: str):
    close_excel_if_open(excel_file)

    if not os.path.exists(excel_file):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Test Results'
    else:
        wb = openpyxl.load_workbook(excel_file)
        ws = wb['Test Results']

    ws.append(['Device Name', device_name])
    ws.append(['test date/time', datetime.now().strftime('%x %X')])
    ws.append(['Test Number', 'Test Case', 'Result', 'Note', 'Error Log'])
    wb.save(excel_file)
    return wb, ws


def record_pass(wb, ws, case_num: int, case_name: str, note: str = '') -> None:
    ws.append([case_num, case_name, 'PASS', note])
    wb.save(excel_file)


def record_fail(wb, ws, case_num: int, case_name: str, screenshot: str = '', error: str = '') -> None:
    ws.append([case_num, case_name, 'FAIL', screenshot, error])
    wb.save(excel_file)
