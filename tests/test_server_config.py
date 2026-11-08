# -*- coding: utf-8 -*-
"""원격 설정(app_config) — 서버에 적힌 기능 켜기/끄기 값이 게임의 RemoteConfig 에 그대로 반영되는지 (2026-11-08).

서버 표를 읽기만 한다(쓰지 않음). 값이 true 인 키만 켜짐, 나머지·없는 키는 꺼짐(fail-closed)이어야 한다.
"""
import time

import pytest

import client
import server_helpers
from screen_helpers import wait_until

pytestmark = pytest.mark.server


def enabled(key: str) -> bool:
    return client._req("GET", f"/remote_config?key={key}")["enabled"]


def test_every_server_flag_is_reflected_exactly_in_the_game():
    rows = server_helpers.db("select key, value from public.app_config")
    assert rows, "서버 app_config 에 행이 없습니다"
    # 게임은 시작할 때 한 번 읽는다 — 읽기가 끝날 때까지 기다린다
    assert wait_until(lambda: any(enabled(r["key"]) for r in rows) or all(r["value"] is not True for r in rows), timeout=20), "원격 설정을 게임이 읽지 못했습니다"
    for r in rows:
        want = r["value"] is True
        assert enabled(r["key"]) == want, f"{r['key']}: 서버 값 {r['value']!r} → 게임에서 {'켜짐' if enabled(r['key']) else '꺼짐'}"


def test_unknown_key_is_off():
    assert enabled("this_key_does_not_exist_autotest") is False
