import argparse
import os
import shutil
import sqlite3
import sys
import time
import unicodedata


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def get_db_path() -> str:
    # Mirrors backend/app/__init__.py config: database/database_v2.db
    return os.path.abspath(os.path.join(_project_root(), "database", "database_v2.db"))


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = " ".join(s.split())
    # remove accents for more robust keyword matching
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


BOTTOM_KEYWORDS = [
    "quan",
    "jean",
    "jeans",
    "denim",
    "pants",
    "shorts",
    "short",
    "chan vay",
    "skirt",
    "baggy",
    "ong suong",
    "ong rong",
    "skinny",
    "legging",
    "trouser",
    "kaki",
    "jogger",
    "quan tay",
    "quan au",
]

DRESS_KEYWORDS = [
    "dam",
    "vay lien",
    "jumpsuit",
    "maxi",
    "dress",
    "romper",
]


def detect_category(name: str, current_category: str) -> str:
    n = norm(name)
    cur = (current_category or "").strip()
    cur_n = norm(cur)

    # Bottoms first
    if any(k in n for k in BOTTOM_KEYWORDS):
        if any(k in n for k in ["jean", "jeans", "denim", "quan jean", "quan bo"]):
            return "bottoms (jeans)"
        if any(k in n for k in ["short", "shorts", "quan dui", "quan ngan", "dui"]):
            return "bottoms (shorts)"
        if any(k in n for k in ["chan vay", "skirt", "vay ngan", "mini skirt", "midi skirt"]):
            return "bottoms (skirt)"
        return "bottoms (pants)"

    # Dress / full body
    if any(k in n for k in DRESS_KEYWORDS):
        return "dress"

    # Tops
    if any(k in n for k in ["hoodie", "sweatshirt", "ao ni", "ni", "ao hoodie"]):
        return "tops (hoodie)"
    if any(k in n for k in ["khoac", "jacket", "coat", "blazer", "ao khoac"]):
        return "tops (jacket)"
    if "polo" in n:
        return "tops (polo)"
    if any(k in n for k in ["so mi", "shirt", "blouse"]):
        return "tops (shirt)"
    if any(k in n for k in ["croptop", "crop top", "ao ngan"]):
        return "tops (crop)"
    if any(k in n for k in ["thun", "phong", "tee", "t-shirt", "tshirt", "ao thun", "ao phong"]):
        return "tops (t_shirt)"

    # Accessories
    if any(k in n for k in ["giay", "shoe", "tui", "bag", "mu", "hat", "that lung", "belt", "kinh", "glasses", "phu kien", "accessor"]):
        return "accessories"

    # If it's already a known normalized value, keep it.
    if cur_n in ("dress", "accessories") or cur_n.startswith("tops") or cur_n.startswith("bottoms"):
        return cur

    # Unknown → keep original
    return cur


def detect_gender(name: str, existing: str) -> str:
    ex = norm(existing)
    if ex in ("male", "female", "unisex"):
        return ex
    n = norm(name)
    if "unisex" in n:
        return "unisex"
    if any(k in n for k in ["nam", "men", "male"]):
        return "male"
    if any(k in n for k in ["nu", "women", "female", "lady"]):
        return "female"
    return "unisex"


def detect_occasion(existing: str) -> str:
    ex = norm(existing)
    if ex in ("casual", "work", "party", "date", "sport", "beach"):
        return ex
    if any(k in ex for k in ["casual", "daily", "thuong ngay"]):
        return "casual"
    if any(k in ex for k in ["office", "work", "formal", "cong so"]):
        return "work"
    if any(k in ex for k in ["party", "event", "tiec", "su kien"]):
        return "party"
    return "casual"


def detect_style_tag(existing: str) -> str:
    ex = norm(existing)
    if ex in ("streetwear", "korean", "minimalist", "classic", "y2k", "boho", "any"):
        return ex
    if "streetwear" in ex:
        return "streetwear"
    if any(k in ex for k in ["korean", "kpop"]):
        return "korean"
    if "minimal" in ex or "minimalist" in ex:
        return "minimalist"
    if any(k in ex for k in ["classic", "basic"]):
        return "classic"
    if "y2k" in ex:
        return "y2k"
    if "boho" in ex:
        return "boho"
    return "any"


