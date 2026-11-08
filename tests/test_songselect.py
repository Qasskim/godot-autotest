# -*- coding: utf-8 -*-
"""곡 선택 화면 — 화면에 보이는 글자와 저장된 설정값으로 확인 (2026-11-08, 사용자 지시: 기능·데이터로 확인할 수 있는 건 전부 자동화).

곡 17개의 기대값은 채보 파일(.rgds)의 meta 에서 직접 읽는다. 소리·모양은 사람이 확인한다. 서버·계정은 쓰지 않는다(--no-server).
설정이 바뀌는 테스트는 끝에 원래 값으로 되돌린다(settings.cfg 는 격리 프로필 안).
"""
import glob
import json
import os
import re
import time

import pytest

import client
from godot_runner import GAME_PROJECT, GAME_APPDATA_DIR
from screen_helpers import labels, norm, press, ui, wait_until

SETTINGS_CFG = os.path.join(GAME_APPDATA_DIR, "RhythmGame_New", "settings.cfg")
KEYMODES = [4, 5, 6, 8]
DIFFS = ["EZ", "NM", "HD", "EX"]


def buttons() -> list:
    return client.screen_buttons()


def meta_of(res_path: str) -> dict:
    with open(os.path.join(GAME_PROJECT, res_path.replace("res://", "")), encoding="utf-8") as f:
        return json.load(f)["meta"]


def all_groups() -> dict:
    """공식 곡 폴더별 {(키, 난이도): meta} — 채보 파일에서 직접 읽은 기대값."""
    out = {}
    for d in sorted(glob.glob(os.path.join(GAME_PROJECT, "charts", "keysound", "*"))):
        files = {}
        for fp in glob.glob(os.path.join(d, "*_v8.rgds")):
            m = json.load(open(fp, encoding="utf-8"))["meta"]
            files[(int(m["keymode"]), m["difficulty"])] = m | {"_file": fp}
        if files:
            out[os.path.basename(d)] = files
    return out


def read_cfg() -> dict:
    """settings.cfg 의 'key=value' 줄을 문자열 그대로 읽는다(여러 줄 값은 첫 줄만)."""
    text = open(SETTINGS_CFG, encoding="utf-8").read()
    return dict(re.findall(r"^(\w+)=(.*)$", text, flags=re.M))


def open_select() -> None:
    client.navigate("song_select")
    assert client.wait_for_scene("SongSelect", timeout=15), "곡 선택 화면이 열리지 않았습니다"
    assert wait_until(lambda: client.songs()["count"] > 0, timeout=10)
    time.sleep(1.2)


def titles() -> list:
    return client.songs()["songs"]


def combo_buttons() -> tuple:
    b = buttons()
    km = next(x for x in b if re.fullmatch(r"\dK", x))
    df = next(x for x in b if x in DIFFS)
    return km, df


def reset_view() -> None:
    """정렬을 이름순 ▲, 조합을 4K EZ 로 돌려 놓는다."""
    open_select()
    for _ in range(3):
        if ui("select_sort_name") in buttons():
            break
        press(buttons()[buttons().index("▲" if "▲" in buttons() else "▼") - 1])
    if "▼" in buttons():
        press("▼")
    for _ in range(12):                      # 키 수·난이도 조합도 4K EZ 로 (조합은 화면을 나갔다 와도 마지막 곡 기준으로 복원된다)
        if combo_buttons() == ("4K", "EZ"):
            break
        press(combo_buttons()[0])
        if combo_buttons() != ("4K", "EZ"):
            press(combo_buttons()[1])
    assert combo_buttons() == ("4K", "EZ"), f"조합을 4K EZ 로 돌리지 못했습니다: {combo_buttons()}"


@pytest.fixture(autouse=True)
def _clean_view():
    reset_view()
    yield


@pytest.fixture(scope="module", autouse=True)
def _restore_view_at_end():
    yield
    reset_view()


# ── 1. 처음 들어왔을 때 ─────────────────────────────────────────────

