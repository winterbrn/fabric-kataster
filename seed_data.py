"""Deterministic generator for 300 parcels and 300 owners."""
import random
import unicodedata

FIRST_NAMES = [
    "Ján", "Peter", "Martin", "Tomáš", "Marek", "Pavol", "Roman", "Štefan",
    "Miloš", "Juraj", "Dávid", "Lukáš", "Matej", "Filip", "Adam", "Andrej",
    "Jakub", "Michal", "Daniel", "Samuel", "Ivan", "Vladimír", "Jozef",
    "Radoslav", "Erik", "Patrik", "Tibor", "Róbert", "František", "Ladislav",
    "Eva", "Mária", "Anna", "Jana", "Zuzana", "Denisa", "Simona", "Lenka",
    "Helena", "Katarína", "Barbora", "Monika", "Petra", "Kristína", "Ivana",
    "Martina", "Lucia", "Veronika", "Nikola", "Natália", "Soňa", "Beáta",
    "Alena", "Diana", "Silvia", "Renáta", "Tatiana", "Gabriela", "Dominika",
    "Andrea",
]

LAST_NAMES = [
    "Hruška", "Kováč", "Hrubý", "Slaný", "Urban", "Novák", "Kráľ",
    "Hradský", "Gregor", "Mráz", "Szabó", "Mišík", "Kučera", "Vlček",
    "Krištof", "Baláž", "Varga", "Horváth", "Tóth", "Nagy", "Molnár",
    "Černý", "Dvořák", "Pospíšil", "Sedláček", "Beneš", "Procházka",
    "Šimek", "Polák", "Kolář",
]

STREETS = [
    "Ružinovská", "Záhradná", "Bajkalská", "Trnavská", "Karadžičova",
    "Prievozská", "Mlynské nivy", "Račianska", "Kukučínova", "Šancová",
    "Obchodná", "Dunajská", "Grösslingová", "Dostojevského", "Mickiewiczova",
    "Vazovova", "Radlinského", "Budovateľská", "Ľubovnianska", "Ipeľská",
]

LAND_TYPES = [
    ("Záhrada", 10),
    ("Zastavaná plocha a nádvorie", 20),
    ("Orná pôda", 30),
    ("Zastavaná plocha a nádvorie", 20),
    ("Záhrada", 10),
    ("Zastavaná plocha a nádvorie", 20),
    ("Orná pôda", 30),
]

BURDENS = [
    "Bez tiarch.", "Bez tiarch.", "Bez tiarch.", "Bez tiarch.",
    "Slovenská sporiteľňa", "Bez tiarch.", "vecné bremeno", "Bez tiarch.",
]

TOTAL = 300
GRID_COLS = 20
GRID_ROWS = 15
CELL_W = 40
CELL_H = 35
ORIGIN_X = 50
ORIGIN_Y = 20


def _strip_diacritics(s):
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def generate_users(count=TOTAL):
    rng = random.Random(42)
    pairs = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
    rng.shuffle(pairs)
    pairs = pairs[:TOTAL]

    seen_ids = {}
    users = []
    for i, (first, last) in enumerate(pairs):
        prefix = _strip_diacritics(first)[:3].upper() + _strip_diacritics(last)[:2].upper()
        n = seen_ids.get(prefix, 0) + 1
        seen_ids[prefix] = n
        uid = f"{prefix}{n:03d}"

        street = STREETS[i % len(STREETS)]
        house_num = (i * 4) + 1
        birth_year = 1970 + (i % 35)
        birth_month = (i % 12) + 1
        birth_day = (i % 28) + 1

        users.append({
            "first_name": first,
            "last_name": last,
            "userId": uid,
            "address": f"{street} {house_num}, 821 01 Bratislava",
            "birthDate": f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
        })

    return users[:count]


def generate_parcels(count=TOTAL):
    rng = random.Random(123)
    users = generate_users(TOTAL)

    parcels = []
    for i in range(min(count, TOTAL)):
        row = i // GRID_COLS
        col = i % GRID_COLS

        x0 = ORIGIN_X + col * CELL_W + rng.randint(-2, 2)
        y0 = ORIGIN_Y + row * CELL_H + rng.randint(-2, 2)
        x1 = x0 + CELL_W + rng.randint(-2, 2)
        y1 = y0 + CELL_H + rng.randint(-2, 2)

        land_type, usage_code = LAND_TYPES[i % len(LAND_TYPES)]
        burden = BURDENS[i % len(BURDENS)]
        area = 500 + rng.randint(0, 1500)

        parcel_num_a = 100 + (i // 10)
        parcel_num_b = (i % 10) + 1

        u = users[i]

        parcels.append({
            "id": f"parcel-ba-ruzinov-{i + 1:06d}",
            "parcelId": f"P-{i + 1:03d}",
            "parcelNumber": f"{parcel_num_a}/{parcel_num_b}",
            "listOwnershipNumber": 1001 + i,
            "cadastralArea": "Bratislava",
            "area": area,
            "landType": land_type,
            "usageMethodCode": usage_code,
            "protectedPropertyTypeCode": 0,
            "isCommonProperty": False,
            "location": "v_zastavanom_uzemi_obce",
            "legalRelationshipTypeCode": 1,
            "owners": [{
                "name": f"{u['first_name']} {u['last_name']}",
                "share": "1/1",
                "userId": u["userId"],
                "address": u["address"],
                "birthDate": u["birthDate"],
            }],
            "burdens": burden,
            "points": [
                {"x": x0, "y": y0},
                {"x": x1, "y": y0},
                {"x": x1, "y": y1},
                {"x": x0, "y": y1},
            ],
        })

    return parcels
