# -*- coding: utf-8 -*-
"""설정 화면 — 탭 4개(계정·게임·사운드·크레딧)의 글자·버튼·저장값을 화면에 보이는 글자와 저장 파일로 확인 (2026-11-08).

서버 없이(--no-server) 게스트(익명) 상태. 로그아웃·계정 탈퇴는 로그인한 계정에서만 보이므로 test_server_settings.py 가 맡는다.
설정을 바꾸는 테스트는 끝에 원래 값으로 되돌린다. 소리가 실제로 나는지·모양은 사람이 확인한다.
"""
import json
import os
import re
import time

import pytest

import client
from godot_runner import GAME_APPDATA_DIR, GAME_PROJECT
from screen_helpers import labels, norm, press, ui, wait_until

APP = os.path.join(GAME_APPDATA_DIR, "RhythmGame_New")
TABS_KO = [ui("settings_account_tab"), ui("settings_game_tab"), ui("settings_sound_tab"), ui("settings_credits_tab")]


def buttons() -> list:
    return client.screen_buttons()


def cfg() -> dict:
    text = open(os.path.join(APP, "settings.cfg"), encoding="utf-8").read()
    return dict(re.findall(r"^(\w+)=(.*)$", text, flags=re.M))


def profile() -> dict:
    return json.load(open(os.path.join(APP, "profile.json"), encoding="utf-8"))


def open_settings(tab: str = "") -> None:
    client.navigate("main_menu")
    assert client.wait_for_scene("MainMenu", timeout=15)
    time.sleep(0.8)
    client.tap_mainmenu_settings()
    assert client.wait_for_scene("Settings", timeout=10)
    time.sleep(0.8)
    if tab:
        assert client.select_tab(tab), f"'{tab}' 탭이 없습니다: {client.tabs()}"
        time.sleep(0.4)


# ── 탭 ──────────────────────────────────────────────────────────────

def test_four_tabs_in_order_and_account_tab_selected_first():
    open_settings()
    assert client.tabs() == [(TABS_KO[0], True), (TABS_KO[1], False), (TABS_KO[2], False), (TABS_KO[3], False)], client.tabs()


def test_each_tab_shows_only_its_own_content():
    open_settings()
    expect = {
        TABS_KO[0]: [ui("settings_nickname_btn")],
        TABS_KO[1]: [ui("settings_calibrate_btn"), ui("settings_tutorial_btn")],
        TABS_KO[2]: [ui("settings_eq_title")],
        TABS_KO[3]: ["Galmuri (font) - SIL Open Font License 1.1", "Godot Engine - MIT License"],
    }
    for tab, mine in expect.items():
        assert client.select_tab(tab)
        time.sleep(0.3)
        assert [t for t, sel in client.tabs() if sel] == [tab]
        for name in mine:
            assert name in buttons(), f"'{tab}' 탭에 '{name}' 버튼이 없습니다: {buttons()}"
        others = [n for t, ns in expect.items() if t != tab for n in ns]
        for name in others:
            assert name not in buttons(), f"'{tab}' 탭에 다른 탭의 '{name}' 버튼이 보입니다"
        assert ui("settings_back_btn") in buttons(), f"'{tab}' 탭에서 돌아가기 버튼이 안 보입니다"


def test_back_button_returns_to_main_menu_from_every_tab():
    for tab in TABS_KO:
        open_settings(tab)
        press(ui("settings_back_btn"))
        assert client.wait_for_scene("MainMenu", timeout=10), f"'{tab}' 탭에서 돌아가기가 메인 메뉴로 가지 않습니다"


# ── 계정 탭 ─────────────────────────────────────────────────────────

def test_account_tab_guest_shows_nickname_google_link_and_no_logout_or_delete():
    open_settings()
    name = profile()["display_name"]
    assert norm(ui("settings_nickname_label") % name) in labels(), f"닉네임 줄이 '{name}' 이 아닙니다: {labels()}"
    assert ui("settings_nickname_btn") in buttons() and ui("login_pc_google_btn") in buttons()
    for hidden in (ui("settings_logout_btn"), ui("settings_delete_account_btn"), ui("settings_platform_link_btn"), ui("settings_auto_rotate_toggle")):
        assert hidden not in buttons(), f"게스트·PC 에서는 '{hidden}' 가 보이면 안 됩니다"