def test_entry_shows_buttons_and_labels():
    b = buttons()
    for name in (ui("select_back"), ui("select_folder_official"), ui("select_folder_ucc"), ui("select_sort_name"), "▲", "4K", "EZ",
                 "Best Score", "라이벌", "PLAY", "-", "+"):
        assert name in b, f"'{name}' 버튼이 없습니다: {b}"
    for text in (ui("select_options_btn"), "프리 모드"):
        assert text in labels(), f"'{text}' 글자가 없습니다 — 화면: {labels()}"
    play = next(i for i in client.screen()["items"] if i["kind"] == "button" and i["text"] == "PLAY")
    assert play["disabled"] is False


def test_list_has_every_shipped_song_once_in_name_order():
    groups = all_groups()
    want = sorted(m[(4, "EZ")]["display_title"] for m in groups.values() if (4, "EZ") in m)
    got = titles()
    assert len(got) == len(set(got)), f"곡이 중복으로 나옵니다: {got}"
    assert got == want, f"곡 목록이 채보 파일의 4K EZ 곡과 다릅니다:\n화면 {got}\n파일 {want}"


def test_first_song_labels_match_chart_meta():
    paths = client.songs()["paths"]
    client.tap_song_at(0)
    time.sleep(0.3)
    m = meta_of(paths[0])
    assert m["display_title"] in labels()
    assert m["artist"] in labels()
    assert f"BPM {float(m['bpm'])}" in labels()
    assert f"Lv.{float(m['level'])} [{m['difficulty']}]" in labels()


def test_every_song_selected_shows_its_own_labels():
    s = client.songs()
    for i, path in enumerate(s["paths"]):
        client.tap_song_at(i)
        time.sleep(0.25)
        m = meta_of(path)
        got = labels()
        assert m["display_title"] in got and m["artist"] in got, f"{i}번 곡 제목·아티스트가 화면과 다릅니다: {got}"
        assert f"BPM {float(m['bpm'])}" in got, f"{i}번 곡 BPM 이 다릅니다: {got}"
        assert f"Lv.{float(m['level'])} [{m['difficulty']}]" in got, f"{i}번 곡 레벨·난이도가 다릅니다: {got}"


# ── 2. 정렬 ─────────────────────────────────────────────────────────

def test_name_sort_direction_toggle_reverses_the_list():
    asc = titles()
    press("▲")
    assert "▼" in buttons()
    assert titles() == list(reversed(asc)), "▼ 로 바꿨는데 목록이 거꾸로가 아닙니다"
    press("▼")
    assert titles() == asc


def test_sort_mode_cycles_name_difficulty_recent_and_back():
    order = [ui("select_sort_name"), ui("select_sort_difficulty"), ui("select_sort_recent"), ui("select_sort_name")]
    for step, want in enumerate(order):
        assert want in buttons(), f"{step}번째 정렬 방식 '{want}' 이 안 보입니다: {buttons()}"
        if step < 3:
            press(want)


def test_difficulty_sort_orders_by_level_then_name_both_directions():
    press(ui("select_sort_name"))
    assert ui("select_sort_difficulty") in buttons()
    groups = all_groups()
    rows = [(float(m[(4, "EZ")]["level"]), m[(4, "EZ")]["display_title"]) for m in groups.values() if (4, "EZ") in m]
    asc = [t for _, t in sorted(rows)]
    assert titles() == asc, f"난이도순(▲)이 레벨 오름차순·이름 순이 아닙니다:\n화면 {titles()}\n기대 {asc}"
    press("▲")
    desc = [t for _, t in sorted(rows, key=lambda r: (-r[0], r[1]))]
    assert titles() == desc, f"난이도순(▼)이 레벨 내림차순·같으면 이름순이 아닙니다:\n화면 {titles()}\n기대 {desc}"


def test_direction_is_kept_when_sort_mode_changes():
    press("▲")                                     # ▼
    press(ui("select_sort_name"))                  # 난이도순
    assert "▼" in buttons(), "정렬 방식을 바꿨는데 방향이 ▲ 로 돌아갔습니다"


def test_sort_choice_is_saved_and_kept_after_reentering():
    press(ui("select_sort_name"))
    press("▲")
    cfg = read_cfg()
    assert cfg["song_sort_mode"] == "1" and cfg["song_sort_reverse"] == "true", f"설정 파일에 정렬이 안 저장됐습니다: {cfg}"
    open_select()
    assert ui("select_sort_difficulty") in buttons() and "▼" in buttons(), f"다시 들어왔더니 정렬이 풀렸습니다: {buttons()}"


