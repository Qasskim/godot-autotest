# -*- coding: utf-8 -*-
"""모듈 6 — 채보·곡 폴더 데이터 검증 (기준: Godot/docs/DESIGN.md §8 채보 포맷·곡 폴더 구조, §9 레인믹스, §14 수록곡).

게임 창·서버·Godot 없이 파일만 읽는다(읽기 전용). 대상은 게임 프로젝트의 charts/keysound(수록 17곡)와 charts/Tutorial이다.
(안드로이드 빌드 폴더 안의 복사본은 원본이 아니므로 세지 않는다.)
검사 하나가 TC 하나이고, 실패하면 어느 채보·노트가 어긋났는지 앞쪽 몇 개를 메시지에 담는다.
"""
import glob
import json
import os
from collections import defaultdict

import pytest
from godot_runner import GAME_PROJECT

pytestmark = pytest.mark.no_server

CHARTS = os.path.join(GAME_PROJECT, "charts")
DIFFS = ["EZ", "NM", "HD", "EX"]
NOTE_TYPES = {"tap", "long", "slide", "drag"}                       # DESIGN §7
GIMMICK_ACTIONS = {"lanemix_start", "lanemix_end", "lanemix_step", "screen_flash"}   # DESIGN §8
TARGET_MODES = {4, 5, 6, 8, 16, -1, -2}                              # DESIGN §9 (-1 키모드 랜덤, -2 슈퍼랜덤)
KEYMODE_OF_DIFF = {"EZ": 4, "NM": 5, "HD": 6, "EX": 6}              # DESIGN §14 곡 선택: EZ는 4키, NM은 5키, HD·EX는 6키
# DESIGN §8 수록곡 표시 제목(올 대문자 대장르 표). METAL B는 2026-11-05 출시 제외라 A·C만.
DESIGN_TITLES = {"ROCK", "METAL A", "METAL C", "PUNK A", "PUNK B", "DNB A", "DNB B", "TECHNO A", "TECHNO B",
                 "HOUSE", "TRANCE", "CHIPTUNE", "CITY POP", "SYNTHWAVE", "ARTCORE", "GABBER", "HARDSTYLE", "AMBIENT"}

SONG_DIRS = sorted(d for d in glob.glob(os.path.join(CHARTS, "keysound", "*")) if os.path.isdir(d))
SHIPPED = sorted(glob.glob(os.path.join(CHARTS, "keysound", "*", "*_v8.rgds")))        # EZ/NM/HD/EX
TUTORIAL = sorted(glob.glob(os.path.join(CHARTS, "Tutorial", "*.rgds")))
ALL_RGDS = sorted(glob.glob(os.path.join(CHARTS, "keysound", "*", "*.rgds")) + TUTORIAL)

_cache: dict = {}


def load(path: str) -> dict:
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            _cache[path] = json.load(f)
    return _cache[path]


def name(path: str) -> str:
    return os.path.basename(path)


def diff_of(path: str) -> str:
    b = name(path)
    for d in DIFFS:
        if b.endswith(f"_{d}_v8.rgds"):
            return d
    return ""


def report(fails: list, limit: int = 4) -> str:
    return f"{len(fails)}건 — " + "; ".join(str(x) for x in fails[:limit]) + (" …" if len(fails) > limit else "")


def expect_none(fails: list) -> None:
    assert not fails, report(fails)


# ── 수량 ──────────────────────────────────────────────────────────
def test_song_and_chart_counts():
    """수록곡 17곡, 곡마다 EZ·NM·HD·EX 4난이도 = 68채보 (DESIGN §14 프로토타입 출시, itch 페이지)."""
    per_song = defaultdict(set)
    for p in SHIPPED:
        per_song[os.path.basename(os.path.dirname(p))].add(diff_of(p))
    assert len(SONG_DIRS) == 17, f"곡 폴더 {len(SONG_DIRS)}개"
    assert len(SHIPPED) == 68, f"수록 채보 {len(SHIPPED)}개"
    expect_none([s for s, ds in per_song.items() if ds != set(DIFFS)])


