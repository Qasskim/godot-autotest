"""
화면 전환 테스트
결과 화면 → 곡 선택 복귀 → 설정 화면 열기/닫기
"""
import time
from datetime import datetime
from common.ocr_helper import get_screen_text, tap
from common.result_writer import record_pass, record_fail


def run(driver, wb, ws, case_num: int) -> int:

    # TC: 결과 화면에서 Back 버튼 터치 시 곡 선택 화면으로 복귀하는가?
    try:
        case_num += 1
        tap(driver, 0.1, 0.92)  # Back 버튼 (좌측 하단)
        time.sleep(3)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['SELECT', 'Select', '곡', 'SONG', 'Song', 'DEBUG']):
            record_pass(wb, ws, case_num, '결과 화면에서 Back 버튼 터치 시 곡 선택 화면으로 복귀하는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '결과 화면에서 Back 버튼 터치 시 곡 선택 화면으로 복귀하는가?',
                        screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '곡 선택 복귀 확인 오류', screenshot, str(e))
        print(str(e))

    # TC: 곡 선택 화면에서 설정 버튼 터치 시 설정 화면이 열리는가?
    try:
        case_num += 1
        tap(driver, 0.95, 0.05)  # 설정 버튼 (우측 상단)
        time.sleep(2)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['SETTING', 'Setting', '설정']):
            record_pass(wb, ws, case_num, '곡 선택 화면에서 설정 버튼 터치 시 설정 화면이 열리는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '곡 선택 화면에서 설정 버튼 터치 시 설정 화면이 열리는가?',
                        screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '설정 화면 열기 확인 오류', screenshot, str(e))
        print(str(e))

    # TC: 설정 화면에서 닫기 버튼 터치 시 곡 선택 화면으로 복귀하는가?
    try:
        case_num += 1
        tap(driver, 0.95, 0.05)  # 설정 닫기 (같은 버튼 토글 또는 X 버튼)
        time.sleep(2)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['SELECT', 'Select', '곡', 'SONG', 'Song', 'DEBUG']):
            record_pass(wb, ws, case_num, '설정 화면 닫기 후 곡 선택 화면으로 복귀하는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '설정 화면 닫기 후 곡 선택 화면으로 복귀하는가?',
                        screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '설정 닫기 후 복귀 확인 오류', screenshot, str(e))
        print(str(e))

    return case_num
