# -*- coding: utf-8 -*-
"""서버 데이터가 있을 때의 화면 — Best Score 1위, 전체 리더보드 줄·R 표시, 라이벌 등록·해제(리더보드 줄 / 관리 팝업), 라이벌 탭, 오류 문구 (2026-11-08).

기개발 서버에 그대로 접속하고 고정 테스트 계정 3·4(·5)로 로그인한다. 만든 기록·라이벌은 cleanup_server.py(장부)가 지운다.
시험 기록은 배포 곡 'ARTCORE' 4K EZ 한 곡(pc 플랫폼)에만 만든다 — 이 곡의 기존 서버 기록은 없다(2026-11-08 조회).
"""
import time

import pytest

import client
from screen_helpers import labels, labels_and_inner, norm, press, ui, wait_until
from server_helpers import ACCT_A, ACCT_B, ACCT_C, db, login, mix, payload, submit
from test_server_social import account_row, remove_all_rivals

pytestmark = pytest.mark.server

SONG_ID = "keysound_artcore_Gmin_174_006_artcore_Gmin_174_006_EZ_v8"
CHART = (SONG_ID, "EZ", 0)


def buttons() -> list:
    return client.screen_buttons()


def submit_pc(acct: int, judgments: list) -> dict:
    login(acct)
    r = submit(payload(CHART, judgments, platform="pc"))
    assert r["ok"], r
    return r["response"]


def total_notes() -> int:
    """서버가 요구하는 판정 개수 — 등록된 총 노트 수에 레인믹스 구간의 기본 쪽 노트를 더한 값(레인믹스를 고르지 않은 플레이)."""
    row = db(f"select total_notes, lanemix_sections from public.charts where song_id='{SONG_ID}' and difficulty='EZ'")[0]
    return int(row["total_notes"]) + sum(int(sec["base"]) for sec in (row["lanemix_sections"] or []))


@pytest.fixture(scope="module")
def seeded():
    """A: Wow(전체-20)·Great15·Good5, B: 전부 Wow. 마지막은 A 로 로그인한 상태."""
    total = total_notes()
    ex_max = total * 3
    a_ex = 3 * (total - 20) + 15 * 2
    login(ACCT_A)
    client.clear_server_records()
    a_resp = submit_pc(ACCT_A, mix(wow=total - 20, great=15, good=5))
    b_resp = submit_pc(ACCT_B, mix(wow=total))
    login(ACCT_A)
    remove_all_rivals()
    return {"a": account_row(ACCT_A), "b": account_row(ACCT_B), "a_resp": a_resp, "b_resp": b_resp,
            "total": total, "ex_max": ex_max, "a_ex": a_ex, "a_rate": f"{a_ex / ex_max * 100:.2f}%"}


def open_select_on_artcore() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15)
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)
    titles = client.songs()["songs"]
    client.tap_song_at(titles.index("ARTCORE"))
    time.sleep(0.5)
    # 4K EZ 조합이 아니면 맞춘다
    for _ in range(12):
        b = buttons()
        if "4K" in b and "EZ" in b:
            break
        press(next(x for x in b if x[-1] == "K" and x[:-1].isdigit()))
    time.sleep(0.8)


def open_leaderboard() -> None:
    open_select_on_artcore()
    press(ui("select_tab_world"))
    press(ui("select_leaderboard_btn"))
    assert client.wait_for_scene("Leaderboard", timeout=10)
    assert wait_until(lambda: "#1" in labels() or "#1" in buttons(), timeout=10), f"리더보드 줄이 안 나옵니다 — 화면: {labels()} {buttons()}"
    time.sleep(0.4)


# ── Best Score 탭 ───────────────────────────────────────────────────

def test_best_score_tab_shows_current_number_one(seeded):
    open_select_on_artcore()
    press(ui("select_tab_world"))
    b = seeded["b"]
    assert wait_until(lambda: b["name"] in labels(), timeout=10), f"1위 닉네임 {b['name']} 이 안 보입니다: {labels()}"
    want = f"{seeded['ex_max']} / {seeded['ex_max']}"
    assert want in labels(), f"1위 점수가 '{want}' 이 아닙니다: {labels()}"
    assert norm(f"100.00%  {seeded['b_resp']['record']['grade']}") in labels(), f"1위 달성률·등급이 다릅니다: {labels()}"


# ── 전체 리더보드 화면 ──────────────────────────────────────────────

def test_leaderboard_rows_rank_name_rate_grade_date_and_hint(seeded):
    open_leaderboard()
    a, b = seeded["a"], seeded["b"]
    rows = labels_and_inner()
    assert ui("leaderboard_title") in rows and ui("leaderboard_rival_hint") in rows, f"제목·안내 문구가 없습니다: {rows}"
    assert b["name"] in rows and a["name"] in rows
    first = next(i for i in client.screen()["items"] if i["kind"] == "button" and i["text"] == "#1")
    assert first["inner"][:4] == ["#1", b["name"], "100.00%", seeded["b_resp"]["record"]["grade"]], f"1위 줄이 B 의 기록이 아닙니다: {first['inner']}"
    assert "100.00%" in rows and seeded["a_rate"] in rows, f"달성률 칸이 다릅니다: {rows}"
    assert seeded["b_resp"]["record"]["grade"] in rows and seeded["a_resp"]["record"]["grade"] in rows
    assert "#2" in rows, "내 줄(#2)은 버튼이 아니라 글자로 보여야 합니다"
    assert "#1" in buttons(), "다른 사람 줄(#1)은 눌러서 라이벌을 고르는 버튼이어야 합니다"
    assert "#2" not in buttons(), "내 줄이 버튼으로 보입니다"
    assert any(r.startswith("20") and len(r) == 10 and r[4] == "-" for r in rows), f"플레이 날짜 칸이 없습니다: {rows}"