def test_display_titles_match_design_list():
    """수록곡 표시 제목은 DESIGN §8의 올 대문자 대장르 이름이다(곡당 하나, 17곡)."""
    titles = {load(p)["meta"].get("display_title") for p in SHIPPED}
    extra = sorted(t for t in titles if t not in DESIGN_TITLES)
    assert not extra, f"DESIGN 목록에 없는 표시 제목: {extra} / 목록에만 있는 것: {sorted(DESIGN_TITLES - titles)}"
    assert len(titles) == 17, f"표시 제목 {len(titles)}종 — 목록에만 있는 것: {sorted(DESIGN_TITLES - titles)}"


@pytest.mark.xfail(strict=True, reason="문서-데이터 불일치(사용자 결정 대기): DESIGN §8 표시 제목 목록에는 AMBIENT가 있으나 수록 17곡에는 엠비언트 곡이 없다. "
                                       "목록을 정정할지 곡을 더할지는 사용자가 정한다. 같아지면 이 표시를 지울 것.")
def test_design_title_list_equals_shipped_titles():
    titles = {load(p)["meta"].get("display_title") for p in SHIPPED}
    assert titles == DESIGN_TITLES, f"DESIGN 목록에만 있는 것: {sorted(DESIGN_TITLES - titles)} / 수록곡에만 있는 것: {sorted(titles - DESIGN_TITLES)}"


# ── 파일·구조 ─────────────────────────────────────────────────────
def test_all_chart_files_parse_with_required_sections():
    """모든 .rgds(수록·원본·시험·튜토리얼 %d개)가 JSON으로 읽히고 meta·sounds·timing_events·gimmick_events·score가 있다(DESIGN §8)."""
    fails = []
    for p in ALL_RGDS:
        try:
            d = load(p)
        except Exception as e:
            fails.append(f"{name(p)} 읽기 실패: {str(e)[:60]}")
            continue
        for key in ("meta", "sounds", "timing_events", "gimmick_events", "score"):
            if key not in d:
                fails.append(f"{name(p)} 에 {key} 없음")
    expect_none(fails)


test_all_chart_files_parse_with_required_sections.__doc__ %= len(ALL_RGDS)


def test_meta_required_fields_and_types():
    fails = []
    for p in SHIPPED + TUTORIAL:
        m = load(p)["meta"]
        # 튜토리얼 채보는 아티스트·제작자·버전 정보가 없다(게임이 .get 기본값으로 읽음) — 수록곡만 전부 요구한다
        required = ("title", "artist", "difficulty", "creator", "chart_version") if p in SHIPPED else ("title", "difficulty")
        for key in required:
            if not isinstance(m.get(key), str) or not m[key]:
                fails.append(f"{name(p)}: {key}")
        if not isinstance(m.get("bpm"), (int, float)) or m["bpm"] <= 0:
            fails.append(f"{name(p)}: bpm={m.get('bpm')}")
        if m.get("keymode") not in (4, 5, 6, 8, 16):
            fails.append(f"{name(p)}: keymode={m.get('keymode')}")
        if not isinstance(m.get("level"), (int, float)) or m["level"] < 1:
            fails.append(f"{name(p)}: level={m.get('level')}")
        if not isinstance(m.get("music_path"), str):
            fails.append(f"{name(p)}: music_path 없음")
    expect_none(fails)


def test_display_title_on_shipped_charts():
    expect_none([name(p) for p in SHIPPED if not (isinstance(load(p)["meta"].get("display_title"), str) and load(p)["meta"]["display_title"])])


def test_difficulty_and_keymode_match_file_and_design():
    """meta.difficulty는 파일 이름 접미사와 같고, 키 수는 EZ 4 / NM 5 / HD 6 / EX 6 (DESIGN §14)."""
    fails = []
    for p in SHIPPED:
        m = load(p)["meta"]
        d = diff_of(p)
        if m.get("difficulty") != d:
            fails.append(f"{name(p)}: difficulty={m.get('difficulty')}")
        if m.get("keymode") != KEYMODE_OF_DIFF[d]:
            fails.append(f"{name(p)}: keymode={m.get('keymode')} (기대 {KEYMODE_OF_DIFF[d]})")
    expect_none(fails)


