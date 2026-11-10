# -*- coding: utf-8 -*-
"""서버 엣지 함수 — 관리자 전용 함수의 거부와 입력 검사 (register_chart·sign_package·link_google_play, 2026-11-10).
기준: supabase/functions/*/index.ts 의 응답 코드(register_chart·sign_package: 로그인하지 않은/익명 401 auth_required, 관리자가 아니면 403 not_admin,
link_google_play: 인증 코드가 비면 400 missing_auth_code — 구글에 연결하기 전에 거른다).

개발 서버에 그대로 접속하고(마커 server) 고정 테스트 계정 3(관리자 아님)으로 로그인한다. 서버에 아무것도 쓰지 않는 호출만 한다:
관리자가 아니라서 거부되는 호출, 구글에 닿기 전에 거부되는 호출. 관리자가 성공하는 경로(채보 등록·서명)는 관리자 계정이 필요하고 서버 데이터를 바꾸므로
이 시험의 범위가 아니다 — 서명 값이 게임의 공개키로 검증되는지는 test_unit_signing, 채보 노트 수 계산은 test_data_charts 가 본다.
호출은 게임의 TestServer /debug_submit_score?fn= (허용 목록 4개)으로 보낸다. 이 시험의 payload 값은 시험 작성자가 정했다.
"""
import base64

import pytest

import client
from server_helpers import ACCT_A, db, login

pytestmark = pytest.mark.server

CHART_B64 = base64.b64encode(b'{"meta": {}, "score": []}').decode()


@pytest.fixture(scope="module")
def caller():
    uid = login(ACCT_A)
    rows = db(f"select user_id from public.admins where user_id='{uid}'")
    assert not rows, "시험 계정 3이 관리자입니다 — 이 시험의 전제(관리자 아님)가 깨졌습니다"
    return uid


def call(fn: str, payload: dict) -> dict:
    return client.debug_submit_score(payload, fn=fn)


def test_register_chart_rejects_a_non_admin_account(caller):
    r = call("register_chart", {"song_id": "autotest_never_registered", "difficulty": "EZ", "chart_base64": CHART_B64, "dry_run": True})
    assert r["ok"] is False and r["response"].get("error") == "not_admin", r
    assert db("select count(*) as n from public.charts where song_id='autotest_never_registered'")[0]["n"] == 0, "관리자가 아닌데 채보가 등록됐습니다"


def test_sign_package_rejects_a_non_admin_account(caller):
    r = call("sign_package", {"content_base64": CHART_B64})
    assert r["ok"] is False and r["response"].get("error") == "not_admin", r
    assert "signature" not in str(r["response"]).lower() or r["response"].get("error") == "not_admin", f"관리자가 아닌데 서명 값이 돌아왔습니다: {r}"


def test_link_google_play_without_auth_code_is_rejected_before_calling_google(caller):
    r = call("link_google_play", {"display_name": "autotest"})
    assert r["ok"] is False and r["response"].get("error") == "missing_auth_code", r
    r2 = call("link_google_play", {"auth_code": "   "})
    assert r2["ok"] is False and r2["response"].get("error") == "missing_auth_code", f"공백만 있는 인증 코드도 거부해야 합니다: {r2}"


def test_debug_endpoint_refuses_functions_outside_the_allow_list(caller):
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as e:
        client.post_json("/debug_submit_score?fn=delete_account", {"x": 1})
    assert e.value.code == 400, "허용 목록 밖의 함수(delete_account)를 디버그 엔드포인트가 받았습니다"
