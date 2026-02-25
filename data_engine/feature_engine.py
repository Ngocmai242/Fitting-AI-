import re
import unicodedata
from typing import Dict, List, Tuple


def _normalize(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace for robust matching."""
    if not text:
        return ""
    # Strip accents
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    # Remove special chars but keep spaces
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


ITEM_CATEGORY_RULES: List[Dict[str, object]] = [
    # 1. One-piece & Sets (High Priority for AI Outfit Training)
    {"item_type": "dress", "category": "Dress", "keywords": ["vay", "dam", "dress", "vay lien", "vay lien than", "sundress", "maxi", "midi", "vay xoe", "vay suong", "dam thiet ke", "dam body", "vay body", "vay hoa", "dam suong", "dam du tiec"]},
    {"item_type": "set", "category": "Set_Sleepwear", "keywords": ["pijama", "do ngu", "bo ngu", "bongu", "ngu nu", "ngu nam", "set ngu", "mac nha", "vay ngu", "vayngu", "pyjama", "ao ngu", "do mac nha", "bo ngu lụa"]},
    {"item_type": "set", "category": "Matching_set", "keywords": ["set do", "do bo", "dobo", "matching set", "combo", "nguyen bo", "set quan", "set vay", "bo quan ao", "set trang phuc", "bo cotton", "set he", "set bo", "set nu", "set khoac", "set vest", "set ao quan"]},
    {"item_type": "dress", "category": "Jumpsuit", "keywords": ["jumpsuit", "do bay", "jum"]},
    
    # 2. Outerwear
    {"item_type": "outerwear", "category": "Outer_Blazer", "keywords": ["blazer", "ao blazer", "ao vest", "vest"]},
    {"item_type": "outerwear", "category": "Outer_Jacket", "keywords": ["jacket", "ao khoac", "khoac ngoai", "ao gio", "windbreaker", "ao phao", "denim jacket", "jean jacket", "bomber", "ao khoac bomber", "ao jacket"]},
    {"item_type": "outerwear", "category": "Outer_Coat", "keywords": ["coat", "ao mang to", "ao da", "mang to", "da ep", "da cuu", "da long"]},
    
    # 3. Tops
    {"item_type": "top", "category": "Top_Tshirt", "keywords": ["ao thun", "t-shirt", "tshirt", "tee", "ao phong", "basic tee", "cotton tee", "oversize tee", "form rong"]},
    {"item_type": "top", "category": "Top_Croptop", "keywords": ["crop", "croptop", "cropped", "ao ngan", "ao ho eo", "baby tee", "tre vai"]},
    {"item_type": "top", "category": "Top_Shirt", "keywords": ["so mi", "shirt", "button down", "ao so mi", "somi", "co duc"]},
    {"item_type": "top", "category": "Top_Polo", "keywords": ["ao polo", "polo", "polo shirt", "co be", "ao thun co be"]},
    {"item_type": "top", "category": "Top_Tanktop", "keywords": ["tank", "ba lo", "sat nach", "2 day", "hai day", "camisole", "ao day", "day trang", "ong", "ao quay"]},
    {"item_type": "top", "category": "Top_Sweater", "keywords": ["hoodie", "ao hoodie", "sweater", "ao len", "ao ni", "len tam", "giu nhiet", "det kim", "cardigan", "pullover"]},
    
    # 4. Bottoms
    {"item_type": "bottom", "category": "Bottom_Formal_Trousers", "keywords": ["quan tay", "quan au", "formal pant", "quần tây"]},
    {"item_type": "bottom", "category": "Bottom_Jeans", "keywords": ["jean", "denim", "quan bo", "quan jean", "wide leg", "skinny"]},
    {"item_type": "bottom", "category": "Bottom_Shorts", "keywords": ["short", "quan dui", "quan ngo", "quandui"]},
    {"item_type": "bottom", "category": "Bottom_Jogger", "keywords": ["jogger", "quan jogger", "bo gau", "quan the thao bo", "sweatpants"]},
    {"item_type": "bottom", "category": "Bottom_Skirt", "keywords": ["chan vay", "skirt", "vay chu a", "mini skirt", "vay tennis", "vay xep ly"]},
    {"item_type": "bottom", "category": "Bottom_LongSkirt", "keywords": ["vay dai", "maxi skirt", "vay midi", "vay dai qua goi"]},
    
    # 5. Footwear
    {"item_type": "shoes", "category": "Footwear_Loafers", "keywords": ["loafer", "penny", "giay luoi", "giày lười"]},
    {"item_type": "shoes", "category": "Footwear_Sneakers", "keywords": ["sneaker", "giay the thao", "giay bata"]},
    {"item_type": "shoes", "category": "Footwear_Heels", "keywords": ["cao got", "high heel", "guoc"]},
    {"item_type": "shoes", "category": "Footwear_Sandals", "keywords": ["sandal", "xang dan", "dep quai", "le"]},
    
    # 6. Accessories
    {"item_type": "bag", "category": "Acc_Bag", "keywords": ["tui", "bag", "tui xach", "tui deo"]},
    {"item_type": "accessory", "category": "Acc_Hat", "keywords": ["mu", "non", "hat", "cap"]},
]

COLOR_RULES: Dict[str, List[str]] = {
    "Black": ["den", "black"],
    "White": ["trang", "white"],
    "Grey": ["xam", "ghi", "grey"],
    "Beige": ["beige", "be", "kem"],
    "Brown": ["nau", "brown", "coffee"],
    "Cream": ["cream"],
    "Ivory": ["ivory"],
    "Red": ["do", "red"],
    "Orange": ["cam", "orange"],
    "Coral": ["coral", "san ho"],
    "Pink": ["hong", "pink"],
    "Burgundy": ["burgundy"],
    "Maroon": ["maroon"],
    "Yellow": ["vang", "yellow"],
    "Mustard": ["mustard"],
    "Blue": ["xanh duong", "blue"],
    "Navy": ["navy"],
    "Sky blue": ["xanh da troi", "sky blue"],
    "Mint": ["mint", "xanh bac ha"],
    "Green": ["xanh la", "green"],
    "Olive": ["olive"],
    "Teal": ["teal"],
    "Purple": ["tim", "purple"],
    "Lavender": ["lavender"],
    "Floral": ["hoa", "floral"],
    "Striped": ["ke soc", "striped", "soc"],
    "Plaid": ["caro", "plaid", "checked"],
    "Multicolor": ["nhieu mau", "multi", "rainbow"],
}

COLOR_TONES: Dict[str, str] = {
    "Black": "Neutral",
    "White": "Neutral",
    "Grey": "Neutral",
    "Beige": "Neutral",
    "Brown": "Neutral",
    "Cream": "Neutral",
    "Ivory": "Neutral",
    "Red": "Warm",
    "Orange": "Warm",
    "Coral": "Warm",
    "Pink": "Warm",
    "Burgundy": "Warm",
    "Maroon": "Warm",
    "Yellow": "Warm",
    "Mustard": "Warm",
    "Blue": "Cool",
    "Navy": "Cool",
    "Sky blue": "Cool",
    "Mint": "Cool",
    "Green": "Cool",
    "Olive": "Cool",
    "Teal": "Cool",
    "Purple": "Cool",
    "Lavender": "Cool",
    "Floral": "Pattern",
    "Striped": "Pattern",
    "Plaid": "Pattern",
    "Multicolor": "Pattern",
}

STYLE_RULES: List[Tuple[str, List[str]]] = [
    ("Luxury", ["luxury", "cao cap", "designer"]),
    ("Party", ["party", "du tiec", "tiec"]),
    ("Formal", ["formal", "nghi le", "trang trong"]),
    ("Office", ["cong so", "office", "workwear"]),
    ("Streetwear", ["street", "hiphop", "hip hop", "urban"]),
    ("Minimal", ["minimal", "toi gian"]),
    ("Vintage", ["vintage"]),
    ("Retro", ["retro"]),
    ("Korean", ["korean", "han quoc", "ulzzang"]),
    ("Y2K", ["y2k", "2000s"]),
    ("Elegant", ["elegant", "quy phai", "sang trong"]),
    ("Chic", ["chic"]),
    ("Sporty", ["sporty", "sport", "the thao"]),
    ("Athleisure", ["athleisure", "yoga", "gym"]),
    ("Bohemian", ["boho", "bohemian"]),
    ("Preppy", ["preppy", "hoc duong"]),
    ("Punk", ["punk"]),
    ("Goth", ["goth"]),
    ("Sexy", ["sexy", "goi cam"]),
    ("Cute", ["cute", "de thuong"]),
    ("Feminine", ["nu tinh", "feminine"]),
    ("Masculine", ["nam tinh", "masculine"]),
    ("Unisex", ["unisex"]),
    ("Basic", ["basic"]),
    ("Casual", ["casual"]),
]

SEASON_RULES: List[Tuple[str, List[str]]] = [
    ("Summer", ["summer", "mua he", "nhe", "thoang", "cooling", "mong", "ngan tay", "sat nach", "2 day"]),
    ("Winter", ["winter", "mua dong", "giu am", "am ap", "ao khoac", "ao len"]),
    ("Spring", ["spring", "mua xuan"]),
    ("Autumn", ["autumn", "fall", "mua thu"]),
]

OCCASION_RULES: List[Tuple[str, List[str]]] = [
    ("Wedding", ["dam cuoi", "wedding"]),
    ("Formal event", ["su kien", "formal"]),
    ("Party", ["party", "du tiec"]),
    ("Work", ["cong so", "office", "di lam"]),
    ("School", ["hoc sinh", "school", "college"]),
    ("Travel", ["du lich", "travel", "tour"]),
    ("Date", ["hen ho", "date"]),
    ("Gym", ["gym", "tap luyen", "fitness"]),
    ("Beach", ["bo bien", "beach", "resort"]),
    ("Outdoor", ["da ngoai", "outdoor", "di choi"]),
]

FIT_RULES: List[Tuple[str, List[str]]] = [
    ("Oversize", ["oversize", "form rong", "loose fit", "baggy", "dang rong"]),
    ("Slim fit", ["slim fit", "om vua", "gom vang"]),
    ("Regular fit", ["regular fit", "classic fit"]),
    ("Loose fit", ["loose fit", "relaxed fit"]),
    ("Body fit", ["body fit", "om sat", "bodycon"]),
    ("Cropped", ["cropped", "crop", "lung ngan"]),
    ("High-waist", ["lung cao", "high waist", "high rise"]),
    ("Low-waist", ["lung thap", "low waist"]),
    ("Wide-leg", ["wide leg", "ong rong"]),
    ("Skinny", ["skinny", "ong om"]),
]

MATERIAL_RULES: List[Tuple[str, List[str]]] = [
    ("Cotton", ["cotton", "thun"]),
    ("Denim", ["denim", "jean"]),
    ("Linen", ["linen", "dui", "dui"]),
    ("Leather", ["leather", "da"]),
    ("Polyester", ["polyester", "poly"]),
    ("Wool", ["wool", "len", "cashmere"]),
    ("Silk", ["silk", "lua"]),
    ("Satin", ["satin"]),
    ("Chiffon", ["chiffon", "voan"]),
    ("Velvet", ["velvet", "nhung"]),
    ("Knit", ["knit", "det kim"]),
    ("Fleece", ["fleece"]),
    ("Spandex", ["spandex", "thun lanh"]),
]

GENDER_RULES: List[Tuple[str, List[str]]] = [
    ("Male", ["nam", "men", "male", "boy"]),
    ("Female", ["nu", "women", "female", "girl", "lady"]),
    ("Unisex", ["unisex", "ca tinh"]),
]


REFERENCE_ITEM_TYPES: Dict[str, List[str]] = {}
for rule in ITEM_CATEGORY_RULES:
    item_type = rule["item_type"]  # type: ignore[index]
    category = rule["category"]  # type: ignore[index]
    REFERENCE_ITEM_TYPES.setdefault(item_type, [])
    if category not in REFERENCE_ITEM_TYPES[item_type]:
        REFERENCE_ITEM_TYPES[item_type].append(category)

REFERENCE_COLORS: Dict[str, str] = {color: COLOR_TONES[color] for color in COLOR_RULES.keys()}
REFERENCE_STYLES: List[str] = [style for style, _ in STYLE_RULES]
REFERENCE_SEASONS: List[str] = [season for season, _ in SEASON_RULES] + ["All-season"]
REFERENCE_OCCASIONS: List[str] = [occasion for occasion, _ in OCCASION_RULES] + ["Daily wear"]


class FeatureExtractor:
    """Extract fashion attributes from product names following the project taxonomy."""

    @staticmethod
    def extract(name: str, shopee_cat: str = "") -> Dict[str, str]:
        normalized = _normalize(name)
        
        # 1. Detect via our rules first
        item_type, category = FeatureExtractor._detect_item_and_category(normalized)
        
        # 2. Fallback to mapping rules if "Other" or if shopee_cat is provided and seems useful
        if category == "Other" or "other" in shopee_cat.lower():
            category = FeatureExtractor._map_category_by_keywords(normalized, shopee_cat)
            # Re-detect item_type based on new category if needed
            for rule in ITEM_CATEGORY_RULES:
                if rule["category"] == category:
                    item_type = str(rule["item_type"])
                    break

        color, color_tone = FeatureExtractor._detect_color(normalized)
        style = FeatureExtractor._detect_style(normalized)
        season = FeatureExtractor._detect_season(normalized)
        occasion = FeatureExtractor._detect_occasion(normalized)
        fit = FeatureExtractor._detect_fit(normalized)
        material = FeatureExtractor._detect_material(normalized)
        gender = FeatureExtractor._detect_gender(normalized)

        return {
            "item_type": item_type,
            "category": category,
            "sub_category": category,
            "gender": gender,
            "material": material,
            "style": style,
            "color": color,
            "color_tone": color_tone,
            "season": season,
            "occasion": occasion,
            "fit_type": fit,
            "shopee_category": shopee_cat
        }

    @staticmethod
    def _map_category_by_keywords(name: str, shopee_cat: str) -> str:
        """Specific mapping for AI outfit training as requested by user."""
        # Evaluate longer, more specific keywords first to avoid over-matching (e.g., "chan vay" vs "vay")
        keyword_pairs = [
            ('chan vay', 'Bottom_Skirt'),
            ('skirt', 'Bottom_Skirt'),
            ('vay dai', 'Bottom_LongSkirt'),
            ('maxi skirt', 'Bottom_LongSkirt'),
            ('vay midi', 'Bottom_LongSkirt'),
            ('pijama', 'Set_Sleepwear'),
            ('do ngu', 'Set_Sleepwear'),
            ('loafer', 'Footwear_Loafers'),
            ('t-shirt', 'Top_Tshirt'),
            ('ao thun', 'Top_Tshirt'),
            ('ao polo', 'Top_Polo'),
            ('polo', 'Top_Polo'),
            ('co be', 'Top_Polo'),
            ('quan tay', 'Bottom_Formal_Trousers'),
            ('jogger', 'Bottom_Jogger'),
            ('dam', 'Dress'),
            ('vay', 'Dress'),
            ('blazer', 'Outer_Blazer'),
            ('hoodie', 'Top_Sweater'),
        ]

        # Sort by keyword length descending to prefer more specific phrases
        keyword_pairs.sort(key=lambda kv: len(kv[0]), reverse=True)

        name_lower = name.lower()
        for key, val in keyword_pairs:
            if key in name_lower:
                return val
        
        # If still nothing, return the original Shopee cat if it's not "Other"
        if shopee_cat and "other" not in shopee_cat.lower():
            return shopee_cat
            
        return "Other"

    @staticmethod
    def _detect_item_and_category(text: str) -> Tuple[str, str]:
        text = f" {text} "
        candidates: List[Tuple[int, int, int, str, str, str]] = []
        for idx, rule in enumerate(ITEM_CATEGORY_RULES):
            keywords = rule["keywords"]  # type: ignore
            for kw in keywords:
                if (f" {kw} " in text) or (len(kw) > 5 and kw in text):
                    cat = str(rule["category"])
                    it = str(rule["item_type"])
                    # Tier priority
                    if cat in ("Dress", "Jumpsuit", "Set_Sleepwear", "Matching_set"):
                        tier = 1
                    elif cat.startswith("Outer_"):
                        tier = 2
                    elif cat.startswith("Bottom_"):
                        tier = 3
                    elif cat.startswith("Top_"):
                        tier = 4
                    else:
                        tier = 5
                    candidates.append((tier, -len(kw), idx, it, cat, kw))
        if candidates:
            for _, _, _, it, cat, kw in candidates:
                if cat == "Bottom_Skirt" and (kw == "chan vay" or kw == "skirt" or "chan vay" in kw):
                    return it, cat
            for _, _, _, it, cat, kw in candidates:
                if cat == "Top_Sweater" and ("hoodie" in kw):
                    return it, cat
            for _, _, _, it, cat, kw in candidates:
                if cat == "Bottom_LongSkirt" and ("vay midi" in kw or "vay dai" in kw or "maxi skirt" in kw):
                    return it, cat
            tier, neglen, idx, it, cat, kw = sorted(candidates)[0]
            return it, cat
        return "Other", "Other"

    @staticmethod
    def _detect_color(text: str) -> Tuple[str, str]:
        for color, keywords in COLOR_RULES.items():
            if any(keyword in text for keyword in keywords):
                return color, COLOR_TONES.get(color, "Neutral")
        return "Multicolor", COLOR_TONES.get("Multicolor", "Pattern")

    @staticmethod
    def _detect_style(text: str) -> str:
        for style, keywords in STYLE_RULES:
            if any(keyword in text for keyword in keywords):
                return style
        return "Casual"

    @staticmethod
    def _detect_season(text: str) -> str:
        for season, keywords in SEASON_RULES:
            if any(keyword in text for keyword in keywords):
                return season
        return "All-season"

    @staticmethod
    def _detect_occasion(text: str) -> str:
        for occasion, keywords in OCCASION_RULES:
            if any(keyword in text for keyword in keywords):
                return occasion
        return "Daily wear"

    @staticmethod
    def _detect_fit(text: str) -> str:
        for fit, keywords in FIT_RULES:
            if any(keyword in text for keyword in keywords):
                return fit
        return "Regular fit"

    @staticmethod
    def _detect_material(text: str) -> str:
        for material, keywords in MATERIAL_RULES:
            if any(keyword in text for keyword in keywords):
                return material
        return "Other"

    @staticmethod
    def _detect_gender(text: str) -> str:
        for gender, keywords in GENDER_RULES:
            if any(keyword in text for keyword in keywords):
                return gender
        return "Unisex"


def get_reference_taxonomy() -> Dict[str, object]:
    return {
        "item_types": REFERENCE_ITEM_TYPES,
        "colors": REFERENCE_COLORS,
        "styles": REFERENCE_STYLES,
        "seasons": REFERENCE_SEASONS,
        "occasions": REFERENCE_OCCASIONS,
    }
