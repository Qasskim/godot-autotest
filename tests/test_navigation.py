"""
화면 전환 테스트 (TC-12)
전제: SongSelect 상태에서 시작
"""
from datetime import datetime
import common.api_client as api
from common.result_writer import record_pass, record_fail


def _screenshot(driver, case_num: int) -> str:
    path = f"screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}_tc{case_num}.png"
    driver.save_screenshot(path)
    return path


def run(driver, wb, ws, case_num: int) -> int:

    # TC-12: 곡 선택 화면에서 메인 메뉴로 복귀
    case_num += 1
    try:
        api.navigate_main_menu()
        ok = api.wait_for_scene("MainMenu", timeout=10)
        if ok:
            record_pass(wb, ws, case_num, "곡 선택 화면에서 메인 메뉴로 복귀했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "곡 선택 화면에서 메인 메뉴로 복귀했는가?",
                        ss, f"씬 전환 실패: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "곡 선택 화면에서 메인 메뉴로 복귀했는가?", ss, str(e))

    return case_num
