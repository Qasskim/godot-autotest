# -*- coding: utf-8 -*-
"""개인 최고기록 갱신/비교 테스트 + ResultScreen 스크린샷"""
import os
import time
import pytest
import client
from conftest import SONG_ID, DIFFICULTY, PLATFORM, play_one_round

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _screenshot(label: str) -> None:
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, f"result_{label}_{ts}.png")
    if client.screenshot(path):
        print(f"\n[스크린샷] {path}")
    else:
        print("\n[스크린샷 실패]")


def _print_summary(res: dict, label: str) -> None:
    print(f"\n[{label}] 점수:{res['score']}  정확도:{res['accuracy']:.2f}%  그레이드:{res['grade']}")
    print(f"  마크:{res.get('marks', [])}")
    if res.get("is_best"):
        print("  ★ 신기록 갱신")
    else:
        prev = res.get("prev_best", {})
        if prev:
            diff = res["score"] - prev.get("ex_score", 0)
            sign = "+" if diff >= 0 else ""
            print(f"  기록 미갱신 (이전:{prev.get('ex_score','?')}  차이:{sign}{diff})")


@pytest.mark.slow
def test_is_best_flag_and_best_endpoint():
    """플레이 후 is_best 상태와 /best 엔드포인트 값이 일치하는지 확인"""
    res = play_one_round()
    _print_summary(res, "플레이")
    _screenshot("play")

    if res["is_best"]:
        best = client.best(SONG_ID, DIFFICULTY, PLATFORM)
        assert "error" not in best, f"/best 오류: {best}"
        assert best.get("ex_score") == res["score"], \
            f"/best 점수({best.get('ex_score')}) != result 점수({res['score']})"
        print("  /best 일치 확인")
    else:
        prev = res.get("prev_best", {})
        assert prev, "is_best=false인데 prev_best 없음"
        assert prev.get("ex_score", 0) >= res["score"], \
            f"prev_best({prev.get('ex_score')})가 현재 점수({res['score']})보다 낮은데 is_best=false"
        print(f"  기록 미갱신 확인 (이전:{prev.get('ex_score')}  현재:{res['score']})")


@pytest.mark.slow
def test_two_plays_comparison():
    """2판 연속 플레이 후 점수 비교 및 is_best 정합성 확인"""
    res1 = play_one_round()
    _print_summary(res1, "1차")
    _screenshot("play1")

    res2 = play_one_round()
    _print_summary(res2, "2차")
    _screenshot("play2")

    score1 = res1["score"]
    score2 = res2["score"]
    diff = score2 - score1
    sign = "+" if diff >= 0 else ""
    print(f"\n[비교] {score1} → {score2}  ({sign}{diff})")

    if score2 > score1:
        assert res2["is_best"] is True, f"점수 올랐는데 is_best=false (diff={diff})"
    elif score2 == score1:
        # 동점은 갱신 안 함
        assert res2["is_best"] is False, "동점인데 is_best=true"
    else:
        assert res2["is_best"] is False, f"점수 낮은데 is_best=true (diff={diff})"
        prev = res2.get("prev_best", {})
        assert prev.get("ex_score", 0) > score2, \
            f"prev_best({prev.get('ex_score')})가 현재 점수({score2})보다 낮거나 같음"