# ── 3. 키 수·난이도 순환 ────────────────────────────────────────────

def expected_titles(km: int, diff: str) -> list:
    return sorted(m[(km, diff)]["display_title"] for m in all_groups().values() if (km, diff) in m)


def model_press_key(state, combos):
    """사용자가 정한 규칙(2026-11-02): 키 수 버튼은 곡 목록에 있는 다음 키로 가고, 새 키에 지금 난이도가 없으면 그 키에 있는 난이도 중 가장 가까운(같으면 낮은 쪽) 것으로."""
    km, df = state
    kms = [k for k in KEYMODES if any(c[0] == k for c in combos)]
    km = kms[(kms.index(km) + 1) % len(kms)]
    ds = [d for d in DIFFS if (km, d) in combos]
    if df not in ds:
        df = min(ds, key=lambda d: (abs(DIFFS.index(d) - DIFFS.index(df)), DIFFS.index(d)))
    return km, df


def model_press_diff(state, combos):
    km, df = state
    ds = [d for d in DIFFS if any(c[1] == d for c in combos)]
    df = ds[(ds.index(df) + 1) % len(ds)]
    ks = [k for k in KEYMODES if (k, df) in combos]
    if km not in ks:
        km = min(ks, key=lambda k: (abs(KEYMODES.index(k) - KEYMODES.index(km)), KEYMODES.index(k)))
    return km, df


def shown_combo() -> tuple:
    km, df = combo_buttons()
    return int(km[0]), df


def test_key_and_difficulty_buttons_follow_the_nearest_combo_rule():
    """키 수 버튼과 난이도 버튼을 번갈아 24번 눌러 가며, 매번 화면의 조합이 규칙대로이고 곡 목록이 채보 파일에 그 조합이 있는 곡과 같은지 확인한다."""
    combos = {c for fs in all_groups().values() for c in fs}
    state = shown_combo()
    assert state == (4, "EZ"), f"처음 조합이 4K EZ 가 아닙니다: {state}"
    trail = [state]
    for i in range(24):
        if i % 3 == 2:
            press(combo_buttons()[1])
            state = model_press_diff(state, combos)
        else:
            press(combo_buttons()[0])
            state = model_press_key(state, combos)
        trail.append(state)
        assert shown_combo() == state, f"{i + 1}번째 누른 뒤 조합이 규칙과 다릅니다 — 지금까지 {trail}, 화면 {shown_combo()}"
        want = expected_titles(*state)
        assert titles() == want, f"{state} 목록이 다릅니다 — 화면 {titles()} / 기대 {want}"
        m = meta_of(client.songs()["paths"][titles().index(next(t for t in titles() if t in labels()))])
        assert (m["keymode"], m["difficulty"]) == state and f"Lv.{float(m['level'])} [{state[1]}]" in labels(), f"선택 곡 표시가 {state} 가 아닙니다: {labels()}"


def test_first_press_examples_from_4k_ez():
    press("4K")
    assert (combo_buttons()) == ("5K", "NM"), "4K EZ 에서 키 수를 누르면 5K 로 가고, 5K 에는 EZ 가 없어 가장 가까운 NM 이 되어야 합니다"
    press("5K")
    assert combo_buttons() == ("6K", "HD")


def test_changing_difficulty_keeps_the_same_song_selected():
    song = titles()[3]
    client.tap_song_at(3)
    time.sleep(0.3)
    press(combo_buttons()[1])
    assert combo_buttons() != ("4K", "EZ")
    assert song in labels(), f"난이도를 바꿨는데 선택 곡이 {song} 에서 바뀌었습니다: {labels()}"


# ── 4. 폴더 탭 ──────────────────────────────────────────────────────

def test_ucc_tab_is_coming_soon_and_keeps_official_list():
    before = titles()
    press(ui("select_folder_ucc"))
    time.sleep(0.4)
    assert titles() == before, "준비 중인 UCC 탭을 눌렀더니 곡 목록이 바뀌었습니다"
    assert client.scene() == "SongSelect"


# ── 5. 배속 ─────────────────────────────────────────────────────────

