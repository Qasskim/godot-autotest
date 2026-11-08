# -*- coding: utf-8 -*-
"""서버에 남은 테스트 데이터 정리 (2026-11-08, 사용자 확정 "장부 목록 방식").

지우는 대상은 **server_ledger.jsonl 에 적힌 계정뿐**이다. 장부에 없는 것은 외부 플레이어 것일 수 있어 절대 건드리지 않는다.
- 게임이 만든 익명 계정(fixed=false): 계정째 삭제 (records·sequences·rivals·rival_notices·users 는 on delete cascade 로 같이 사라짐)
- 고정 테스트 계정(fixed=true, test@~test7@): 계정·닉네임은 남기고 records·sequences·rivals·rival_notices 행만 삭제
- 장부 밖 의심 목록: 첫 run_start 이후에 생긴 계정 중 장부에 없는 것 — **보여주기만 하고 지우지 않는다**

사용법 (저장소 루트에서):
    python tests/cleanup_server.py            # 기본: 지울 목록과 행 수만 보여준다 (읽기 전용)
    python tests/cleanup_server.py --apply    # 실제 삭제 — 한 문장(트랜잭션)으로 지우고 앞뒤 행 수를 보여준다. 사용자 확인 뒤에만 실행할 것

서버 접속은 Supabase CLI(`npx supabase db query --linked`)를 쓴다. CLI 는 이 프로젝트를 "production"으로 표시하고 쓰기에는 --yes 가 필요하다.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_ledger  # noqa: E402

GAME_REPO = os.environ.get("GAME_REPO", r"D:\Godot\RhythmGame_New")   # supabase/ 링크 정보가 있는 곳


def _arr(ids: list) -> str:
    for i in ids:
        assert server_ledger.is_uuid(i), i       # SQL 에 넣기 전에 형식 검사 (장부가 깨져도 주입이 불가능하게)
    return "array[" + ",".join(f"'{i}'" for i in ids) + "]::uuid[]"


def _query(sql: str, write: bool = False) -> list:
    cmd = ["npx", "--yes", "supabase", "db", "query", "--linked", "--yes" if write else "--read-only", sql]
    r = subprocess.run(cmd, cwd=GAME_REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=(os.name == "nt"), timeout=180)
    out = r.stdout
    start = out.find("{")
    if r.returncode != 0 or start < 0:
        raise RuntimeError(f"supabase CLI 실패(종료코드 {r.returncode}):\n{(r.stdout + r.stderr)[-800:]}")
    return json.loads(out[start:out.rfind("}") + 1])["rows"]


def counts_sql(anon: list, fixed: list) -> str:
    a, f = _arr(anon), _arr(fixed)
    return (
        "select "
        f"(select count(*) from auth.users where id = any({a})) as anon_accounts_to_delete, "
        f"(select count(*) from public.records where user_id = any({a})) as anon_records_cascaded, "
        f"(select count(*) from public.records where user_id = any({f})) as fixed_records, "
        f"(select count(*) from public.sequences where user_id = any({f})) as fixed_sequences, "
        f"(select count(*) from public.rivals where user_id = any({f})) as fixed_rivals, "
        f"(select count(*) from public.rival_notices where user_id = any({f})) as fixed_notices, "
        f"(select count(*) from public.rivals where rival_user_id = any({a}) and user_id <> all({a})) as others_rivals_cascaded"
    )


def delete_sql(anon: list, fixed: list) -> str:
    """한 문장 = 한 트랜잭션. 고정 계정은 행만, 익명 계정은 계정째(나머지는 cascade). 같은 행을 두 번 지우려 하지 않도록 집합을 나눈다."""
    a, f = _arr(anon), _arr(fixed)
    return (
        "with "
        f"d_rec as (delete from public.records where user_id = any({f}) returning 1), "
        f"d_seq as (delete from public.sequences where user_id = any({f}) returning 1), "
        f"d_riv as (delete from public.rivals where user_id = any({f}) returning 1), "
        f"d_not as (delete from public.rival_notices where user_id = any({f}) returning 1), "
        f"d_usr as (delete from auth.users where id = any({a}) returning 1) "
        "select (select count(*) from d_rec) as records, (select count(*) from d_seq) as sequences, "
        "(select count(*) from d_riv) as rivals, (select count(*) from d_not) as notices, (select count(*) from d_usr) as accounts"
    )


def suspects_sql(known: list, since: str) -> str:
    return (
        "select id, is_anonymous, created_at from auth.users "
        f"where created_at >= '{since}'::timestamptz and id <> all({_arr(known)}) order by created_at"
    )


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # 윈도 콘솔 기본(cp949)에서 한글·기호가 깨지거나 예외가 나지 않게
    apply = "--apply" in sys.argv
    acc = server_ledger.accounts()
    anon = sorted(u for u, v in acc.items() if not v["fixed"])
    fixed = sorted(u for u, v in acc.items() if v["fixed"])
    print(f"장부: {server_ledger.LEDGER_PATH}")
    print(f"장부에 적힌 계정 — 익명 {len(anon)}개(계정째 삭제), 고정 테스트 {len(fixed)}개(기록 행만 삭제)")
    if not acc:
        print("장부가 비어 있어 지울 것이 없습니다.")
        return 0
    before = _query(counts_sql(anon, fixed))[0]
    print("지울 대상 행 수(읽기 전용 조회):", json.dumps(before, ensure_ascii=False))
    since = server_ledger.first_run_start()
    if since:
        rows = _query(suspects_sql(anon + fixed, since))
        print(f"장부 밖 의심 계정(첫 run_start {since} 이후 생성, 지우지 않음): {len(rows)}개")
        for r in rows[:20]:
            print("  ", r["id"], "익명" if r["is_anonymous"] else "실계정", r["created_at"])
    if not apply:
        print("→ 목록만 보여드렸습니다. 실제로 지우려면 --apply (사용자 확인 뒤에).")
        return 0
    done = _query(delete_sql(anon, fixed), write=True)[0]
    print("삭제 결과:", json.dumps(done, ensure_ascii=False))
    after = _query(counts_sql(anon, fixed))[0]
    print("삭제 뒤 남은 대상 행 수:", json.dumps(after, ensure_ascii=False))
    server_ledger.append("cleaned", deleted=done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
