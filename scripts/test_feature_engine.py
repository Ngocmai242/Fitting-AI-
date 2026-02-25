import sys
sys.path.insert(0, 'g:/1')
from data_engine.feature_engine import FeatureExtractor

samples = [
    "chan vay denim dang A",
    "chan vay xep ly mini skirt",
    "vay midi dai qua goi",
    "vay lien bodycon du tiec",
    "dam maxi hoa nu tinh",
    "dam len tam co cao",
    "skirt nu chu A basic",
    "ao polo co be",
    "quan jogger the thao bo gau",
    "set do ngu satin nu",
]

for s in samples:
    f = FeatureExtractor.extract(s, "")
    print(f"{s} -> {f['item_type']} | {f['category']}")