def ensure_columns(cur: sqlite3.Cursor, existing_cols: set[str]) -> None:
    # Add missing metadata columns for training/filters. Safe to run repeatedly.
    alters = [
        ("ALTER TABLE products ADD COLUMN garment_type TEXT DEFAULT '';", "garment_type"),
        ("ALTER TABLE products ADD COLUMN gender TEXT DEFAULT 'unisex';", "gender"),
        ("ALTER TABLE products ADD COLUMN occasion TEXT DEFAULT 'casual';", "occasion"),
        ("ALTER TABLE products ADD COLUMN style_tag TEXT DEFAULT '';", "style_tag"),
        ("ALTER TABLE products ADD COLUMN fit_type TEXT DEFAULT 'regular fit';", "fit_type"),
        ("ALTER TABLE products ADD COLUMN season TEXT DEFAULT 'all-season';", "season"),
        ("ALTER TABLE products ADD COLUMN color_tone TEXT DEFAULT 'neutral';", "color_tone"),
        ("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT '';", "image_url"),
        ("ALTER TABLE products ADD COLUMN shopee_url TEXT DEFAULT '';", "shopee_url"),
        ("ALTER TABLE products ADD COLUMN category TEXT;", "category"),
    ]
    for sql, col in alters:
        if col in existing_cols:
            continue
        try:
            cur.execute(sql)
            existing_cols.add(col)
        except Exception:
            # ignore if already exists / sqlite limitation
            pass


def main() -> int:
    # Ensure Windows console can print Vietnamese logs
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Print changes without updating DB")
    args = ap.parse_args()

    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"[ERR] DB not found: {db_path}")
        return 2

    # Backup (always, unless dry-run)
    if not args.dry_run:
        ts = time.strftime("%Y%m%d_%H%M%S")
        backup_path = db_path + f".bak_{ts}"
        shutil.copy2(db_path, backup_path)
        print(f"[OK] Backup created: {backup_path}")
    else:
        print("[DRY-RUN] No DB writes will be performed.")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(products)")
    cols = {r[1] for r in cur.fetchall()}
    ensure_columns(cur, cols)

    # Read all products we can normalize
    select_cols = ["id", "name"]
    for c in ["category", "gender", "occasion", "occasion_label", "style_tag", "style_label", "garment_type"]:
        if c in cols:
            select_cols.append(c)
    cur.execute(f"SELECT {', '.join(select_cols)} FROM products")
    rows = cur.fetchall()

    total = 0
    fixed = 0

    for r in rows:
        total += 1
        pid = r["id"]
        name = r["name"] or ""
        old_cat = r["category"] if "category" in r.keys() else ""

        new_cat = detect_category(name, old_cat)

        old_gender = r["gender"] if "gender" in r.keys() else ""
        new_gender = detect_gender(name, old_gender)

        occ_src = ""
        if "occasion" in r.keys() and r["occasion"]:
            occ_src = r["occasion"]
        elif "occasion_label" in r.keys() and r["occasion_label"]:
            occ_src = r["occasion_label"]
        new_occasion = detect_occasion(occ_src)

        style_src = ""
        if "style_tag" in r.keys() and r["style_tag"]:
            style_src = r["style_tag"]
        elif "style_label" in r.keys() and r["style_label"]:
            style_src = r["style_label"]
        new_style = detect_style_tag(style_src)

        # garment_type = category (after normalized)
        new_garment = new_cat or (r["garment_type"] if "garment_type" in r.keys() else "")

        changes = {}
        if "category" in cols and (new_cat and (new_cat != (old_cat or ""))):
            changes["category"] = new_cat
        if "garment_type" in cols and new_garment and (new_garment != (r["garment_type"] or "" if "garment_type" in r.keys() else "")):
            changes["garment_type"] = new_garment

        # Only fill gender/style_tag/occasion if empty or non-canonical
        if "gender" in cols:
            exg = (old_gender or "").strip()
            if not exg or norm(exg) not in ("male", "female", "unisex"):
                if new_gender != norm(exg):
                    changes["gender"] = new_gender
        if "occasion" in cols:
            exo = (r["occasion"] or "").strip() if "occasion" in r.keys() else ""
            if not exo or norm(exo) not in ("casual", "work", "party", "date", "sport", "beach"):
                changes["occasion"] = new_occasion
        if "style_tag" in cols:
            exs = (r["style_tag"] or "").strip() if "style_tag" in r.keys() else ""
            if not exs or norm(exs) == "":
                changes["style_tag"] = new_style

        if changes:
            fixed += 1
            print(f'[FIX] ID={pid}: "{name}"')
            for k, v in changes.items():
                oldv = r[k] if k in r.keys() else ""
                print(f'      {k}: "{oldv}" -> "{v}"')

            if not args.dry_run:
                sets = ", ".join([f"{k} = ?" for k in changes.keys()])
                params = list(changes.values()) + [pid]
                cur.execute(f"UPDATE products SET {sets} WHERE id = ?", params)
        else:
            cat_disp = old_cat or (r["category"] if "category" in r.keys() else "")
            print(f'[OK]  ID={pid}: "{name}" | "{cat_disp}"')

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(f"\nTổng kết: Đã fix {fixed} sản phẩm / Tổng {total} sản phẩm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