def test_nickname_popup_opens_prefilled_and_cancel_keeps_name():
    open_settings()
    name = profile()["display_name"]
    press(ui("settings_nickname_btn"))
    time.sleep(0.4)
    assert ui("settings_nickname_popup_title") in labels()
    edit = [i for i in client.screen()["items"] if i["kind"] == "edit"][0]
    assert edit["text"] == name, f"입력창이 지금 닉네임 '{name}' 으로 채워져 있지 않습니다: {edit}"
    assert ui("settings_apply") in buttons() and ui("settings_cancel") in buttons()
    assert client.fill_input("바꾸다만이름")
    press(ui("settings_cancel"))
    time.sleep(0.3)
    assert ui("settings_nickname_popup_title") not in labels()
    assert norm(ui("settings_nickname_label") % name) in labels()
    assert profile()["display_name"] == name


def test_nickname_popup_invalid_names_show_errors_and_valid_name_is_saved_then_restored():
    open_settings()
    old = profile()["display_name"]
    press(ui("settings_nickname_btn"))
    time.sleep(0.4)
    try:
        assert client.fill_input("")
        press(ui("settings_apply"))
        assert norm(ui("err_nickname_length")) in labels()
        press(ui("settings_confirm"))
        assert client.fill_input("a@b#c")
        press(ui("settings_apply"))
        assert norm(ui("err_nickname_chars")) in labels()
        press(ui("settings_confirm"))
        assert profile()["display_name"] == old, "오류가 났는데 닉네임이 저장됐습니다"
        assert client.fill_input("새이름")
        press(ui("settings_apply"))
        assert wait_until(lambda: norm(ui("settings_nickname_label") % "새이름") in labels(), timeout=8), f"닉네임 줄이 바뀌지 않습니다: {labels()}"
        assert profile()["display_name"] == "새이름"
    finally:
        if profile()["display_name"] != old:
            if ui("settings_nickname_popup_title") not in labels():
                press(ui("settings_nickname_btn"))
            client.fill_input(old)
            press(ui("settings_apply"))
            wait_until(lambda: profile()["display_name"] == old, timeout=8)
    assert profile()["display_name"] == old


# ── 게임 탭 ─────────────────────────────────────────────────────────

def test_game_tab_audio_offset_matches_saved_calibration():
    text = open(os.path.join(APP, "calibration.cfg"), encoding="utf-8").read()
    ms = float(re.search(r"user_calibration_ms=(-?[\d.]+)", text).group(1))
    client.calibration(ms)      # 매 시험 전에 보정이 0으로 돌아가므로(conftest, 2026-11-10) 저장된 값을 지금 값으로 맞춘 뒤 화면과 비교한다
    open_settings(ui("settings_game_tab"))
    assert norm(ui("settings_audio_offset") % ms) in labels(), f"오디오 오프셋 줄이 저장값 {ms} 와 다릅니다: {labels()}"
    assert ui("settings_language_label") in labels() and ui("settings_visual_theme_label") in labels()


def test_language_dropdown_lists_korean_and_english_and_switching_translates_screen():
    open_settings(ui("settings_game_tab"))
    info = client.pick_option(0)
    assert info["items"] == ["한국어", "English"] and info["selected"] == "한국어", info
    en_tabs = [ui("settings_account_tab", "en"), ui("settings_game_tab", "en"), ui("settings_sound_tab", "en"), ui("settings_credits_tab", "en")]
    try:
        assert client.pick_option(0, "English")["ok"]
        assert wait_until(lambda: [t for t, _ in client.tabs()] == en_tabs, timeout=8), f"영어로 바꿨는데 탭 제목이 안 바뀝니다: {client.tabs()}"
        assert open(os.path.join(APP, "lang_pref.txt"), encoding="utf-8").read().strip() == "en"
        assert ui("settings_back_btn", "en") in buttons()
    finally:
        client.select_tab(en_tabs[1])
        time.sleep(0.4)
        client.pick_option(0, "한국어")
        wait_until(lambda: [t for t, _ in client.tabs()] == TABS_KO, timeout=8)
    assert open(os.path.join(APP, "lang_pref.txt"), encoding="utf-8").read().strip() == "ko"


