# -*- coding: utf-8 -*-
"""레인믹스 구간 끝 직후 노트 배치 튐 회귀 시험 (2026-11-10).

배경: 노트는 판정선 3초 전에 만들어지는데, 구간 도중에 만들어진 '구간 끝 이후의 기본 노트'가 구간 키 수(예: 5키)로 만들어져
5키 배치로 내려오다가 구간 끝에서 기본 키 수(4키)로 한꺼번에 바뀌어 위치가 튀었다(GameManager._do_spawn_note 의 key_mode).
방식: 수락한 구간이 끝나기 전부터 끝난 뒤까지 /debug_notes 를 계속 읽어, 구간 끝 이후에 칠 기본 노트가 처음 보일 때부터 끝까지
기본 키 수의 배치(key_mode)로 그려지는지 본다. 한 번이라도 다른 key_mode 로 보이면 실패.
이 시험의 값(곡·키 수·난이도·관찰 범위 1500ms)은 사용자가 지정한 것이 아니라 시험 작성자가 정했다. 서버·계정은 쓰지 않는다.
측정 도구는 probe_lanemix_boundary.py·probe_lanemix_visual.py 와 같다.
"""
import time

import pytest

import client
import probe_lanemix_boundary as pb

OBSERVE_AFTER_END_MS = 1500


@pytest.fixture(autouse=True)
def _leave_after():
    yield
    pb.COMBO = None
    try:
        pb.leave()
    except Exception:  # noqa: BLE001 — 정리 실패가 시험 결과를 덮지 않게
        pass
    client.autolanemix(True)


def test_notes_after_section_end_keep_base_layout():
    pb.COMBO = ("4K", "EZ")
    pb.start_song("CITY POP")
    p = pb.wait_state("OFFER", timeout=170)
    sec_start = p["section_starts"][0]
    chart = pb.find_chart(sec_start)
    assert chart is not None, f"구간 시작 {sec_start} 의 채보를 못 찾음"
    sec_end = [e["timing_ms"] for e in chart["gimmick_events"] if e.get("action") == "lanemix_end"][0]
    base_mode = p["from_mode"]
    assert p["to_mode"] != base_mode, "구간 키 수가 기본 키 수와 같으면 이 시험이 의미가 없다"
    client.click(p["button_x"], p["button_y"])
    pb.wait_state("RETURN", timeout=200)
    seen = {}      # (timing_ms, lane) -> 본 key_mode 집합
    deadline = time.time() + 40
    while time.time() < deadline:
        st = client.notes_on_screen()
        for n in st["notes"]:
            if sec_end <= n["timing_ms"] <= sec_end + OBSERVE_AFTER_END_MS and n["lane"] < 16:
                seen.setdefault((round(n["timing_ms"], 1), n["lane"]), set()).add(n["key_mode"])
        if st["music_ms"] > sec_end + OBSERVE_AFTER_END_MS + 300:
            break
        time.sleep(0.03)
    assert seen, "구간 끝 이후 노트를 한 개도 못 봤다(관찰 실패)"
    bad = {k: sorted(v) for k, v in seen.items() if v != {base_mode}}
    assert not bad, f"구간 끝 이후 기본 노트가 기본 {base_mode}키가 아닌 배치로 보였다: {bad}"
