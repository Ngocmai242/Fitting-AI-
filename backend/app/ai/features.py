import math

def _dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def compute_ratios(points):
    ls = points["left_shoulder"]
    rs = points["right_shoulder"]
    lh = points["left_hip"]
    rh = points["right_hip"]
    la = points["left_ankle"]
    ra = points["right_ankle"]
    nose = points["nose"]
    shoulder_w = _dist(ls, rs)
    hip_w = _dist(lh, rh)
    waist_w = min(shoulder_w, hip_w) * 0.85
    top_y = min(nose[1], ls[1], rs[1])
    ankle_y = max(la[1], ra[1])
    height = max(ankle_y - top_y, 1)
    leg_len = max(ankle_y - ((lh[1]+rh[1])//2), 1)
    shoulder_ratio = round(shoulder_w/height, 3)
    hip_ratio = round(hip_w/height, 3)
    waist_ratio = round(waist_w/height, 3)
    leg_ratio = round(leg_len/height, 3)
    return {
        "shoulder_ratio": shoulder_ratio,
        "waist_ratio": waist_ratio,
        "hip_ratio": hip_ratio,
        "leg_ratio": leg_ratio
    }

def estimate_gender(ratios):
    """
    Heuristic gender estimation from body proportions.
    Returns (label, confidence) where label in {"Male","Female","Uncertain"}.
    Conservative thresholds to reduce misclassification.
    """
    s = ratios.get("shoulder_ratio", 0.0)
    h = ratios.get("hip_ratio", 0.0)
    w = ratios.get("waist_ratio", 0.0)
    shoulder_dom = s - h
    hip_dom = h - s

    # Normalize margins to [0,1] scale for confidence contribution
    def _nz(x): 
        return x if x > 0 else 0.0
    # Shoulder-dominant and waist not extremely small -> more likely Male
    if shoulder_dom > 0.06 and w >= (min(s, h) * 0.80):
        conf = min(0.95, 0.6 + _nz(shoulder_dom - 0.05) * 5.0 + _nz(w - min(s, h) * 0.80) * 3.0)
        return "Male", round(conf, 3)
    # Hip-dominant and waist relatively smaller -> more likely Female
    if hip_dom > 0.03 and w <= (min(s, h) * 0.95):
        conf = min(0.95, 0.6 + _nz(hip_dom - 0.05) * 5.0 + _nz((min(s, h) * 0.95) - w) * 3.0)
        return "Female", round(conf, 3)
    # Otherwise uncertain
    return "Uncertain", 0.5
