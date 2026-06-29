import argparse
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

LOG_FILE = "loadtest.log"
log_lock = threading.Lock()


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


# fazy: nazov, chaincode funkcia, ktore konto pouzit
PHASES = [
    ("vytvorenie",          "CreateChangeRequest",          "seller"),
    ("schvalenie_kupujuci", "BuyerApproveChangeRequest",    "buyer"),
    ("potvrdenie_platby",   "RequesterConfirmPayment",      "seller"),
    ("schvalenie_kataster", "CadastreApproveChangeRequest", "cadastre"),
    ("schvalenie_okres",    "DistrictApproveChangeRequest", "district"),
    ("vykonanie",           "CadastreExecuteChangeRequest", "cadastre"),
]


def run_one_sale(idx, parcel_id, seller, buyer, share, cadastre_user="CADAS002", district_user="DISTR002"):
    label = "#" + str(idx) + " " + parcel_id + " (" + seller + " -> " + buyer + ")"
    log(label + ": START")
    rid = None

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

        t0 = time.time()
        out = curl_post(fcn, args, org, user)
        dt = time.time() - t0

        err = parse_error(out)
        if err:
            log(label + ": " + phase_name + " ZLYHALO (" + ("%.2f" % dt) + "s) - " + err)
            return {"id": idx, "parcel": parcel_id, "ok": False, "phase": phase_name}

        res = parse_result(out)
        if rid is None:
            if not res or "id" not in res:
                log(label + ": vytvorenie ZLYHALO - chyba id v odpovedi")
                return {"id": idx, "parcel": parcel_id, "ok": False, "phase": phase_name}
            rid = res["id"]

        status = res.get("status") if isinstance(res, dict) else "?"
        log(label + ": " + phase_name + " OK (" + ("%.2f" % dt) + "s), stav=" + str(status))

    log(label + ": HOTOVO")
    return {"id": idx, "parcel": parcel_id, "ok": True, "phase": "vykonanie"}


def fetch_parcels(org, user):
    out = curl_get("GetAllParcels", [], org, user)
    res = parse_result(out)
    if not isinstance(res, list):
        log("Surova odpoved z GetAllParcels: " + out[:500])
        return []
    return res


def fetch_parcel(pid, org, user):
    out = curl_get("ReadParcel", [pid], org, user)
    return parse_result(out)


def current_owner(pid, org, user):
    out = curl_get("ReadParcel", [pid], org, user)
    p = parse_result(out)
    if not isinstance(p, dict) or not p.get("owners"):
        log("ReadParcel(" + pid + ") odpoved: " + out[:300])
        return None, None
    o = p["owners"][0]
    return o.get("userId"), o.get("share", "1/1")


def run_pool(count, parcels, parallel, admin_user, cadastre_user, district_user):
    """Pool: kazdy worker pocka kym sa uvolni parcela, potom spusti dalsiu ziadost."""
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
                    log("#" + str(idx) + " " + pid + ": nepodarilo sa zistit vlastnika.")
                    with state_lock:
                        results.append({"id": idx, "parcel": pid, "ok": False, "phase": "init"})
                    continue
                cands = [u for u in users if u != seller]
                if not cands:
                    log("#" + str(idx) + " " + pid + ": nikoho komu predat.")
                    with state_lock:
                        results.append({"id": idx, "parcel": pid, "ok": False, "phase": "init"})
                    continue
                buyer = random.choice(cands)
                r = run_one_sale(idx, pid, seller, buyer, share, cadastre_user, district_user)
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


def build_cases(count, parcels, allow_repeats):
    parcel_owners = {}
    users = set()
    for p in parcels:
        owners = p.get("owners", [])
        if owners:
            parcel_owners[p["id"]] = (owners[0]["userId"], owners[0]["share"])
            for o in owners:
                users.add(o["userId"])

    pids = list(parcel_owners.keys())
    if not pids:
        return []

    if not allow_repeats and count > len(pids):
        log("VAROVANIE: pocet (" + str(count) + ") > pocet parciel ("
            + str(len(pids)) + "), znizujem na " + str(len(pids)) + ".")
        count = len(pids)

    if allow_repeats:
        chosen = [random.choice(pids) for _ in range(count)]
    else:
        chosen = random.sample(pids, count)

    cases = []
    for i, pid in enumerate(chosen, start=1):
        seller, share = parcel_owners[pid]
        candidates = [u for u in users if u != seller]
        if not candidates:
            continue
        buyer = random.choice(candidates)
        cases.append((i, pid, seller, buyer, share))
    return cases


def main():
    ap = argparse.ArgumentParser(description="Zataz test pre kataster.")
    ap.add_argument("--count", type=int, default=10, help="Kolko ziadosti spustit.")
    ap.add_argument("--parallel", type=int, default=1, help="Kolko paralelnych vlakien.")
    ap.add_argument("--repeats", action="store_true",
                    help="Povolit aby sa parcela pouzila viackrat (sekvencne).")
    ap.add_argument("--admin-user", default="CADAS002", help="Pouzivatel pre nacitanie parciel.")
    ap.add_argument("--cadastre-user", default="CADAS002", help="Konto uradnika katastra.")
    ap.add_argument("--district-user", default="DISTR002", help="Konto uradnika okresu.")
    args = ap.parse_args()

    open(LOG_FILE, "w").close()  # vycistit log

    log("=== START: pocet=" + str(args.count) + ", paralelne=" + str(args.parallel) + " ===")

    parcels = fetch_parcels("Cadastre", args.admin_user)
    if not parcels:
        log("Nenasli sa ziadne parcely. Koniec.")
        return

    log("Nacitanych " + str(len(parcels)) + " parciel.")

    log("Spustam " + str(args.count) + " ziadosti, paralelne="
        + str(args.parallel) + ".")

    t0 = time.time()
    if args.parallel <= 1:
        cases = build_cases(args.count, parcels, args.repeats)
        if not cases:
            log("Nepodarilo sa zostavit testovacie pripady.")
            return
        results = []
        for c in cases:
            results.append(run_one_sale(*c, args.cadastre_user, args.district_user))
    else:
        results = run_pool(
            args.count, parcels, args.parallel,
            args.admin_user, args.cadastre_user, args.district_user,
        )

    total = time.time() - t0
    ok = sum(1 for r in results if r["ok"])
    fail = len(results) - ok

    # rozdelenie zlyhani podla fazy
    fails_by_phase = {}
    for r in results:
        if not r["ok"]:
            fails_by_phase[r["phase"]] = fails_by_phase.get(r["phase"], 0) + 1

    log("=== KONIEC ===")
    log("Uspesne: " + str(ok) + " / " + str(len(results)))
    log("Zlyhane: " + str(fail))
    for ph, n in fails_by_phase.items():
        log("  - faza '" + ph + "': " + str(n))
    log("Celkovy cas: " + ("%.2f" % total) + "s")
    if ok > 0:
        log("Priemer na uspesnu ziadost: " + ("%.2f" % (total / ok)) + "s")
    log("Log ulozeny do: " + LOG_FILE)


if __name__ == "__main__":
    main()
