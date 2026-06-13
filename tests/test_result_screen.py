"""
결과 화면 검증 테스트 (TC-8 ~ TC-11)
전제: 오토플레이 완주 후 ResultScreen 상태
"""
from datetime import datetime
import common.api_client as api
from common.result_writer import record_pass, record_fail


def _screenshot(driver, case_num: int) -> str:
    path = f"screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}_tc{case_num}.png"
    driver.save_screenshot(path)
    return path


def run(driver, wb, ws, case_num: int) -> int:

    # TC-8: 판정 항목(Wow/Great/Good/Oops) 모두 0 이상인가?
    case_num += 1
    try:
        result = api.get_result()
        keys = ["wow", "great", "good", "oops"]
        missing = [k for k in keys if k not in result]
        if not missing:
            detail = ", ".join(f"{k}={result[k]}" for k in keys)
            record_pass(wb, ws, case_num, "결과 화면에 판정 항목이 모두 표시되는가?", detail)
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "결과 화면에 판정 항목이 모두 표시되는가?",
                        ss, f"누락 키: {missing}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "결과 화면에 판정 항목이 모두 표시되는가?", ss, str(e))

    # TC-9: 점수(score)가 0 이상인가?
    case_num += 1
    try:
        result = api.get_result()
        score  = result.get("score", -1)
        max_ex = result.get("max_ex", 0)
        if score >= 0:
            record_pass(wb, ws, case_num, "결과 화면에 점수가 표시되는가?",
                        f"score={score}, max_ex={max_ex}, accuracy={result.get('accuracy'):.2f}%")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "결과 화면에 점수가 표시되는가?",
                        ss, f"score={score}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "결과 화면에 점수가 표시되는가?", ss, str(e))

    # TC-10: 다시하기 버튼 → 게임 화면 진입
    case_num += 1
    try:
        api.tap_retry()
        ok = api.wait_for_scene("GameScene", timeout=15)
        if ok:
            record_pass(wb, ws, case_num, "다시하기 버튼 동작 후 게임 화면에 진입했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "다시하기 버튼 동작 후 게임 화면에 진입했는가?",
                        ss, f"씬 전환 실패: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "다시하기 버튼 동작 후 게임 화면에 진입했는가?", ss, str(e))

    # TC-10 이후 결과 화면으로 다시 이동 (TC-11 준비)
    api.wait_for_scene("ResultScreen", timeout=300, interval=2.0)

    # TC-11: 곡선택 버튼 → 곡 선택 화면 복귀
    case_num += 1
    try:
        api.tap_select_song()
        ok = api.wait_for_scene("SongSelect", timeout=10)
        if ok:
            record_pass(wb, ws, case_num, "곡 선택 버튼 동작 후 곡 선택 화면에 복귀했는가?")
        else:
            ss = _screenshot(driver, case_num)
            record_fail(wb, ws, case_num, "곡 선택 버튼 동작 후 곡 선택 화면에 복귀했는가?",
                        ss, f"씬 전환 실패: {api.get_scene()}")
    except Exception as e:
        ss = _screenshot(driver, case_num)
        record_fail(wb, ws, case_num, "곡 선택 버튼 동작 후 곡 선택 화면에 복귀했는가?", ss, str(e))

    return case_num
