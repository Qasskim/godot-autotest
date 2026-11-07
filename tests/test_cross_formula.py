# -*- coding: utf-8 -*-
"""교차 비교 — 시퀀서(C#)와 게임(GDScript)의 음량·pan 공식이 같은가 (기준 DESIGN.md §8).

DESIGN §8: "좌우 음량 공식이 양쪽에서 같아야 한다 ... 바꿀 땐 양쪽을 같이 고칠 것." 시퀀서에서 듣는 소리와 게임 소리가 달라지면 안 된다.
- 시퀀서 쪽: csharp_check/SeqFormulaCheck 가 시퀀서 소스(NoteData.cs, PanLaw.cs)를 그대로 연결해 dotnet publish 한 뒤 실행한 출력.
- 게임 쪽: godot_unit/unit_audio.gd 가 ChartLoader.note_gain/note_pan, KeySoundManager._apply_pan 결과를 낸 수치표.
- 기준: 문서의 공식(음량 = velocity/64 × volume/100, pan 은 반대쪽 채널만 cos(|pan|/127 × 90°)).
서버·게임 창 없이 돈다.
"""
import json
import math
import os
import subprocess

import pytest
from godot_runner import REPO_ROOT, run_unit_module

pytestmark = pytest.mark.no_server

PROJ = os.path.join(REPO_ROOT, "csharp_check", "SeqFormulaCheck")


@pytest.fixture(scope="module")
def csharp():
    r = subprocess.run(["dotnet", "publish", "-c", "Release", "-o", "out"], cwd=PROJ, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert r.returncode == 0, f"dotnet publish 실패:\n{(r.stdout + r.stderr)[-1200:]}"
    out = subprocess.run([os.path.join(PROJ, "out", "SeqFormulaCheck.exe")], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60).stdout
    data = {"pan": {}, "gain": {}, "clampv": {}, "clampvol": {}, "clamppan": {}, "defaults": None}
    for line in out.splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "PAN":
            data["pan"][int(p[1])] = (float(p[2]), float(p[3]))
        elif p[0] == "GAIN":
            data["gain"][(int(p[1]), float(p[2]))] = float(p[3])
        elif p[0] == "CLAMPV":
            data["clampv"][int(p[1])] = int(p[2])
        elif p[0] == "CLAMPVOL":
            data["clampvol"][float(p[1])] = float(p[2])
        elif p[0] == "CLAMPPAN":
            data["clamppan"][int(p[1])] = int(p[2])
        elif p[0] == "DEFAULTS_NULL":
            data["defaults"] = [int(x) for x in p[1:]]
    return data


@pytest.fixture(scope="module")
def game():
    res = run_unit_module("audio")
    row = next(r for r in res if r["name"].startswith("교차 비교용 수치표"))
    return json.loads(row["detail"])


def far_gain(pan: int) -> float:
    return math.cos(abs(pan) / 127.0 * math.pi / 2.0)


def test_csharp_pan_follows_documented_formula(csharp):
    """시퀀서 PanLaw: pan 0은 원음, 양수는 왼쪽만·음수는 오른쪽만 cos(|pan|/127×90°) 배."""
    bad = []
    assert len(csharp["pan"]) == 255
    for pan, (l, r) in csharp["pan"].items():
        want_l, want_r = (1.0, 1.0) if pan == 0 else ((far_gain(pan), 1.0) if pan > 0 else (1.0, far_gain(pan)))
        if abs(l - want_l) > 1e-6 or abs(r - want_r) > 1e-6:
            bad.append((pan, l, r, want_l, want_r))
    assert not bad, f"{len(bad)}건 — {bad[:3]}"


def test_csharp_gain_follows_documented_formula(csharp):
    """시퀀서 음량: velocity/64 × volume/100."""
    bad = [(k, v, k[0] / 64.0 * k[1] / 100.0) for k, v in csharp["gain"].items() if abs(v - k[0] / 64.0 * k[1] / 100.0) > 1e-6]
    assert len(csharp["gain"]) == 40 and not bad, f"{len(bad)}건 — {bad[:3]}"


def test_game_pan_matches_sequencer(csharp, game):
    """게임 pan 적용(샘플 20000)의 반대쪽 채널 값은 시퀀서 이득을 샘플에 곱한 값과 1 이내로 같고, 가까운 쪽은 그대로다."""
    amp = game["amp"]
    bad = []
    assert len(game["pan"]) == 255
    for pan, gl, gr in game["pan"]:
        cl, cr = csharp["pan"][pan]
        if abs(gl - int(amp * cl)) > 1 or abs(gr - int(amp * cr)) > 1:
            bad.append((pan, (gl, gr), (int(amp * cl), int(amp * cr))))
        if pan > 0 and gr != amp or pan < 0 and gl != amp or pan == 0 and (gl, gr) != (amp, amp):
            bad.append((pan, "가까운 쪽이 그대로가 아님", (gl, gr)))
    assert not bad, f"{len(bad)}건 — {bad[:3]}"


def test_game_gain_matches_sequencer(csharp, game):
    """게임 음량(ChartLoader.note_gain)이 시퀀서 NoteData.Gain과 40개 조합 모두 같다."""
    bad = [(v, vol, g, csharp["gain"][(v, float(vol))]) for v, vol, g in game["gain"] if abs(g - csharp["gain"][(v, float(vol))]) > 1e-6]
    assert len(game["gain"]) == 40 and not bad, f"{len(bad)}건 — {bad[:3]}"


def test_out_of_range_values_are_clamped_the_same_way(csharp, game):
    """범위 밖 값은 양쪽이 같은 값으로 자른다(velocity 1~127, volume 0~200, pan ±127)."""
    c = game["clamp"]
    assert abs(c["vel_-5"] - csharp["clampv"][-5] / 64.0) < 1e-6
    assert abs(c["vel_0"] - csharp["clampv"][0] / 64.0) < 1e-6
    assert abs(c["vel_500"] - csharp["clampv"][500] / 64.0) < 1e-6
    assert abs(c["vol_-10"] - csharp["clampvol"][-10.0] / 100.0) < 1e-6
    assert abs(c["vol_300"] - csharp["clampvol"][300.0] / 100.0) < 1e-6
    assert (c["pan_-200"], c["pan_200"]) == (csharp["clamppan"][-200], csharp["clamppan"][200])


def test_sequencer_does_not_write_default_values(csharp):
    """기준값(velocity 64, volume 100, pan 0)이면 파일에 적지 않는다(null) — 기존 채보와 호환 (DESIGN §8)."""
    assert csharp["defaults"] == [1, 1, 1]
