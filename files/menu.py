# ============================================================
#  BiteKaro — Menu Definition (Single Source of Truth)
#  5 Categories × 5 Items = 25 Items
# ============================================================

MENU = {
    "hot_beverages": [
        {"id": "HB01", "name": "Espresso",       "price": 80,  "tags": ["coffee","strong","quick","energizing","hot"], "cal": 10},
        {"id": "HB02", "name": "Cappuccino",      "price": 120, "tags": ["coffee","creamy","popular","hot"],            "cal": 120},
        {"id": "HB03", "name": "Masala Chai",     "price": 60,  "tags": ["tea","spicy","comfort","hot","indian"],       "cal": 90},
        {"id": "HB04", "name": "Filter Coffee",   "price": 70,  "tags": ["coffee","strong","south-indian","hot"],       "cal": 80},
        {"id": "HB05", "name": "Hot Chocolate",   "price": 130, "tags": ["sweet","comfort","hot","indulgent"],          "cal": 220},
    ],
    "cold_beverages": [
        {"id": "CB01", "name": "Cold Coffee",     "price": 140, "tags": ["coffee","cold","popular","refreshing"],       "cal": 180},
        {"id": "CB02", "name": "Mango Shake",     "price": 120, "tags": ["fruity","cold","sweet","seasonal","filling"], "cal": 210},
        {"id": "CB03", "name": "Lemonade",        "price": 80,  "tags": ["refreshing","cold","light","tangy"],          "cal": 60},
        {"id": "CB04", "name": "Iced Tea",        "price": 90,  "tags": ["tea","cold","light","refreshing"],            "cal": 70},
        {"id": "CB05", "name": "Cold Brew",       "price": 160, "tags": ["coffee","cold","strong","premium"],           "cal": 15},
    ],
    "snacks": [
        {"id": "SN01", "name": "Samosa",          "price": 30,  "tags": ["indian","veg","fried","spicy","popular"],     "cal": 130},
        {"id": "SN02", "name": "Vada Pav",        "price": 40,  "tags": ["indian","veg","filling","spicy","mumbai"],    "cal": 290},
        {"id": "SN03", "name": "Bread Pakoda",    "price": 50,  "tags": ["indian","veg","fried","comfort","monsoon"],   "cal": 200},
        {"id": "SN04", "name": "Dhokla",          "price": 60,  "tags": ["indian","veg","light","gujarati","healthy"],  "cal": 160},
        {"id": "SN05", "name": "Poha",            "price": 60,  "tags": ["indian","veg","light","breakfast","healthy"], "cal": 180},
    ],
    "meals": [
        {"id": "ML01", "name": "Masala Dosa",     "price": 120, "tags": ["indian","veg","south-indian","filling","meal"],"cal": 380},
        {"id": "ML02", "name": "Pav Bhaji",       "price": 110, "tags": ["indian","veg","filling","spicy","meal"],      "cal": 420},
        {"id": "ML03", "name": "Paneer Wrap",     "price": 130, "tags": ["indian","veg","filling","meal","popular"],    "cal": 390},
        {"id": "ML04", "name": "Chole Bhature",   "price": 140, "tags": ["indian","veg","heavy","spicy","meal"],        "cal": 550},
        {"id": "ML05", "name": "Upma",            "price": 80,  "tags": ["indian","veg","light","breakfast","south-indian"],"cal": 200},
    ],
    "desserts": [
        {"id": "DS01", "name": "Chocolate Muffin","price": 80,  "tags": ["sweet","baked","popular","indulgent"],        "cal": 350},
        {"id": "DS02", "name": "Gulab Jamun",     "price": 60,  "tags": ["indian","sweet","traditional","warm"],        "cal": 180},
        {"id": "DS03", "name": "Brownie",         "price": 90,  "tags": ["sweet","baked","chocolate","indulgent"],      "cal": 320},
        {"id": "DS04", "name": "Kulfi",           "price": 70,  "tags": ["indian","sweet","cold","traditional"],        "cal": 150},
        {"id": "DS05", "name": "Rasgulla",        "price": 50,  "tags": ["indian","sweet","light","traditional"],       "cal": 120},
    ],
}

# Flat list — useful for indexing
ALL_ITEMS = []
for category, items in MENU.items():
    for item in items:
        ALL_ITEMS.append({**item, "category": category})

ITEM_IDS    = [i["id"]   for i in ALL_ITEMS]
ITEM_NAMES  = {i["id"]: i["name"] for i in ALL_ITEMS}
ITEM_LOOKUP = {i["id"]: i          for i in ALL_ITEMS}
ID_TO_IDX   = {iid: idx for idx, iid in enumerate(ITEM_IDS)}
IDX_TO_ID   = {idx: iid for iid, idx in ID_TO_IDX.items()}

# Natural pairings — cross-sell ground truth (from domain knowledge)
# Used to bias synthetic data generation realistically
NATURAL_PAIRINGS = {
    "SN01": ["HB03", "CB01", "HB04"],   # Samosa → Chai, Cold Coffee, Filter Coffee
    "SN02": ["HB03", "CB01", "CB03"],   # Vada Pav → Chai, Cold Coffee, Lemonade
    "SN03": ["HB03", "HB05", "CB04"],   # Bread Pakoda → Chai, Hot Choc, Iced Tea
    "SN04": ["HB03", "HB04", "CB03"],   # Dhokla → Chai, Filter Coffee, Lemonade
    "SN05": ["HB03", "HB04", "CB04"],   # Poha → Chai, Filter Coffee, Iced Tea
    "ML01": ["HB04", "CB03", "CB01"],   # Masala Dosa → Filter Coffee, Lemonade
    "ML02": ["CB03", "CB01", "CB04"],   # Pav Bhaji → Lemonade, Cold Coffee
    "ML03": ["CB01", "CB03", "HB02"],   # Paneer Wrap → Cold Coffee, Lemonade
    "ML04": ["CB03", "CB04", "HB03"],   # Chole Bhature → Lemonade, Iced Tea
    "ML05": ["HB03", "HB04", "CB04"],   # Upma → Chai, Filter Coffee
    "DS01": ["HB02", "CB01", "CB05"],   # Chocolate Muffin → Cappuccino, Cold Coffee
    "DS02": ["HB03", "HB04", "HB05"],   # Gulab Jamun → Chai, Filter Coffee
    "DS03": ["HB02", "CB01", "HB05"],   # Brownie → Cappuccino, Cold Coffee
    "DS04": ["CB01", "CB03", "CB02"],   # Kulfi → Cold Coffee, Lemonade
    "DS05": ["HB03", "HB04", "CB04"],   # Rasgulla → Chai, Filter Coffee
}

if __name__ == "__main__":
    print(f"Total items: {len(ALL_ITEMS)}")
    for cat, items in MENU.items():
        print(f"  {cat}: {[i['name'] for i in items]}")
