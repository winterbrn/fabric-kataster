#!/usr/bin/env bash
set -euo pipefail

# Usage: ./seedParcels.sh [count]
#   count - number of parcels to create (default: 300, max: 300)

if [[ ! -x ./deployChaincode.sh ]]; then
  echo "Missing ./deployChaincode.sh (run from repo root)" >&2
  exit 1
fi

COUNT="${1:-300}"

python3 - "$COUNT" <<'PY'
import json
import subprocess
import sys

sys.path.insert(0, ".")
from seed_data import generate_parcels

count = int(sys.argv[1])
parcels = generate_parcels(count)

for p in parcels:
    parcel_json = json.dumps(p, ensure_ascii=False, separators=(",", ":"))
    print(f"Creating {p['id']} ({p['owners'][0]['userId']}) ...")
    subprocess.run(["./deployChaincode.sh", "createparcel", parcel_json], check=True)

print(f"Done: created {len(parcels)} parcels.")
PY