def test_visual_theme_dropdown_lists_three_themes_and_switch_is_saved_then_restored():
    open_settings(ui("settings_game_tab"))
    info = client.pick_option(1)
    assert info["items"] == ["아스트랄 오션", "코스믹 네온", "어비스 에테르"], info
    before = cfg()["visual_theme"]
    try:
        assert client.pick_option(1, "코스믹 네온")["ok"]
        assert wait_until(lambda: cfg()["visual_theme"] == '"cosmic_neon"', timeout=8), f"테마가 저장되지 않았습니다: {cfg()['visual_theme']}"
    finally:
        client.select_tab(ui("settings_game_tab"))
        time.sleep(0.5)
        client.pick_option(1, "아스트랄 오션")
        wait_until(lambda: cfg()["visual_theme"] == before, timeout=8)
    assert cfg()["visual_theme"] == before


# ── 사운드 탭 ───────────────────────────────────────────────────────

ROWS = [("bgm", ui("settings_bgm_label")), ("sfx", ui("settings_sfx_label")),
        ("keysound", ui("settings_keysound_label")), ("event_sfx", ui("settings_event_sfx_label"))]


def title_of(label: str) -> str:
    return next(b for b in buttons() if b == label or b.startswith(label + " ["))


@pytest.mark.parametrize("n,row", list(enumerate(ROWS)))
def test_sound_row_slider_title_toggle_and_saved_values(n, row):
    key, label = row
    open_settings(ui("settings_sound_tab"))
    start = float(cfg()[f"{key}_volume"])
    assert title_of(label) == f"{label} [{round(start * 100)}%]", f"{label} 제목이 저장값 {start} 와 다릅니다: {title_of(label)}"
    try:
        assert client.set_slider(n, 0.5)["ok"]
        assert title_of(label) == f"{label} [50%]" and float(cfg()[f"{key}_volume"]) == 0.5
        assert client.set_slider(n, 0.0)["ok"] and title_of(label) == f"{label} [0%]"
        assert client.set_slider(n, 1.0)["ok"] and title_of(label) == f"{label} [100%]"
        assert client.slider_alphas()[n] == 1.0
        press(title_of(label))                                 # 끄기: -/슬라이더/+ 행이 접혀 안 보이고(0.5초) 음소거가 저장된다
        time.sleep(0.9)
        assert cfg()[f"{key}_muted"] == "true", f"끄기(음소거)가 저장되지 않았습니다: {cfg()[f'{key}_muted']}"
        assert client.slider_alphas()[n] == 0.0, "음소거했는데 볼륨 슬라이더 행이 접히지 않았습니다"
        assert title_of(label) == label, f"음소거 중에는 제목에 퍼센트가 없어야 합니다: {title_of(label)}"
        press(title_of(label))
        time.sleep(0.9)
        assert cfg()[f"{key}_muted"] == "false" and client.slider_alphas()[n] == 1.0, "다시 켰는데 볼륨 줄이 펼쳐지지 않았습니다"
    finally:
        if cfg()[f"{key}_muted"] == "true":                   # 중간에 실패해도 음소거를 켜 둔 채 끝나지 않게 되돌린다
            press(title_of(label))
            time.sleep(0.9)
        client.set_slider(n, start)
    assert float(cfg()[f"{key}_volume"]) == pytest.approx(start) and cfg()[f"{key}_muted"] == "false"