def speed_label() -> float:
    m = next(re.fullmatch(r"배속 ([\d.]+)x", l) for l in labels() if re.fullmatch(r"배속 ([\d.]+)x", l))
    return float(m.group(1))


def test_speed_buttons_step_by_quarter_and_save_per_song():
    first = speed_label()
    press("+")
    assert speed_label() == first + 0.25
    press("-")
    press("-")
    assert speed_label() == first - 0.25
    press("+")                                     # 원래 값으로


def test_speed_is_per_song_and_clamped_to_min_and_max():
    paths = client.songs()["paths"]
    client.tap_song_at(0)
    time.sleep(0.3)
    base0 = speed_label()
    for _ in range(45):
        press("+")
    assert speed_label() == 10.0, f"최대 배속이 10.0 이 아닙니다: {speed_label()}"
    client.tap_song_at(1)
    time.sleep(0.3)
    other = speed_label()
    assert other != 10.0, "첫 곡의 배속을 올렸는데 둘째 곡에도 적용됐습니다"
    client.tap_song_at(0)
    time.sleep(0.3)
    for _ in range(50):
        press("-")
    assert speed_label() == 0.25, f"최소 배속이 0.25 가 아닙니다: {speed_label()}"
    while speed_label() < base0:
        press("+")


# ── 6. 옵션 ─────────────────────────────────────────────────────────

def test_low_spec_toggle_is_saved_and_restored():
    before = read_cfg()["low_spec_mode"]
    press(ui("select_low_spec_toggle_short"))
    after = read_cfg()["low_spec_mode"]
    assert after != before, "저사양 모드를 눌렀는데 설정이 바뀌지 않았습니다"
    press(ui("select_low_spec_toggle_short"))
    assert read_cfg()["low_spec_mode"] == before


def test_note_random_dropdown_lists_none_and_random_only_and_saves_choice():
    # 드롭다운 순서(화면 위→아래): 0 고스트, 1 노트 랜덤, 2 목표 등급
    info = client.pick_option(1)
    assert info["items"] == [ui("select_note_random_none"), ui("select_note_random_random")], f"노트 랜덤 항목이 {info['items']} 입니다(S-RANDOM 은 목록에서 뺀 상태)"
    assert info["selected"] == ui("select_note_random_none")
    r = client.pick_option(1, ui("select_note_random_random"))
    assert r["ok"] and r["selected"] == ui("select_note_random_random")
    assert read_cfg()["note_random_mode"] == "1"
    client.pick_option(1, ui("select_note_random_none"))
    assert read_cfg()["note_random_mode"] == "0"


def test_target_grade_dropdown_has_none_plus_every_grade_and_saves_choice():
    info = client.pick_option(2)
    grades = ["MAX", "S++", "S+", "S", "A", "B", "C", "D"]      # F 는 기준 점수가 없어 목표로 고를 수 없다
    assert info["items"][0] == ui("select_target_grade_none") and info["items"][1:] == grades, f"목표 등급 항목이 {info['items']} 입니다"
    r = client.pick_option(2, "S+")
    assert r["ok"] and r["selected"] == "S+"
    assert read_cfg()["target_grade"] == '"S+"'
    client.pick_option(2, ui("select_target_grade_none"))
    assert read_cfg()["target_grade"] == '""'


def test_three_dropdowns_are_visible_and_ghost_defaults_to_first_item():
    info = client.pick_option(0)
    assert info["count"] == 3, f"화면에 드롭다운이 {info['count']}개 보입니다(고스트·노트 랜덤·목표 등급 3개여야 합니다)"
    assert info["items"] and info["selected"] == info["items"][0], f"고스트 기본 값이 첫 항목이 아닙니다: {info}"


# ── 7. 뒤로·PLAY ────────────────────────────────────────────────────

def test_back_button_returns_to_main_menu():
    press(ui("select_back"))
    assert client.wait_for_scene("MainMenu", timeout=10)


def test_play_opens_game_scene():
    client.tap_song_at(2)
    time.sleep(0.3)
    press("PLAY")
    assert client.wait_for_scene("GameScene", timeout=30), f"PLAY 를 눌렀는데 게임 화면이 안 열립니다 — 지금 화면: {client.scene()}"
