import argparse
import csv
import json
import random
import subprocess
import sys
import threading
import time
import urllib.parse
from datetime import datetime

API = "http://localhost:4000"
CHANNEL = "landregistry"
CC = "parcel"

LOG_FILE = "loadtest_retry.log"
log_lock = threading.Lock()
CSV_FILE = None

# chyby pri ktorych ma zmysel skusit znova (Fabric MVCC konflikty)
RETRYABLE = ["PHANTOM_READ_CONFLICT", "MVCC_READ_CONFLICT", "ENDORSEMENT_POLICY_FAILURE"]


def log(line):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    msg = "[" + ts + "] " + line
    with log_lock:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def curl_get(fcn, args, org, user):
    args_q = urllib.parse.quote(json.dumps(args))
    url = API + "/channels/" + CHANNEL + "/chaincodes/" + CC \
        + "?fcn=" + fcn + "&args=" + args_q
    cmd = [
        "curl", "-s",
        "-H", "X-Fabric-Org: " + org,
        "-H", "X-Fabric-Username: " + user,
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def curl_post(fcn, args, org, user):
    url = API + "/channels/" + CHANNEL + "/chaincodes/" + CC
    body = json.dumps({"fcn": fcn, "args": args})
    cmd = [
        "curl", "-s",
        "-H", "Content-Type: application/json",
        "-H", "X-Fabric-Org: " + org,
        "-H", "X-Fabric-Username: " + user,
        "-X", "POST",
        "-d", body,
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def parse_result(text):
    try:
        d = json.loads(text)
        if isinstance(d, dict) and "result" in d:
            return d["result"]
        return d
    except Exception:
        return None


def parse_error(text):
    try:
        d = json.loads(text)
        if isinstance(d, dict) and d.get("error"):
            err = str(d.get("error"))
            data = str(d.get("errorData", ""))[:300]
            return err + " - " + data
    except Exception:
        pass
    return None


def is_retryable(err_text):
    if not err_text:
        return False
    for marker in RETRYABLE:
        if marker in err_text:
            return True
    return False


def call_with_retry(label, phase, fcn, args, org, user, wait_s, max_retries):
    """Vola chaincode funkciu, pri MVCC konflikte caka a skusi znova."""
    attempt = 0
    while True:
        attempt += 1
        t0 = time.time()
        out = curl_post(fcn, args, org, user)
        dt = time.time() - t0
        err = parse_error(out)
        if not err:
            return parse_result(out), None, attempt, dt
        if is_retryable(err) and attempt <= max_retries:
            log(label + ": " + phase + " konflikt (pokus " + str(attempt)
                + "/" + str(max_retries) + ", " + ("%.2f" % dt) + "s) - cakam "
                + str(wait_s) + "s")
            time.sleep(wait_s)
            continue
        return None, err, attempt, dt


PHASES = [
    ("vytvorenie",          "CreateChangeRequest",          "seller"),
    ("schvalenie_kupujuci", "BuyerApproveChangeRequest",    "buyer"),
    ("potvrdenie_platby",   "RequesterConfirmPayment",      "seller"),
    ("schvalenie_kataster", "CadastreApproveChangeRequest", "cadastre"),
    ("schvalenie_okres",    "DistrictApproveChangeRequest", "district"),
    ("vykonanie",           "CadastreExecuteChangeRequest", "cadastre"),
]


def run_one_sale(idx, parcel_id, seller, buyer, share, cadastre_user, district_user, wait_s, max_retries):
    label = "#" + str(idx) + " " + parcel_id + " (" + seller + " -> " + buyer + ")"
    log(label + ": START")
    rid = None
    total_retries = 0
    phase_times = {}
    t_start = time.time()

    for phase_name, fcn, role in PHASES:
        if role == "seller":
            org, user = "Cadastre", seller
        elif role == "buyer":
            org, user = "Cadastre", buyer
        elif role == "cadastre":
            org, user = "Cadastre", cadastre_user
        else:
            org, user = "District", district_user

        if fcn == "CreateChangeRequest":
            change = {
                "type": "TRANSFER_SHARE",
                "fromUserId": seller,
                "toUserId": buyer,
                "share": share,
            }
            req = {
                "parcelId": parcel_id,
                "requesterUserId": seller,
                "changeJson": json.dumps(change),
            }
            args = [json.dumps(req)]
        else:
            args = [rid]

        res, err, attempts, dt = call_with_retry(
            label, phase_name, fcn, args, org, user, wait_s, max_retries,
        )
        total_retries += attempts - 1
        phase_times[phase_name] = round(dt, 4)

        if err is not None:
            log(label + ": " + phase_name + " ZLYHALO po " + str(attempts)
                + " pokusoch - " + err)
            return {
                "id": idx, "parcel": parcel_id,
                "ok": False, "phase": phase_name, "retries": total_retries,
                "total_time": round(time.time() - t_start, 4),
                "phase_times": phase_times,
            }

        if rid is None and isinstance(res, dict):
            rid = res.get("id")
        status = res.get("status") if isinstance(res, dict) else "?"
        suffix = " (po " + str(attempts) + " pokusoch)" if attempts > 1 else ""
        log(label + ": " + phase_name + " OK (" + ("%.2f" % dt) + "s), stav="
            + str(status) + suffix)

    total_time = round(time.time() - t_start, 4)
    log(label + ": HOTOVO (opakovani spolu: " + str(total_retries) + ")")
    return {
        "id": idx, "parcel": parcel_id,
        "ok": True, "phase": "vykonanie", "retries": total_retries,
        "total_time": total_time,
        "phase_times": phase_times,
    }


def fetch_parcels(org, user):
    out = curl_get("GetAllParcels", [], org, user)
    res = parse_result(out)
    if not isinstance(res, list):
        log("Surova odpoved z GetAllParcels: " + out[:500])
        return []
    return res


def current_owner(pid, org, user):
    out = curl_get("ReadParcel", [pid], org, user)
    p = parse_result(out)
    if not isinstance(p, dict) or not p.get("owners"):
        log("ReadParcel(" + pid + ") odpoved: " + out[:300])
        return None, None
    o = p["owners"][0]
    return o.get("userId"), o.get("share", "1/1")


def run_pool(count, parcels, parallel, admin_user, cadastre_user, district_user, wait_s, max_retries):
    pids = []
    users = set()
    for p in parcels:
        pids.append(p["id"])
        for o in p.get("owners", []):
            uid = o.get("userId")
            if uid:
                users.add(uid)

    state_lock = threading.Lock()
    in_use = set()
    counter = {"next_id": 1}
    results = []

    def acquire():
        while True:
            with state_lock:
                if counter["next_id"] - 1 >= count:
                    return None, None
                free = [p for p in pids if p not in in_use]
                if free:
                    pid = random.choice(free)
                    in_use.add(pid)
                    idx = counter["next_id"]
                    counter["next_id"] += 1
                    return idx, pid
            time.sleep(0.1)

    def release(pid):
        with state_lock:
            in_use.discard(pid)

    def worker():
        while True:
            idx, pid = acquire()
            if idx is None:
                return
            try:
                seller, share = current_owner(pid, "Cadastre", admin_user)
                if not seller:
                    with state_lock:
                        results.append({
                            "id": idx, "parcel": pid,
                            "ok": False, "phase": "init", "retries": 0,
                        })
                    continue
                cands = [u for u in users if u != seller]
                if not cands:
                    with state_lock:
                        results.append({
                            "id": idx, "parcel": pid,
                            "ok": False, "phase": "init", "retries": 0,
                        })
                    continue
                buyer = random.choice(cands)
                r = run_one_sale(
                    idx, pid, seller, buyer, share,
                    cadastre_user, district_user, wait_s, max_retries,
                )
                with state_lock:
                    results.append(r)
            finally:
                release(pid)

    threads = [threading.Thread(target=worker) for _ in range(parallel)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


def write_csv(results, csv_path):
    phase_names = [p[0] for p in PHASES]
    fieldnames = ["id", "parcel", "ok", "phase", "retries", "total_time_s"] + \
                 [p + "_s" for p in phase_names]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results:
            row = {
                "id": r["id"],
                "parcel": r["parcel"],
                "ok": r["ok"],
                "phase": r["phase"],
                "retries": r.get("retries", 0),
                "total_time_s": r.get("total_time", ""),
            }
            pt = r.get("phase_times", {})
            for p in phase_names:
                row[p + "_s"] = pt.get(p, "")
            w.writerow(row)


def main():
    global API, CSV_FILE

    ap = argparse.ArgumentParser(description="Zataz test pre kataster (s opakovanim pri konflikte).")
    ap.add_argument("--count", type=int, default=10, help="Kolko ziadosti spustit.")
    ap.add_argument("--parallel", type=int, default=1, help="Kolko paralelnych vlakien.")
    ap.add_argument("--wait", type=float, default=2.0,
                    help="Kolko sekund cakat pred opakovanim po konflikte.")
    ap.add_argument("--max-retries", type=int, default=10,
                    help="Maximalny pocet opakovani na jednu fazu.")
    ap.add_argument("--admin-user", default="CADAS002")
    ap.add_argument("--cadastre-user", default="CADAS002")
    ap.add_argument("--district-user", default="DISTR002")
    ap.add_argument("--api-url", default=API,
                    help="API endpoint URL (default: http://localhost:4000).")
    ap.add_argument("--output-csv", default=None,
                    help="Export results to CSV file.")
    args = ap.parse_args()

    API = args.api_url
    CSV_FILE = args.output_csv

    open(LOG_FILE, "w").close()

    log("=== START: pocet=" + str(args.count) + ", paralelne=" + str(args.parallel)
        + ", cakanie=" + str(args.wait) + "s, max_retries=" + str(args.max_retries)
        + ", api=" + API + " ===")

    parcels = fetch_parcels("Cadastre", args.admin_user)
    if not parcels:
        log("Nenasli sa ziadne parcely. Koniec.")
        return

    log("Nacitanych " + str(len(parcels)) + " parciel.")

    t0 = time.time()
    results = run_pool(
        args.count, parcels, max(1, args.parallel),
        args.admin_user, args.cadastre_user, args.district_user,
        args.wait, args.max_retries,
    )
    total = time.time() - t0

    ok = sum(1 for r in results if r["ok"])
    fail = len(results) - ok
    retries = sum(r.get("retries", 0) for r in results)

    fails_by_phase = {}
    for r in results:
        if not r["ok"]:
            fails_by_phase[r["phase"]] = fails_by_phase.get(r["phase"], 0) + 1

    log("=== KONIEC ===")
    log("Uspesne: " + str(ok) + " / " + str(len(results)))
    log("Zlyhane: " + str(fail))
    for ph, n in fails_by_phase.items():
        log("  - faza '" + ph + "': " + str(n))
    log("Opakovani spolu: " + str(retries))
    log("Celkovy cas: " + ("%.2f" % total) + "s")
    if ok > 0:
        log("Priemer na uspesnu ziadost: " + ("%.2f" % (total / ok)) + "s")
    log("Log ulozeny do: " + LOG_FILE)

    if CSV_FILE:
        write_csv(results, CSV_FILE)
        log("CSV ulozeny do: " + CSV_FILE)


if __name__ == "__main__":
    main()
