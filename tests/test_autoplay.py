"""
오토플레이 테스트 (TC-1 ~ TC-7)
흐름: 앱 실행 → 메인 확인 → 곡 선택 진입 → 오토플레이 ON → 첫 곡 선택 → 플레이 → 완주 → 결과 검증
"""
from datetime import datetime
import common.api_client as api
from common.result_writer import record_pass, record_fail


def _screenshot(driver, case_num: int) -> str:
    path = f"screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}_tc{case_num}.png"
    driver.save_screenshot(path)
    return path


def run(driver, wb, ws, case_num: int) -> int:

    # TC-1: 앱 실행 후 메인 화면 진입 확인
    case_num += 1
    try:
        ok = api.wait_for_ping(timeout=15)
        if not ok:
            record_fail(wb, ws, case_num, "앱 실행 후 메인 화면에 진입했는가?", "", "TestServer 응답 없음")
        else:
            scene = api.get_scene()
            if scene == "MainMenu":
                record_pass(wb, ws, case_num, "앱 실행 후 메인 화면에 진입했는가?")
            else:
                ss = _screenshot(driver, case_num)
                record_fail(wb, ws, case_num, "앱 실행 후 메인 화면에 진입했는가?", ss, f"씬: {scene}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "앱 실행 후 메인 화면에 진입했는가?", ss, str(e))

    # TC-2: 곡 선택 화면 진입
    case_num += 1
    try:
        api.navigate_song_select()
        ok = api.wait_for_scene("SongSelect", timeout=10)
        if ok:
            record_pass(wb, ws, case_num, "PLAY 버튼 터치 후 곡 선택 화면에 진입했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "PLAY 버튼 터치 후 곡 선택 화면에 진입했는가?",
                        ss, f"씬 전환 실패: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "PLAY 버튼 터치 후 곡 선택 화면에 진입했는가?", ss, str(e))

    # TC-3: 오토플레이 ON
    case_num += 1
    try:
        api.autoplay_on()
        if api.get_autoplay():
            record_pass(wb, ws, case_num, "DEBUG에서 오토플레이를 활성화했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "DEBUG에서 오토플레이를 활성화했는가?",
                        ss, "API 응답 auto_play=false")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "DEBUG에서 오토플레이를 활성화했는가?", ss, str(e))

    # TC-4: 첫 번째 곡 선택 후 게임 화면 진입
    case_num += 1
    try:
        api.tap_first_song()
        api.tap_play()
        ok = api.wait_for_scene("GameScene", timeout=15)
        if ok:
            record_pass(wb, ws, case_num, "곡 선택 후 게임 화면에 진입했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "곡 선택 후 게임 화면에 진입했는가?",
                        ss, f"씬 전환 실패: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "곡 선택 후 게임 화면에 진입했는가?", ss, str(e))

    # TC-5: 오토플레이 완주 후 결과 화면 진입 (최대 300초 대기)
    case_num += 1
    try:
        ok = api.wait_for_scene("ResultScreen", timeout=300, interval=2.0)
        if ok:
            record_pass(wb, ws, case_num, "오토플레이 완주 후 결과 화면에 진입했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "오토플레이 완주 후 결과 화면에 진입했는가?",
                        ss, f"300초 내 ResultScreen 미도달: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "오토플레이 완주 후 결과 화면에 진입했는가?", ss, str(e))

    # TC-6: Miss 0 확인
    case_num += 1
    try:
        result = api.get_result()
        miss = result.get("miss", -1)
        if miss == 0:
            record_pass(wb, ws, case_num, "오토플레이 결과에서 Miss가 0인가?",
                        f"Miss={miss}, Wow={result.get('wow')}, Great={result.get('great')}")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "오토플레이 결과에서 Miss가 0인가?",
                        ss, f"Miss={miss} (result={result})")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "오토플레이 결과에서 Miss가 0인가?", ss, str(e))

    # TC-7: GRADE MAX 확인
    case_num += 1
    try:
        result = api.get_result()
        grade = result.get("grade", "")
        if grade == "MAX":
            record_pass(wb, ws, case_num, "오토플레이 결과 등급이 MAX인가?", f"GRADE={grade}")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "오토플레이 결과 등급이 MAX인가?",
                        ss, f"GRADE={grade}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "오토플레이 결과 등급이 MAX인가?", ss, str(e))

    return case_num