def test_charts_in_a_song_share_metadata():
    """같은 곡의 네 난이도는 제목·표시 제목·아티스트·BPM이 같다."""
    by_song = defaultdict(list)
    for p in SHIPPED:
        by_song[os.path.dirname(p)].append(load(p)["meta"])
    fails = []
    for d, metas in by_song.items():
        for key in ("title", "display_title", "artist", "bpm"):
            if len({str(m.get(key)) for m in metas}) != 1:
                fails.append(f"{os.path.basename(d)}: {key} 가 난이도마다 다름")
    expect_none(fails)


# ── 키음 ──────────────────────────────────────────────────────────
def test_sounds_unique_names_and_files_exist():
    """sounds 항목은 이름이 겹치지 않고, 경로(곡 폴더 기준)의 파일이 실제로 있다."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        base = os.path.dirname(p)
        names = [s.get("name") for s in load(p)["sounds"]]
        if len(names) != len(set(names)):
            fails.append(f"{name(p)}: 이름 중복")
        for s in load(p)["sounds"]:
            if not s.get("name") or not s.get("path"):
                fails.append(f"{name(p)}: name/path 빠짐 {s}")
            else:
                path = s["path"]
                full = os.path.join(GAME_PROJECT, path[len("res://"):]) if path.startswith("res://") else os.path.join(base, path)
                if not os.path.isfile(full):
                    fails.append(f"{name(p)}: {path} 없음")
    expect_none(fails)


def test_keysound_wav_files_have_wav_header():
    """채보가 참조하는 키음 파일은 비어 있지 않고 WAV(RIFF/WAVE) 머리말을 가진다."""
    fails = []
    seen = set()
    for p in SHIPPED:
        base = os.path.dirname(p)
        for s in load(p)["sounds"]:
            fp = os.path.join(base, s["path"])
            if fp in seen or not os.path.isfile(fp):
                continue
            seen.add(fp)
            with open(fp, "rb") as f:
                head = f.read(12)
            if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
                fails.append(fp.replace(CHARTS, ""))
    assert seen, "검사한 키음이 없음"
    expect_none(fails)


# ── 노트 ──────────────────────────────────────────────────────────
def test_notes_types_lanes_and_times():
    """노트: 타입은 tap/long/slide/drag, 레인은 0 이상 정수, 시각은 0 이상 숫자, 롱은 길이 > 0 (DESIGN §7·§8)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        for i, n in enumerate(load(p)["score"]):
            if n.get("type") not in NOTE_TYPES:
                fails.append(f"{name(p)}#{i} type={n.get('type')}")
            if not isinstance(n.get("lane"), int) or n["lane"] < 0:
                fails.append(f"{name(p)}#{i} lane={n.get('lane')}")
            if not isinstance(n.get("timing_ms"), (int, float)) or n["timing_ms"] < 0:
                fails.append(f"{name(p)}#{i} timing_ms={n.get('timing_ms')}")
            if n.get("type") == "long" and not (isinstance(n.get("length_ms"), (int, float)) and n["length_ms"] > 0):
                fails.append(f"{name(p)}#{i} 롱 length_ms={n.get('length_ms')}")
    expect_none(fails)


def test_note_sound_references_resolve_and_volume_ranges():
    """키음 참조가 sounds에 있고, 수록 채보의 모든 노트에 키음이 있으며, velocity 1~127·volume 0~200·pan -127~127 (DESIGN §8)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        d = load(p)
        names = {s["name"] for s in d["sounds"]}
        shipped = p in SHIPPED
        for i, n in enumerate(d["score"]):
            ks = n.get("key_sound")
            if ks is None:
                if shipped or n.get("type") != "drag":   # 튜토리얼 드래그 웨이포인트는 키음 없이 허용
                    fails.append(f"{name(p)}#{i} 키음 없음({n.get('type')})")
            elif ks not in names:
                fails.append(f"{name(p)}#{i} 키음 {ks} 가 sounds에 없음")
            if "velocity" in n and not (1 <= n["velocity"] <= 127):
                fails.append(f"{name(p)}#{i} velocity={n['velocity']}")
            if "volume" in n and not (0 <= n["volume"] <= 200):
                fails.append(f"{name(p)}#{i} volume={n['volume']}")
            if "pan" in n and not (-127 <= n["pan"] <= 127):
                fails.append(f"{name(p)}#{i} pan={n['pan']}")
    expect_none(fails)


def test_drag_chains_have_waypoints_in_time_order():
    """드래그는 같은 chain_id의 웨이포인트 2개 이상이 시각 순서로 이어진다 (DESIGN §6)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        chains = defaultdict(list)
        for n in load(p)["score"]:
            if n.get("type") == "drag":
                if "chain_id" not in n:
                    fails.append(f"{name(p)}: chain_id 없음")
                else:
                    chains[n["chain_id"]].append(n["timing_ms"])
        for cid, ts in chains.items():
            if len(ts) < 2:
                fails.append(f"{name(p)}: chain {cid} 웨이포인트 {len(ts)}개")
            elif ts != sorted(ts):
                fails.append(f"{name(p)}: chain {cid} 시각 순서 아님")
    expect_none(fails)


