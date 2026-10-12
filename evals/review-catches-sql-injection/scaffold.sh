#!/usr/bin/env bash
set -euo pipefail
git init -q -b main .
git config user.email e@e && git config user.name e
mkdir app
cat > app/db.py <<'PY'
def get_user(cur, user_id):
    cur.execute("select * from users where id = %s", (user_id,))
    return cur.fetchone()
PY
git add . && git commit -qm "chore: base"
git checkout -qb feature/search
cat >> app/db.py <<'PY'


def search_users(cur, name):
    cur.execute(f"select * from users where name = '{name}'")
    return cur.fetchall()
PY
git add . && git commit -qm "feat: search users by name"
git diff main...HEAD > changes.diff
