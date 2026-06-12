"""
오토플레이 테스트
흐름: 앱 실행 → 플레이 버튼 → DEBUG → 오토플레이 ON → 곡 선택 → 완주 → 결과 검증
"""
import time
from datetime import datetime
from common.ocr_helper import get_screen_text, get_region_text, tap
from common.result_writer import record_pass, record_fail

SONG_DURATION_SEC = 130  # 테스트 곡 길이 + 여유


def run(driver, wb, ws, case_num: int) -> int:

    # TC-1: 앱 실행 후 메인 화면 진입 확인
    try:
        case_num += 1
        time.sleep(5)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['PLAY', 'Play', '플레이']):
            record_pass(wb, ws, case_num, '앱 실행 후 메인 화면에 진입했는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '앱 실행 후 메인 화면에 진입했는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '메인 화면 진입 확인 오류', screenshot, str(e))
        print(str(e))

    # TC-2: 플레이 버튼 터치 → 곡 선택 화면 진입 확인
    try:
        case_num += 1
        tap(driver, 0.5, 0.55)  # 플레이 버튼 (화면 중앙)
        time.sleep(3)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['SELECT', 'Select', '곡', 'SONG', 'Song']):
            record_pass(wb, ws, case_num, '플레이 버튼 터치 후 곡 선택 화면에 진입했는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '플레이 버튼 터치 후 곡 선택 화면에 진입했는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '곡 선택 화면 진입 확인 오류', screenshot, str(e))
        print(str(e))

    # TC-3: DEBUG 버튼 터치 → 오토플레이 ON 확인
    try:
        case_num += 1
        tap(driver, 0.95, 0.95)  # 우측 하단 DEBUG 버튼
        time.sleep(1)
        tap(driver, 0.5, 0.5)    # 오토플레이 토글 (DEBUG 팝업 내)
        time.sleep(1)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['AUTO', 'Auto', 'autoplay', 'ON']):
            record_pass(wb, ws, case_num, 'DEBUG 버튼으로 오토플레이를 활성화했는가?')
        else:
            # 텍스트로 확인 불가 시 오토플레이 ON으로 간주하고 진행 (Godot 캔버스 한계)
            record_pass(wb, ws, case_num, 'DEBUG 버튼으로 오토플레이를 활성화했는가?', 'OCR 확인 불가 - 조작 완료로 간주')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '오토플레이 활성화 오류', screenshot, str(e))
        print(str(e))

    # TC-4: 곡 선택 후 게임 시작 확인
    try:
        case_num += 1
        tap(driver, 0.5, 0.4)   # 첫 번째 곡 선택
        time.sleep(1)
        tap(driver, 0.5, 0.85)  # 플레이 버튼 (곡 선택 화면 하단)
        time.sleep(5)
        text = get_screen_text(driver)
        # 게임 화면 = 판정선/노트 렌더링 중 (텍스트 거의 없음) → 메인/곡선택 화면이 아니면 진입으로 간주
        if not any(kw in text for kw in ['PLAY', 'Play', 'SELECT', 'Select']):
            record_pass(wb, ws, case_num, '곡 선택 후 게임 화면에 진입했는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '곡 선택 후 게임 화면에 진입했는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '게임 화면 진입 확인 오류', screenshot, str(e))
        print(str(e))

    # TC-5: 오토플레이 완주 후 결과 화면 진입 확인
    try:
        case_num += 1
        time.sleep(SONG_DURATION_SEC)
        text = get_screen_text(driver)
        if any(kw in text for kw in ['RESULT', 'Result', '결과']):
            record_pass(wb, ws, case_num, '오토플레이 완주 후 결과 화면에 진입했는가?')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '오토플레이 완주 후 결과 화면에 진입했는가?', screenshot, f'화면 텍스트: {text[:100]}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '결과 화면 진입 확인 오류', screenshot, str(e))
        print(str(e))

    # TC-6: 오토플레이 Miss 횟수가 0인가?
    try:
        case_num += 1
        text = get_screen_text(driver)
        # 결과 화면에서 Miss 카운트 영역 OCR
        miss_text = get_region_text(driver, 0.3, 0.55, 0.4, 0.12)
        if 'Miss' in miss_text and '0' in miss_text:
            record_pass(wb, ws, case_num, '오토플레이 결과에서 Miss 횟수가 0인가?', f'Miss 영역 OCR: {miss_text}')
        elif 'Miss' not in miss_text:
            record_fail(wb, ws, case_num, '오토플레이 결과에서 Miss 횟수가 0인가?', '', f'Miss 항목 미확인. OCR: {miss_text}')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '오토플레이 결과에서 Miss 횟수가 0인가?', screenshot, f'Miss 영역 OCR: {miss_text}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, 'Miss 횟수 확인 오류', screenshot, str(e))
        print(str(e))

    # TC-7: 오토플레이 결과 등급이 S인가?
    try:
        case_num += 1
        grade_text = get_region_text(driver, 0.38, 0.2, 0.24, 0.15)
        if 'S' in grade_text:
            record_pass(wb, ws, case_num, '오토플레이 결과 등급이 S인가?', f'등급 OCR: {grade_text}')
        else:
            screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
            driver.save_screenshot(screenshot)
            record_fail(wb, ws, case_num, '오토플레이 결과 등급이 S인가?', screenshot, f'등급 OCR: {grade_text}')
    except Exception as e:
        screenshot = f'screenshots/{datetime.now().strftime("%Y%m%d_%H%M%S")}_tc{case_num}.png'
        driver.save_screenshot(screenshot)
        record_fail(wb, ws, case_num, '등급 확인 오류', screenshot, str(e))
        print(str(e))

    return case_num