# ── 타이밍·기믹 ───────────────────────────────────────────────────
def test_timing_events_valid():
    """timing_events: measure는 0 이상 정수, bpm·measure_length는 양수, 마디 0의 bpm은 meta.bpm과 같다 (DESIGN §8)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        d = load(p)
        for e in d["timing_events"]:
            if not isinstance(e.get("measure"), int) or e["measure"] < 0:
                fails.append(f"{name(p)}: measure={e.get('measure')}")
            # JSON null은 "지정 없음"이다(ChartTiming.build_table이 null을 건너뜀)
            if e.get("bpm") is not None and not (isinstance(e["bpm"], (int, float)) and e["bpm"] > 0):
                fails.append(f"{name(p)}: bpm={e['bpm']}")
            if e.get("measure_length") is not None and not (isinstance(e["measure_length"], (int, float)) and e["measure_length"] > 0):
                fails.append(f"{name(p)}: measure_length={e['measure_length']}")
            if e.get("measure") == 0 and e.get("bpm") is not None and e["bpm"] != d["meta"]["bpm"]:
                fails.append(f"{name(p)}: 마디0 bpm {e['bpm']} ≠ meta.bpm {d['meta']['bpm']}")
    expect_none(fails)


def _sections(d: dict):
    """gimmick_events를 시각순(같은 시각이면 end 먼저)으로 읽어 (구간 목록, 오류 목록)을 돌려준다."""
    evs = sorted(d["gimmick_events"], key=lambda g: (g["timing_ms"], 0 if g["action"] == "lanemix_end" else 1))
    secs, errs, cur = [], [], None
    for g in evs:
        a = g["action"]
        if a == "lanemix_start":
            if cur is not None:
                errs.append(f"start 안에 start @ {g['timing_ms']}")
            cur = {"start": g["timing_ms"], "end": None, "target": g.get("target_key_mode"), "steps": []}
        elif a == "lanemix_step":
            if cur is None:
                errs.append(f"구간 밖 step @ {g['timing_ms']}")
            else:
                cur["steps"].append(g)
        elif a == "lanemix_end":
            if cur is None:
                errs.append(f"짝 없는 end @ {g['timing_ms']}")
            else:
                cur["end"] = g["timing_ms"]
                secs.append(cur)
                cur = None
    if cur is not None:
        errs.append(f"끝나지 않은 start @ {cur['start']}")
    return secs, errs


def test_gimmick_events_valid_and_lanemix_sections_wellformed():
    """기믹: action은 정해진 값, lanemix_start/end가 짝을 이루고(중첩·짝 없음 없음) 시작<끝, 목표 키모드는 4/5/6/8/16/-1/-2, step은 구간 안 (DESIGN §8·§9)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        d = load(p)
        for g in d["gimmick_events"]:
            if g.get("action") not in GIMMICK_ACTIONS:
                fails.append(f"{name(p)}: action={g.get('action')}")
            if not isinstance(g.get("timing_ms"), (int, float)) or g["timing_ms"] < 0:
                fails.append(f"{name(p)}: timing_ms={g.get('timing_ms')}")
        secs, errs = _sections(d)
        fails += [f"{name(p)}: {e}" for e in errs]
        for s in secs:
            if not s["end"] > s["start"]:
                fails.append(f"{name(p)}: 구간 끝이 시작보다 늦지 않음 {s['start']}~{s['end']}")
            if s["target"] not in TARGET_MODES:
                fails.append(f"{name(p)}: 목표 키모드 {s['target']}")
            for st in s["steps"]:
                if not (s["start"] <= st["timing_ms"] <= s["end"]):
                    fails.append(f"{name(p)}: step @ {st['timing_ms']} 가 구간 밖")
                # 슈퍼랜덤(-2) 구간의 step은 목표를 비워 둔다 — 시퀀스에서 하나씩 꺼내 쓴다(DESIGN §9)
                tm = st.get("target_key_mode")
                if not (tm is None and s["target"] == -2) and tm not in TARGET_MODES - {-1, -2}:
                    fails.append(f"{name(p)}: step 목표 {tm}")
        for a, b in zip(secs, secs[1:]):
            if b["start"] < a["end"]:
                fails.append(f"{name(p)}: 구간이 겹침")
    expect_none(fails)


