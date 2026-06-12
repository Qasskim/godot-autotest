"""
결과 화면 검증 테스트
전제: 오토플레이 완주 직후 결과 화면이 표시된 상태에서 실행
"""
import time
from datetime import datetime
from common.ocr_helper import get_screen_text, tap
from common.result_writer import record_pass, record_fail


def run(driver, wb, ws, case_num: int) -> int:

    # TC: 결과 화면에 판정 항목(Wow/Great/Good/Oops)이 모두 표시되는가?
    try:
        case_num += 1
        text = get_screen_text(driver)
        missing = [label for label in ['Wow', 'Great', 'Good', 'Oops'] if label not in text]
        if not missing:
            record_pass(wb, ws, case_num, '결과 화면에 판정 항목(Wow/Great/Good/Oops)이 모두 표시되는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '결과 화면에 판정 항목(Wow/Great/Good/Oops)이 모두 표시되는가?',
                        screenshot, f'미표시 항목: {missing}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '판정 항목 표시 확인 오류', screenshot, str(e))
        print(str(e))

    # TC: 결과 화면에 점수(숫자)가 표시되는가?
    try:
        case_num += 1
        import re
        text = get_screen_text(driver)
        numbers = re.findall(r'\d{3,}', text.replace(',', ''))
        if numbers:
            record_pass(wb, ws, case_num, '결과 화면에 점수가 표시되는가?', f'인식된 점수: {numbers[0]}')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '결과 화면에 점수가 표시되는가?', screenshot, '점수 숫자 미인식')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '점수 표시 확인 오류', screenshot, str(e))
        print(str(e))

    # TC: 결과 화면에 다시 시작(Retry) 버튼이 존재하는가?
    try:
        case_num += 1
        text = get_screen_text(driver)
        if any(kw in text for kw in ['RETRY', 'Retry', '다시']):
            record_pass(wb, ws, case_num, '결과 화면에 다시 시작 버튼이 존재하는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '결과 화면에 다시 시작 버튼이 존재하는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '다시 시작 버튼 확인 오류', screenshot, str(e))
        print(str(e))

    # TC: 결과 화면에 곡 선택으로 돌아가기(Back) 버튼이 존재하는가?
    try:
        case_num += 1
        text = get_screen_text(driver)
        if any(kw in text for kw in ['BACK', 'Back', '돌아', '목록']):
            record_pass(wb, ws, case_num, '결과 화면에 곡 선택으로 돌아가기 버튼이 존재하는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '결과 화면에 곡 선택으로 돌아가기 버튼이 존재하는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '돌아가기 버튼 확인 오류', screenshot, str(e))
        print(str(e))

    return case_num
