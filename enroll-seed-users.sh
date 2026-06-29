#!/usr/bin/env bash
set -euo pipefail

# Usage: [FABRIC_API=...] [FABRIC_ORG=...] ./enroll-seed-users.sh [count]
#   count - number of users to enroll (default: 300, max: 300)

FABRIC_API="${FABRIC_API:-http://localhost:4000}"
FABRIC_ORG="${FABRIC_ORG:-Cadastre}"
COUNT="${1:-300}"

python3 - "$COUNT" <<'PY'
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, ".")
from seed_data import generate_users

api = os.environ.get("FABRIC_API", "http://localhost:4000").rstrip("/")
org = os.environ.get("FABRIC_ORG", "Cadastre")
count = int(sys.argv[1])

users = generate_users(count)
user_ids = [u["userId"] for u in users]


def post_json(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api + path,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{e.code} {e.reason}: {body}".strip()) from None


print(f"Fabric API: {api}")
print(f"Org: {org}")
print(f"Enrolling {len(user_ids)} users")

enrolled = 0
skipped = 0

for uid in user_ids:
    login = post_json("/users/login", {"username": uid, "orgName": org})
    if login.get("success") is True:
        print(f"SKIP {uid} (already in wallet)")
        skipped += 1
        continue

    res = post_json("/users", {"username": uid, "orgName": org})
    ok = res.get("success")
    if ok is True:
        print(f"OK   {uid}")
        enrolled += 1
    else:
        print(f"WARN {uid}: {res}")

print(f"Done. enrolled={enrolled} skipped={skipped} total={len(user_ids)}")
PY