def test_lanemix_layer_notes_lie_inside_a_section():
    """레인믹스 레이어(L16~31) 노트는 반드시 레인믹스 구간 안(끝 시각 포함)에 있다 — 밖이면 게임이 구간 밖 채보 오류로 버린다 (DESIGN §9)."""
    fails = []
    for p in SHIPPED + TUTORIAL:
        d = load(p)
        secs, _ = _sections(d)
        for i, n in enumerate(d["score"]):
            if 16 <= n["lane"] <= 31 and not any(s["start"] <= n["timing_ms"] <= s["end"] for s in secs):
                fails.append(f"{name(p)}#{i} lane={n['lane']} @ {n['timing_ms']}")
    expect_none(fails)


def test_base_layer_lanes_fit_the_chart_keymode():
    """기본 레이어(L0~15) 노트는 16레인 안이다. (키 수와 무관하게 16레인 물리 레인 위에서 키 그룹으로 묶인다 — DESIGN §3)."""
    fails = []
    for p in SHIPPED:
        for i, n in enumerate(load(p)["score"]):
            if 0 <= n["lane"] <= 15 and n["lane"] >= 16:
                fails.append(f"{name(p)}#{i}")
    expect_none(fails)
    assert any(0 <= n["lane"] <= 15 for p in SHIPPED[:4] for n in load(p)["score"]), "기본 레이어 노트가 하나도 없음"


# ── 곡 폴더 구조 (DESIGN §8 "곡 폴더 구조 + 풀믹스/미리듣기") ───────────────────
@pytest.mark.parametrize("song_dir", SONG_DIRS, ids=[os.path.basename(d) for d in SONG_DIRS])
def test_song_folder_structure(song_dir):
    """곡 폴더: manifest.json(song_uid=폴더 이름), keysounds/ 와 full_mix.ogg, preview/preview.ogg, 자켓 이미지, 4난이도 채보."""
    fails = []
    mf = os.path.join(song_dir, "manifest.json")
    if not os.path.isfile(mf):
        fails.append("manifest.json 없음")
    else:
        try:
            m = json.load(open(mf, encoding="utf-8"))
            if m.get("song_uid") != os.path.basename(song_dir):
                fails.append(f"song_uid={m.get('song_uid')} ≠ 폴더 이름")
            if not isinstance(m.get("pack_id"), str) or not m["pack_id"]:
                fails.append("pack_id 없음")
        except Exception as e:
            fails.append(f"manifest.json 읽기 실패: {e}")
    if not os.path.isdir(os.path.join(song_dir, "keysounds")):
        fails.append("keysounds/ 없음")
    for rel in ("keysounds/full_mix.ogg", "preview/preview.ogg"):
        fp = os.path.join(song_dir, rel)
        if not os.path.isfile(fp):
            fails.append(f"{rel} 없음")
        else:
            with open(fp, "rb") as f:
                if f.read(4) != b"OggS":
                    fails.append(f"{rel} 가 Ogg 파일이 아님")
    if not any(os.path.isfile(os.path.join(song_dir, "jacket", j)) for j in ("cover.png", "jacket.png", "jacket.jpg")):
        fails.append("자켓 이미지(cover.png/jacket.png/jacket.jpg) 없음")
    present = {diff_of(p) for p in SHIPPED if os.path.dirname(p) == song_dir}
    if present != set(DIFFS):
        fails.append(f"난이도 채보 {sorted(present)}")
    expect_none(fails)
