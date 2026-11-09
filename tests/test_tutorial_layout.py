# -*- coding: utf-8 -*-
"""튜토리얼 4단계(레인믹스 순차 체험) 노트 배치 튐 회귀 시험 (2026-11-10).

배경: 노트는 판정선 3초 전에 만들어지는데 지금 키 수로 만들면, 구간 중 lanemix_step(키 수 변경)과 구간 끝에서 화면의 노트가 한꺼번에
바뀌며 위치가 튀었다(수정 전 측정: 단계 시각 6557·9033·11524ms, 구간 끝 14541ms 에 노트 전부 배치 바뀜). 수정 후에는 어떤 노트도
처음 보인 뒤 그려진 x(cx)가 바뀌지 않아야 한다. 안내 버튼이 나오면 눌러 수락한다.
이 시험의 값(관찰 상한 17500ms = 4단계 채보 마지막 노트 16500ms + 1000ms)은 사용자가 정한 값이 아니라 시험 작성자가 정했다. 서버·계정은 쓰지 않는다.
측정 도구는 probe_tutorial_layout.py 와 같다.
"""
import time

import client
from screen_helpers import enter_tutorial_via_settings, jump_to_stage, press

CHART_END_MS = 17500


def test_stage4_notes_never_change_layout_after_appearing():
    enter_tutorial_via_settings()
    jump_to_stage(3, 1)
    press("START")
    track = {}
    clicked = False
    deadline = time.time() + 60
    while time.time() < deadline:
        st = client._req("GET", "/tutorial_practice_state")
        if not clicked and st.get("prompt_state") in ("OFFER", "READY"):
            client.click(st["button_x"], st["button_y"])
            clicked = True
        for n in st.get("notes", []):
            track.setdefault((round(n["timing_ms"], 1), n["lane"]), []).append((n["key_mode"], n["cx"]))
        if st.get("finished") or st.get("position_ms", 0) > CHART_END_MS:
            break
        time.sleep(0.03)
    assert clicked, "레인믹스 안내 버튼을 누르지 못했다(수락 실패)"
    assert track, "노트를 한 개도 못 봤다(관찰 실패)"
    bad = {k: sorted(set(v)) for k, v in track.items() if len(set(v)) > 1}
    assert not bad, f"처음 보인 뒤 배치가 바뀐 노트가 있다: {bad}"
