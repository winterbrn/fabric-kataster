import tkinter as tk
from tkinter import ttk
import subprocess
import json

API = "http://localhost:4000"
CHANNEL = "landregistry"
CC = "parcel"


def curl_get(fcn, args, org, username):
    url = API + "/channels/" + CHANNEL + "/chaincodes/" + CC \
        + "?fcn=" + fcn + "&args=" + json.dumps(args)
    cmd = [
        "curl", "-s",
        "-H", "X-Fabric-Org: " + org,
        "-H", "X-Fabric-Username: " + username,
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def curl_post(fcn, args, org, username):
    url = API + "/channels/" + CHANNEL + "/chaincodes/" + CC
    body = json.dumps({"fcn": fcn, "args": args})
    cmd = [
        "curl", "-s",
        "-H", "Content-Type: application/json",
        "-H", "X-Fabric-Org: " + org,
        "-H", "X-Fabric-Username: " + username,
        "-X", "POST",
        "-d", body,
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def curl_post_path(path, body):
    url = API + path
    cmd = [
        "curl", "-s",
        "-H", "Content-Type: application/json",
        "-X", "POST",
        "-d", json.dumps(body),
        url,
    ]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def parse_response(text):
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {"result": data}
    except Exception:
        return {"error": text}


def parse_list(text):
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "result" in data:
            data = data["result"]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def format_response(text):
    resp = parse_response(text)
    if resp.get("error"):
        err = str(resp["error"])
        detail = str(resp.get("errorData", ""))
        if detail:
            return "Chyba: " + err + "\n" + detail
        return "Chyba: " + err
    result = resp.get("result", resp)
    if isinstance(result, dict):
        parts = []
        if result.get("id"):
            parts.append("ID: " + result["id"])
        if result.get("status"):
            parts.append("Stav: " + result["status"])
        if result.get("parcelId"):
            parts.append("Parcela: " + result["parcelId"])
        if parts:
            return "OK  —  " + "  |  ".join(parts)
        return "OK"
    return "OK"


STATUS_COLORS = {
    "SUBMITTED": "#2196F3",
    "BUYER_APPROVED": "#FF9800",
    "PAYMENT_CONFIRMED": "#FF9800",
    "CADASTRE_APPROVED": "#9C27B0",
    "DISTRICT_APPROVED": "#9C27B0",
    "EXECUTED": "#4CAF50",
    "REJECTED": "#F44336",
}

STATUS_LABELS = {
    "SUBMITTED": "Podaná",
    "BUYER_APPROVED": "Kupujúci schválil",
    "PAYMENT_CONFIRMED": "Platba potvrdená",
    "CADASTRE_APPROVED": "Kataster schválil",
    "DISTRICT_APPROVED": "Okres schválil",
    "EXECUTED": "Vykonaná",
    "REJECTED": "Zamietnutá",
}


def add_field(parent, label, default=""):
    tk.Label(parent, text=label).pack(anchor="w")
    e = tk.Entry(parent)
    if default:
        e.insert(0, default)
    e.pack(fill="x", pady=2)
    return e


def make_scrollable(parent):
    canvas = tk.Canvas(parent)
    sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    inner = tk.Frame(canvas)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def _on_linux_scroll_up(event):
        canvas.yview_scroll(-1, "units")

    def _on_linux_scroll_down(event):
        canvas.yview_scroll(1, "units")

    canvas.bind_all("<Button-4>", _on_linux_scroll_up)
    canvas.bind_all("<Button-5>", _on_linux_scroll_down)

    return inner


def render_parcel_card(parent, p):
    card = tk.Frame(parent, relief="groove", borderwidth=1, padx=12, pady=8, bg="white")
    card.pack(fill="x", pady=3, padx=5)

    pid = p.get("parcelId", "")
    pnum = p.get("parcelNumber", "")
    header = pid
    if pnum:
        header += "  —  č. " + pnum
    tk.Label(card, text=header, font=("", 11, "bold"), anchor="w", bg="white").pack(fill="x")

    info_parts = []
    cad_area = p.get("cadastralArea", "")
    if cad_area:
        info_parts.append(cad_area)
    area = p.get("area", "")
    if area:
        info_parts.append(str(area) + " m²")
    land = p.get("landType", "")
    if land:
        info_parts.append(land)
    if info_parts:
        tk.Label(card, text="  |  ".join(info_parts), anchor="w", fg="#555", bg="white").pack(fill="x")

    for o in p.get("owners", []):
        name = o.get("name", "?")
        uid = o.get("userId", "")
        share = o.get("share", "")
        owner_text = name
        if uid:
            owner_text += " (" + uid + ")"
        if share and share != "1/1":
            owner_text += "  —  podiel: " + share
        tk.Label(card, text="Vlastník: " + owner_text, anchor="w", bg="white").pack(fill="x")

    burdens = p.get("burdens", "")
    if burdens:
        tk.Label(card, text="Ťarchy: " + burdens, anchor="w", fg="#888", bg="white").pack(fill="x")

    if p.get("isCommonProperty"):
        tk.Label(card, text="Spoločný majetok", anchor="w", fg="#2196F3", bg="white").pack(fill="x")

    return card


def render_request_card(parent, r):
    card = tk.Frame(parent, relief="groove", borderwidth=1, padx=12, pady=8, bg="white")
    card.pack(fill="x", pady=3, padx=5)

    rid = r.get("id", "")
    short_id = rid[:16] + "..." if len(rid) > 16 else rid
    tk.Label(card, text="Žiadosť: " + short_id, font=("", 10, "bold"), anchor="w", bg="white").pack(fill="x")

    tk.Label(card, text="Parcela: " + r.get("parcelId", "?"), anchor="w", bg="white").pack(fill="x")
    tk.Label(card, text="Predávajúci: " + r.get("requesterUserId", "?"), anchor="w", bg="white").pack(fill="x")

    buyer = r.get("buyerUserId", "")
    if buyer:
        tk.Label(card, text="Kupujúci: " + buyer, anchor="w", bg="white").pack(fill="x")

    status = r.get("status", "?")
    color = STATUS_COLORS.get(status, "#333")
    label = STATUS_LABELS.get(status, status)
    tk.Label(card, text="Stav: " + label, anchor="w", fg=color, font=("", 10, "bold"), bg="white").pack(fill="x")

    history = r.get("statusHistory", [])
    if history:
        hist_frame = tk.Frame(card, bg="white", padx=10)
        hist_frame.pack(fill="x", pady=(4, 0))
        for h in history:
            to_label = STATUS_LABELS.get(h.get("toStatus", ""), h.get("toStatus", ""))
            at = h.get("at", "")
            by = h.get("byUserName", h.get("byUserId", ""))
            line = at + "  " + to_label
            if by:
                line += "  (" + by + ")"
            tk.Label(hist_frame, text=line, anchor="w", fg="#888", font=("", 8), bg="white").pack(fill="x")

    return card


# okno
root = tk.Tk()
root.title("Kataster")
root.geometry("1200x750")

tabs = ttk.Notebook(root)
tabs.pack(fill="both", expand=True)


# ── 1. záložka – Všetky parcely ──────────────────────────────────────────────

tab_par = ttk.Frame(tabs)
tabs.add(tab_par, text="Všetky parcely")

top_par = tk.Frame(tab_par)
top_par.pack(fill="x", padx=10, pady=10)

tk.Label(top_par, text="Org:").pack(side="left")
par_org = tk.Entry(top_par, width=12)
par_org.insert(0, "Cadastre")
par_org.pack(side="left", padx=5)

tk.Label(top_par, text="Používateľ:").pack(side="left")
par_user = tk.Entry(top_par, width=12)
par_user.insert(0, "CADAS002")
par_user.pack(side="left", padx=5)

par_count = tk.Label(top_par, text="", fg="#555")
par_count.pack(side="left", padx=10)

par_list_frame = tk.Frame(tab_par)
par_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
par_inner = make_scrollable(par_list_frame)


def on_load_parcels():
    for w in par_inner.winfo_children():
        w.destroy()
    par_count.config(text="Načítavam...")
    root.update()
    out = curl_get("GetAllParcels", [], par_org.get(), par_user.get())
    parcels = parse_list(out)
    for w in par_inner.winfo_children():
        w.destroy()
    if not parcels:
        resp = parse_response(out)
        if resp.get("error"):
            par_count.config(text="Chyba: " + str(resp["error"]))
        else:
            par_count.config(text="Žiadne parcely.")
        return
    par_count.config(text=str(len(parcels)) + " parciel")
    for p in parcels:
        render_parcel_card(par_inner, p)


tk.Button(top_par, text="Načítať parcely", command=on_load_parcels).pack(side="left", padx=10)


# ── 2. záložka – Všetky žiadosti ─────────────────────────────────────────────

tab_all = ttk.Frame(tabs)
tabs.add(tab_all, text="Všetky žiadosti")

top_all = tk.Frame(tab_all)
top_all.pack(fill="x", padx=10, pady=10)

tk.Label(top_all, text="Org:").pack(side="left")
all_org = tk.Entry(top_all, width=12)
all_org.insert(0, "Cadastre")
all_org.pack(side="left", padx=5)

tk.Label(top_all, text="Používateľ:").pack(side="left")
all_user = tk.Entry(top_all, width=12)
all_user.insert(0, "CADAS002")
all_user.pack(side="left", padx=5)

all_count = tk.Label(top_all, text="", fg="#555")
all_count.pack(side="left", padx=10)

all_list_frame = tk.Frame(tab_all)
all_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
all_inner = make_scrollable(all_list_frame)


def on_load_all_requests():
    for w in all_inner.winfo_children():
        w.destroy()
    all_count.config(text="Načítavam...")
    root.update()
    out = curl_get("GetAllChangeRequests", [], all_org.get(), all_user.get())
    reqs = parse_list(out)
    for w in all_inner.winfo_children():
        w.destroy()
    if not reqs:
        resp = parse_response(out)
        if resp.get("error"):
            all_count.config(text="Chyba: " + str(resp["error"]))
        else:
            all_count.config(text="Žiadne žiadosti.")
        return
    all_count.config(text=str(len(reqs)) + " žiadostí")
    for r in reqs:
        render_request_card(all_inner, r)


tk.Button(top_all, text="Načítať žiadosti", command=on_load_all_requests).pack(side="left", padx=10)


# spoločné funkcie
def build_request_list(parent, org_entry, user_entry, status_actions, mine_only=False, mine_field="requesterUserId"):
    list_frame = tk.Frame(parent)
    list_frame.pack(fill="both", expand=True, padx=10, pady=5)
    inner = make_scrollable(list_frame)

    info_label = tk.Label(parent, text="", anchor="w", justify="left", fg="#444")
    info_label.pack(fill="x", padx=10)

    def refresh():
        for w in inner.winfo_children():
            w.destroy()
        out = curl_get("GetAllChangeRequests", [], org_entry.get(), user_entry.get())
        reqs = parse_list(out)
        if mine_only:
            me = user_entry.get()
            reqs = [r for r in reqs if r.get(mine_field) == me]
        reqs = [r for r in reqs if r.get("status") in status_actions]
        if not reqs:
            tk.Label(inner, text="Žiadne žiadosti.").pack(pady=10)
            return
        for r in reqs:
            card = render_request_card(inner, r)

            btns = tk.Frame(card, bg="white")
            btns.pack(fill="x", pady=(6, 0))
            for label, fcn in status_actions.get(r.get("status"), []):
                rid = r.get("id", "")

                def make_cmd(rid=rid, fcn=fcn):
                    def _():
                        res = curl_post(fcn, [rid], org_entry.get(), user_entry.get())
                        info_label.config(text=format_response(res))
                        resp = parse_response(res)
                        if resp.get("error"):
                            info_label.config(fg="#F44336")
                        else:
                            info_label.config(fg="#4CAF50")
                        refresh()
                    return _

                tk.Button(btns, text=label, command=make_cmd()).pack(side="left", padx=(0, 6))

    return refresh


# ── 3. záložka – Predávajúci ─────────────────────────────────────────────────

tab_sell = ttk.Frame(tabs)
tabs.add(tab_sell, text="Predávajúci")

top_sell = tk.Frame(tab_sell)
top_sell.pack(fill="x", padx=10, pady=10)

tk.Label(top_sell, text="Org:").pack(side="left")
sell_org = tk.Entry(top_sell, width=12)
sell_org.insert(0, "Cadastre")
sell_org.pack(side="left", padx=5)

tk.Label(top_sell, text="Používateľ:").pack(side="left")
sell_user = tk.Entry(top_sell, width=14)
sell_user.insert(0, "JANKO001")
sell_user.pack(side="left", padx=5)

sell_msg = tk.Label(top_sell, text="", fg="#444", anchor="w", justify="left")
sell_msg.pack(side="left", padx=10)

# — moje parcely —
sell_parcels_frame = tk.LabelFrame(tab_sell, text="Moje parcely", padx=10, pady=10)
sell_parcels_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

sell_parcels_list = tk.Frame(sell_parcels_frame)
sell_parcels_list.pack(fill="both", expand=True)
sell_parcels_inner = make_scrollable(sell_parcels_list)


def on_load_my_parcels():
    for w in sell_parcels_inner.winfo_children():
        w.destroy()
    sell_msg.config(text="Načítavam...", fg="#555")
    root.update()
    out = curl_get("GetAllParcels", [], sell_org.get(), sell_user.get())
    parcels = parse_list(out)
    me = sell_user.get()
    my_parcels = [p for p in parcels if any(o.get("userId") == me for o in p.get("owners", []))]
    for w in sell_parcels_inner.winfo_children():
        w.destroy()
    if not my_parcels:
        sell_msg.config(text="Žiadne parcely.", fg="#555")
        return
    sell_msg.config(text=str(len(my_parcels)) + " parciel", fg="#555")

    for p in my_parcels:
        card = render_parcel_card(sell_parcels_inner, p)

        my_owner = None
        for o in p.get("owners", []):
            if o.get("userId") == me:
                my_owner = o
                break
        my_share = my_owner.get("share", "1/1") if my_owner else "1/1"
        parcel_id = p.get("id", "")

        sell_form = tk.Frame(card, bg="white")

        def show_sell_form(card=card, form=sell_form, pid=parcel_id, share=my_share):
            form.pack(fill="x", pady=(8, 0))

            row1 = tk.Frame(form, bg="white")
            row1.pack(fill="x", pady=2)
            tk.Label(row1, text="Kupujúci:", bg="white").pack(side="left")
            buyer_entry = tk.Entry(row1, width=16)
            buyer_entry.pack(side="left", padx=5)
            tk.Label(row1, text="Podiel:", bg="white").pack(side="left", padx=(10, 0))
            share_entry = tk.Entry(row1, width=8)
            share_entry.insert(0, share)
            share_entry.pack(side="left", padx=5)

            form_msg = tk.Label(form, text="", anchor="w", bg="white")
            form_msg.pack(fill="x")

            def do_sell():
                buyer = buyer_entry.get().strip()
                sh = share_entry.get().strip()
                if not buyer:
                    form_msg.config(text="Zadaj kupujúceho.", fg="#F44336")
                    return
                change = {
                    "type": "TRANSFER_SHARE",
                    "fromUserId": sell_user.get(),
                    "toUserId": buyer,
                    "share": sh,
                }
                req = {
                    "parcelId": pid,
                    "requesterUserId": sell_user.get(),
                    "changeJson": json.dumps(change),
                }
                out = curl_post("CreateChangeRequest", [json.dumps(req)], sell_org.get(), sell_user.get())
                resp = parse_response(out)
                if resp.get("error"):
                    form_msg.config(text=format_response(out), fg="#F44336")
                else:
                    form_msg.config(text=format_response(out), fg="#4CAF50")
                    refresh_sell()

            def cancel():
                form.pack_forget()
                for w in form.winfo_children():
                    w.destroy()
                sell_btn.pack(anchor="w", pady=(6, 0))

            row2 = tk.Frame(form, bg="white")
            row2.pack(fill="x", pady=4)
            tk.Button(row2, text="Odoslať žiadosť", command=do_sell).pack(side="left", padx=(0, 6))
            tk.Button(row2, text="Zrušiť", command=cancel).pack(side="left")

        sell_btn = tk.Button(card, text="Predať", command=lambda f=show_sell_form: (sell_btn_ref[0].pack_forget(), f()), bg="#FF9800", fg="white")
        sell_btn.pack(anchor="w", pady=(6, 0))
        sell_btn_ref = [sell_btn]

        def make_show(btn=sell_btn, fn=show_sell_form):
            def _():
                btn.pack_forget()
                fn()
            return _

        sell_btn.config(command=make_show())


tk.Button(top_sell, text="Načítať moje parcely", command=on_load_my_parcels).pack(side="left", padx=5)

# — moje aktívne žiadosti —
sell_req_frame = tk.LabelFrame(tab_sell, text="Moje aktívne žiadosti", padx=10, pady=10)
sell_req_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

sell_actions = {
    "BUYER_APPROVED": [("Potvrdiť platbu", "RequesterConfirmPayment")],
    "SUBMITTED": [],
    "PAYMENT_CONFIRMED": [],
    "CADASTRE_APPROVED": [],
    "DISTRICT_APPROVED": [],
}
refresh_sell = build_request_list(
    sell_req_frame, sell_org, sell_user, sell_actions,
    mine_only=True, mine_field="requesterUserId",
)
tk.Button(top_sell, text="Načítať žiadosti", command=lambda: refresh_sell()).pack(side="left", padx=5)


# ── 4. záložka – Kupujúci ────────────────────────────────────────────────────

tab_buy = ttk.Frame(tabs)
tabs.add(tab_buy, text="Kupujúci")

top_buy = tk.Frame(tab_buy)
top_buy.pack(fill="x", padx=10, pady=10)

tk.Label(top_buy, text="Org:").pack(side="left")
buy_org = tk.Entry(top_buy, width=12)
buy_org.insert(0, "Cadastre")
buy_org.pack(side="left", padx=5)

tk.Label(top_buy, text="Používateľ:").pack(side="left")
buy_user = tk.Entry(top_buy, width=14)
buy_user.insert(0, "EVAKO001")
buy_user.pack(side="left", padx=5)

buy_actions = {
    "SUBMITTED": [
        ("Schváliť", "BuyerApproveChangeRequest"),
        ("Zamietnuť", "BuyerRejectChangeRequest"),
    ],
}
refresh_buy = build_request_list(
    tab_buy, buy_org, buy_user, buy_actions,
    mine_only=True, mine_field="buyerUserId",
)
tk.Button(top_buy, text="Načítať žiadosti", command=lambda: refresh_buy()).pack(side="left", padx=10)


# ── 5. záložka – Kataster ────────────────────────────────────────────────────

tab_cad = ttk.Frame(tabs)
tabs.add(tab_cad, text="Kataster")

top_cad = tk.Frame(tab_cad)
top_cad.pack(fill="x", padx=10, pady=10)

tk.Label(top_cad, text="Org:").pack(side="left")
cad_org = tk.Entry(top_cad, width=12)
cad_org.insert(0, "Cadastre")
cad_org.pack(side="left", padx=5)

tk.Label(top_cad, text="Používateľ:").pack(side="left")
cad_user = tk.Entry(top_cad, width=14)
cad_user.insert(0, "CADAS002")
cad_user.pack(side="left", padx=5)

cad_actions = {
    "PAYMENT_CONFIRMED": [
        ("Schváliť", "CadastreApproveChangeRequest"),
        ("Zamietnuť", "CadastreRejectChangeRequest"),
    ],
    "DISTRICT_APPROVED": [
        ("Vykonať zmenu", "CadastreExecuteChangeRequest"),
    ],
}
refresh_cad = build_request_list(tab_cad, cad_org, cad_user, cad_actions)
tk.Button(top_cad, text="Načítať žiadosti", command=lambda: refresh_cad()).pack(side="left", padx=10)


# ── 6. záložka – Okres ───────────────────────────────────────────────────────

tab_dist = ttk.Frame(tabs)
tabs.add(tab_dist, text="Okres")

top_dist = tk.Frame(tab_dist)
top_dist.pack(fill="x", padx=10, pady=10)

tk.Label(top_dist, text="Org:").pack(side="left")
dist_org = tk.Entry(top_dist, width=12)
dist_org.insert(0, "District")
dist_org.pack(side="left", padx=5)

tk.Label(top_dist, text="Používateľ:").pack(side="left")
dist_user = tk.Entry(top_dist, width=14)
dist_user.insert(0, "DISTR002")
dist_user.pack(side="left", padx=5)

dist_actions = {
    "CADASTRE_APPROVED": [
        ("Schváliť", "DistrictApproveChangeRequest"),
        ("Zamietnuť", "DistrictRejectChangeRequest"),
    ],
}
refresh_dist = build_request_list(tab_dist, dist_org, dist_user, dist_actions)
tk.Button(top_dist, text="Načítať žiadosti", command=lambda: refresh_dist()).pack(side="left", padx=10)


# ── 7. záložka – Nový používateľ ─────────────────────────────────────────────

tab_user = ttk.Frame(tabs)
tabs.add(tab_user, text="Nový používateľ")

form = tk.Frame(tab_user, padx=20, pady=20)
form.pack(anchor="nw")

tk.Label(form, text="Používateľské meno:").pack(anchor="w")
new_username = tk.Entry(form, width=30)
new_username.pack(anchor="w", pady=3)

tk.Label(form, text="Typ používateľa:").pack(anchor="w", pady=(10, 0))
user_type = tk.StringVar(value="obcan")
tk.Radiobutton(form, text="Občan", variable=user_type, value="obcan").pack(anchor="w")
tk.Radiobutton(form, text="Úradník – katastrálny úrad", variable=user_type, value="kataster").pack(anchor="w")
tk.Radiobutton(form, text="Úradník – okresný úrad", variable=user_type, value="okres").pack(anchor="w")

new_msg = tk.Label(form, text="", fg="#444", justify="left", anchor="w")
new_msg.pack(anchor="w", pady=10, fill="x")


def on_create_user():
    name = new_username.get().strip()
    if not name:
        new_msg.config(text="Zadaj používateľské meno.", fg="#F44336")
        return
    typ = user_type.get()
    if typ == "okres":
        org = "District"
        attrs = {"kataster.office": "district"}
    elif typ == "kataster":
        org = "Cadastre"
        attrs = {"kataster.office": "cadastre"}
    else:
        org = "Cadastre"
        attrs = {}
    body = {"username": name, "orgName": org}
    if attrs:
        body["attrs"] = attrs
    out = curl_post_path("/users", body)
    resp = parse_response(out)
    if resp.get("error"):
        new_msg.config(text="Chyba: " + str(resp["error"]), fg="#F44336")
    else:
        msg = "Používateľ vytvorený: " + name + "\nOrg: " + org
        if attrs:
            msg += "\nOprávnenia: " + json.dumps(attrs)
        new_msg.config(text=msg, fg="#4CAF50")


tk.Button(form, text="Pridať používateľa", command=on_create_user).pack(anchor="w", pady=5)


root.mainloop()
