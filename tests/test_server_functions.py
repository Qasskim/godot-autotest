# -*- coding: utf-8 -*-
"""서버 엣지 함수 — 게임이 부르는 link_google_play 의 입력 검사 (2026-11-10).
기준: supabase/functions/link_google_play/index.ts (인증 코드가 비면 400 missing_auth_code — 구글에 연결하기 전에 거른다).
게임이 부르는 서버 함수는 add_rival·delete_account·link_google_play·register_nickname·remove_rival·submit_score 6개이고, 디버그 허용 목록은 그중 submit_score·link_google_play 뿐이다.

개발 서버에 그대로 접속하고(마커 server) 고정 테스트 계정 3으로 로그인한다. 서버에 아무것도 쓰지 않는 호출만 한다: 구글에 닿기 전에 거부되는 호출.
호출은 게임의 TestServer /debug_submit_score?fn= (허용 목록 2개: submit_score·link_google_play)으로 보낸다. 이 시험의 payload 값은 시험 작성자가 정했다.
"""
import pytest

import client
from server_helpers import ACCT_A, login

pytestmark = pytest.mark.server

@pytest.fixture(scope="module")
def caller():
    uid = login(ACCT_A)
    return uid


def call(fn: str, payload: dict) -> dict:
    return client.debug_submit_score(payload, fn=fn)


def test_link_google_play_without_auth_code_is_rejected_before_calling_google(caller):
    r = call("link_google_play", {"display_name": "autotest"})
    assert r["ok"] is False and r["response"].get("error") == "missing_auth_code", r
    r2 = call("link_google_play", {"auth_code": "   "})
    assert r2["ok"] is False and r2["response"].get("error") == "missing_auth_code", f"공백만 있는 인증 코드도 거부해야 합니다: {r2}"


def test_debug_endpoint_refuses_functions_outside_the_allow_list(caller):
    import urllib.error
    for fn in ("delete_account", "register_chart", "sign_package"):
        with pytest.raises(urllib.error.HTTPError) as e:
            client.post_json(f"/debug_submit_score?fn={fn}", {"x": 1})
        assert e.value.code == 400, f"허용 목록 밖의 함수({fn})를 디버그 엔드포인트가 받았습니다"
