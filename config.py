import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))

# معلومات الدفع
USDT_WALLET = os.environ.get("USDT_WALLET", "ضع_محفظة_USDT_هنا")
SYRIATEL_CASH = os.environ.get("SYRIATEL_CASH", "ضع_رقم_سيريتيل_كاش_هنا")

# سعر صرف الليرة السورية | SYP Exchange Rate (SYP per 1 USD)
# سعر صرف الليرة السورية (العملة الجديدة) | SYP Exchange Rate (new currency)
# القيمة الافتراضية 140 — عدّلها في Railway Variables متى احتجت
SYP_RATE = float(os.environ.get("SYP_RATE", "140"))

# Proxy Config
PROXY_TYPES = {
    "http": " HTTP/HTTPS",
    "socks5": " SOCKS5",
    "residential": " Residential",
    "mobile": " Mobile 4G/5G",
    "modem": " Modem Private",
}


# ══════════════════════════════════════════════════════
# AppsFlyer Games Config
# ══════════════════════════════════════════════════════
APPSFLYER_GAMES = {
    "domino_dream":        {"name": "Domino Dreams",         "price_usd": float(os.environ.get("AF_PRICE_DOMINO",   "4"))},
    "disney_dream":        {"name": "Disney Dream",          "price_usd": float(os.environ.get("AF_PRICE_DISNEY",   "4"))},
    "coin_master":         {"name": "Coin Master",           "price_usd": float(os.environ.get("AF_PRICE_COIN",     "4"))},
    "travel_town":         {"name": "Travel Town",           "price_usd": float(os.environ.get("AF_PRICE_TRAVEL",   "4"))},
    "yarn_loop":           {"name": "Yarn Loop",             "price_usd": float(os.environ.get("AF_PRICE_YARN",     "4"))},
    "dice_dream":          {"name": "Dice Dreams",           "price_usd": float(os.environ.get("AF_PRICE_DICE",     "4"))},
    "toy_blast":           {"name": "Toy Blast",             "price_usd": float(os.environ.get("AF_PRICE_TOY",      "4"))},
    "toon_blast":          {"name": "Toon Blast",            "price_usd": float(os.environ.get("AF_PRICE_TOON",     "4"))},
    "match_factory":       {"name": "Match Factory",         "price_usd": float(os.environ.get("AF_PRICE_MATCH",    "4"))},
    "royal_kingdom":       {"name": "Royal Kingdom",         "price_usd": float(os.environ.get("AF_PRICE_ROYAL",    "4"))},
    "board_adventure":     {"name": "Board Adventure",       "price_usd": float(os.environ.get("AF_PRICE_BOARD",    "4"))},
    "disney_solitaire":    {"name": "Disney Solitaire",      "price_usd": float(os.environ.get("AF_PRICE_DSOL",     "4"))},
    "homescapes":          {"name": "Homescapes",            "price_usd": float(os.environ.get("AF_PRICE_HOME",     "4"))},
    "screw_guru":          {"name": "Screw Guru",            "price_usd": float(os.environ.get("AF_PRICE_SCREW",    "4"))},
    "empires":             {"name": "⚔️ Empires",            "price_usd": float(os.environ.get("AF_PRICE_EMPIRES",  "4"))},
    "zombie_miner":        {"name": "Zombie Miner",          "price_usd": float(os.environ.get("AF_PRICE_ZOMBIE",   "4"))},
    "family_island":       {"name": "Family Island",         "price_usd": float(os.environ.get("AF_PRICE_FAMILY",   "4"))},
    "fishdom":             {"name": "Fishdom",               "price_usd": float(os.environ.get("AF_PRICE_FISH",     "4"))},
    "goods_master_3d":     {"name": "Goods Master 3D",       "price_usd": float(os.environ.get("AF_PRICE_GOODS",    "4"))},
    "matching_story":      {"name": "Matching Story",        "price_usd": float(os.environ.get("AF_PRICE_MSTORY",   "4"))},
    "solitaire_harvest":   {"name": "Solitaire Grand Harvest","price_usd": float(os.environ.get("AF_PRICE_SHARVEST","4"))},
    "farmville_3":         {"name": "FarmVille 3",           "price_usd": float(os.environ.get("AF_PRICE_FARM",       "4"))},
    "box_jam":             {"name": "Box Jam",                "price_usd": float(os.environ.get("AF_PRICE_BOXJAM",     "4"))},
    "glow_tales":          {"name": "Glow Tales",             "price_usd": float(os.environ.get("AF_PRICE_GLOW",       "4"))},
    "soliter_stash":       {"name": "Soliter Stash",          "price_usd": float(os.environ.get("AF_PRICE_SSTASH",     "4"))},
    "solitaire_cash":      {"name": "Solitaire Cash",         "price_usd": float(os.environ.get("AF_PRICE_SCASH",      "4"))},
    "phase_10":            {"name": "Phase 10",               "price_usd": float(os.environ.get("AF_PRICE_PHASE10",    "4"))},
    "love_fashion":        {"name": "Love & Fashion",         "price_usd": float(os.environ.get("AF_PRICE_LOVEFASH",   "4"))},
    "cash_legends":        {"name": "Cash Legends",           "price_usd": float(os.environ.get("AF_PRICE_CASHLEG",    "4"))},
    "royal_match":         {"name": "Royal Match",            "price_usd": float(os.environ.get("AF_PRICE_ROYALMATCH", "4"))},
    "klondike":            {"name": "Klondike",               "price_usd": float(os.environ.get("AF_PRICE_KLONDIKE",   "4"))},
    "unravel_master":      {"name": "Unravel Master",         "price_usd": float(os.environ.get("AF_PRICE_UNRAVEL",    "4"))},
    "junes_journey":       {"name": "June's Journey",         "price_usd": float(os.environ.get("AF_PRICE_JUNES",      "4"))},
    "idle_outpost":        {"name": "IdleOutpost",            "price_usd": float(os.environ.get("AF_PRICE_IDLE",       "4"))},
    "solitaire_smash":     {"name": "Solitaire Smash",        "price_usd": float(os.environ.get("AF_PRICE_SSMASH",     "4"))},
    "merge_sweets":        {"name": "Merge Sweets",           "price_usd": float(os.environ.get("AF_PRICE_MSWEETS",    "4"))},
    "merge_mansion":       {"name": "Merge Mansion",          "price_usd": float(os.environ.get("AF_PRICE_MMANSION",   "4"))},
    "mergedragons_power":  {"name": "MergeDragons! Power",    "price_usd": float(os.environ.get("AF_PRICE_MDPOWER",    "4"))},
    "mergedragons_level":  {"name": "MergeDragons! Level",    "price_usd": float(os.environ.get("AF_PRICE_MDLEVEL",    "4"))},
    "screw_tap_jam":       {"name": "Screw Tap Jam",          "price_usd": float(os.environ.get("AF_PRICE_SCREWTAP",   "4"))},
    "sort_journey":        {"name": "Sort Journey",           "price_usd": float(os.environ.get("AF_PRICE_SORTJ",      "4"))},
    "immortal":            {"name": "Immortal",               "price_usd": float(os.environ.get("AF_PRICE_IMMORTAL",   "4"))},
}