def test_leaderboard_row_add_and_remove_rival_with_confirm(seeded):
    remove_all_rivals()
    open_leaderboard()
    b = seeded["b"]
    press("#1")
    add_text = norm(ui("leaderboard_rival_add_confirm") % b["name"])
    assert wait_until(lambda: add_text in labels_and_inner(), timeout=5), f"등록 확인 문구가 안 뜹니다: {labels_and_inner()}"
    assert ui("select_rival_add_btn") in buttons() and ui("settings_cancel") in buttons()
    press(ui("settings_cancel"))
    time.sleep(0.4)
    assert ui("leaderboard_rival_mark") not in labels_and_inner(), "취소했는데 R 표시가 붙었습니다"
    press("#1")
    press(ui("select_rival_add_btn"))
    assert wait_until(lambda: ui("leaderboard_rival_mark") in labels_and_inner(), timeout=10), f"등록했는데 R 표시가 안 붙습니다: {labels_and_inner()}"
    assert client.service("rivals")["rivals"][0]["rival_user_id"] == b["id"], "서버에 라이벌이 등록되지 않았습니다"
    press("#1")
    remove_text = norm(ui("leaderboard_rival_remove_confirm") % b["name"])
    assert wait_until(lambda: remove_text in labels_and_inner(), timeout=5), f"해제 확인 문구가 안 뜹니다: {labels_and_inner()}"
    press(ui("select_rival_remove_btn"))
    assert wait_until(lambda: ui("leaderboard_rival_mark") not in labels_and_inner(), timeout=10), f"해제했는데 R 표시가 남았습니다: {labels_and_inner()}"
    assert client.service("rivals")["rivals"] == []


def test_leaderboard_back_returns_to_song_select(seeded):
    open_leaderboard()
    press(ui("leaderboard_back"))
    assert client.wait_for_scene("SongSelect", timeout=10)


# ── 라이벌 관리 팝업·라이벌 탭 ──────────────────────────────────────

def open_manage() -> None:
    open_select_on_artcore()
    press(ui("select_tab_rival"))
    time.sleep(0.5)
    press(ui("select_rival_manage_btn"))
    time.sleep(0.4)


def test_manage_popup_add_by_nickname_lists_rival_and_rival_tab_shows_record(seeded):
    b = seeded["b"]
    open_manage()
    try:
        assert client.fill_input(b["name"])
        press(ui("select_rival_add_btn"))
        assert wait_until(lambda: b["name"] in labels() and ui("select_rival_remove_btn") in buttons(), timeout=10), f"등록한 라이벌이 목록에 안 나옵니다: {labels()}"
        assert [e for e in client.screen()["items"] if e["kind"] == "edit"][0]["text"] == "", "등록 뒤 검색창이 비워지지 않았습니다"
        press(ui("settings_close"))
        time.sleep(0.4)
        assert norm(f"{ui('select_tab_world')} (1/2)") in labels(), f"라이벌 탭 첫 대상이 Best Score (1/2) 가 아닙니다: {labels()}"
        press("▶")
        assert wait_until(lambda: norm(f"{b['name']} (2/2)") in labels(), timeout=5), f"▶ 를 눌렀는데 라이벌 B (2/2) 가 안 나옵니다: {labels()}"
        want = f"{seeded['ex_max']} / {seeded['ex_max']}"
        assert wait_until(lambda: want in labels(), timeout=10), f"라이벌 점수 '{want}' 가 안 나옵니다: {labels()}"
        assert norm(f"100.00%  {seeded['b_resp']['record']['grade']}") in labels()
        press("▶")
        assert norm(f"{ui('select_tab_world')} (1/2)") in labels(), "▶ 끝에서 처음으로 돌아가지 않습니다"
        press("◀")
        assert norm(f"{b['name']} (2/2)") in labels(), "◀ 로 거꾸로 돌아가지 않습니다"
        info = client.pick_option(0)
        assert any(b["name"] in i for i in info["items"]), f"고스트 드롭다운에 라이벌 {b['name']} 이 없습니다: {info['items']}"
    finally:
        remove_all_rivals()


def test_manage_popup_remove_button_removes_rival(seeded):
    b = seeded["b"]
    assert client.service("add_rival", name=b["name"])["ok"]
    open_manage()
    assert b["name"] in labels()
    press(ui("select_rival_remove_btn"))
    assert wait_until(lambda: ui("select_rival_remove_btn") not in buttons(), timeout=10), f"해제했는데 목록에 남았습니다: {labels()}"
    assert client.service("rivals")["rivals"] == []


def test_manage_popup_error_texts_for_self_unknown_and_limit(seeded):
    a, c = seeded["a"], account_row(ACCT_C)
    open_manage()
    try:
        assert client.fill_input(a["name"])
        press(ui("select_rival_add_btn"))
        assert wait_until(lambda: norm(ui("err_rival_self")) in labels(), timeout=8), f"자기 자신 등록 오류 문구가 없습니다: {labels()}"
        press(ui("settings_confirm"))
        assert client.fill_input("없는닉네임_autotest_zzz")
        press(ui("select_rival_add_btn"))
        assert wait_until(lambda: norm(ui("err_rival_not_found")) in labels(), timeout=8), f"없는 닉네임 오류 문구가 없습니다: {labels()}"
        press(ui("settings_confirm"))
        for n in (ACCT_B, 1, 2, 6, 7):
            assert client.service("add_rival", name=account_row(n)["name"])["ok"]
        assert client.fill_input(c["name"])
        press(ui("select_rival_add_btn"))
        assert wait_until(lambda: norm(ui("err_rival_limit")) in labels(), timeout=8), f"6번째 등록 오류 문구가 없습니다: {labels()}"
    finally:
        remove_all_rivals()