def test_sound_row_plus_and_minus_buttons_step_five_percent_and_clamp():
    """화면의 첫 '-' '+' 버튼이 BGM 줄이다."""
    label = ui("settings_bgm_label")
    open_settings(ui("settings_sound_tab"))
    start = float(cfg()["bgm_volume"])
    try:
        client.set_slider(0, 1.0)
        press("+")
        assert client.sliders()[0] == 1.0, "100% 에서 + 를 눌렀더니 값이 올라갔습니다"
        press("-")
        assert client.sliders()[0] == pytest.approx(0.95) and title_of(label) == f"{label} [95%]"
        press("+")
        assert client.sliders()[0] == pytest.approx(1.0)
        client.set_slider(0, 0.0)
        press("-")
        assert client.sliders()[0] == 0.0, "0% 에서 - 를 눌렀더니 값이 내려갔습니다"
    finally:
        client.set_slider(0, start)


def test_equalizer_popup_has_ten_bands_saves_gain_resets_and_closes():
    open_settings(ui("settings_sound_tab"))
    base = len(client.sliders())
    press(ui("settings_eq_title"))
    time.sleep(0.5)
    assert len(client.sliders()) == base + 10, f"이퀄라이저 팝업에 슬라이더 10개가 보여야 합니다: {len(client.sliders()) - base}"
    for hz in ["31", "62", "125", "250", "500", "1k", "2k", "4k", "8k", "16k"]:
        assert hz in labels(), f"주파수 '{hz}' 가 안 보입니다: {labels()}"
    assert ui("settings_eq_reset") in buttons() and ui("settings_confirm") in buttons()
    band = base + 2
    assert client.set_slider(band, 5.0)["ok"]
    assert "+5" in labels(), f"밴드를 +5 로 올렸는데 '+5' 표시가 없습니다: {labels()}"
    assert "5" in cfg()["eq_gains_db"]
    client.set_slider(band, 99.0)
    assert client.sliders()[band] == 6.0, "밴드 최대값이 +6 이 아닙니다"
    client.set_slider(band, -99.0)
    assert client.sliders()[band] == -6.0, "밴드 최소값이 -6 이 아닙니다"
    press(ui("settings_eq_reset"))
    assert all(v == 0.0 for v in client.sliders()[base:base + 10]), "초기화했는데 밴드 값이 0 이 아닙니다"
    assert all(float(x) == 0.0 for x in re.findall(r"-?\d+\.?\d*", cfg()["eq_gains_db"])), f"저장된 밴드 값이 0 이 아닙니다: {cfg()['eq_gains_db']}"
    press(ui("settings_confirm"))
    time.sleep(0.4)
    assert len(client.sliders()) == base, "확인을 눌렀는데 이퀄라이저 팝업이 남아 있습니다"


# ── 크레딧 탭 ───────────────────────────────────────────────────────

def test_credits_tab_body_and_license_popups_open_and_close():
    open_settings(ui("settings_credits_tab"))
    assert any("ASTRAL RAIN" in l and "KOREA NOTE DETONATION SQUAD" in l for l in labels()), f"크레딧 본문이 안 보입니다: {labels()}"
    galmuri = open(os.path.join(GAME_PROJECT, "assets", "fonts", "galmuri", "OFL_LICENSE_Galmuri.txt"), encoding="utf-8").read()
    first_line = norm(galmuri.splitlines()[0])
    press("Galmuri (font) - SIL Open Font License 1.1")
    time.sleep(0.4)
    assert any(first_line in l for l in labels()), f"Galmuri 라이선스 전문 첫 줄이 안 보입니다: {labels()}"
    press(ui("settings_confirm"))
    time.sleep(0.3)
    assert not any(first_line in l for l in labels()), "확인을 눌렀는데 라이선스 팝업이 남아 있습니다"
    press("Godot Engine - MIT License")
    time.sleep(0.4)
    assert any("MIT" in l or "Permission is hereby granted" in l for l in labels()), f"Godot 라이선스 전문이 안 보입니다: {labels()[:6]}"
    press(ui("settings_confirm"))
