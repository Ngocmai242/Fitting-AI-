import os
import pickle

_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "bodyshape_rf.pkl"))
_RF = None
if os.path.exists(_MODEL_PATH):
    try:
        with open(_MODEL_PATH, "rb") as f:
            _RF = pickle.load(f)
    except Exception:
        _RF = None

def _rule_based_shape(ratios):
    """
    Conservative rules using reliable landmarks (shoulder vs hip widths).
    We avoid relying on 'waist' because it is approximated.
    """
    s = ratios["shoulder_ratio"]
    h = ratios["hip_ratio"]
    delta = s - h
    if abs(delta) < 0.02:
        return "H"
    if delta >= 0.05:
        return "V"
    if delta <= -0.03:
        return "A"
    return "H"

def predict_shape(ratios):
    global _RF
    # If trained model exists, prefer it
    if _RF is not None:
        x = [[ratios["shoulder_ratio"], ratios["waist_ratio"], ratios["hip_ratio"], ratios["leg_ratio"]]]
        try:
            pred = _RF.predict(x)[0]
            return str(pred)
        except Exception:
            pass
    return _rule_based_shape(ratios)

def predict_shape_with_confidence(ratios, threshold: float = 0.6):
    """
    Hybrid classifier:
    - If RF model available: use predict_proba for confidence.
      If confidence < threshold, fallback to rule-based and tag source='rule_fallback'.
    - If no model: use rule-based and estimate confidence from margin.
    Returns: (shape, confidence, source)
    """
    global _RF
    x = [[ratios["shoulder_ratio"], ratios["waist_ratio"], ratios["hip_ratio"], ratios["leg_ratio"]]]
    if _RF is not None:
        try:
            # If model exposes predict_proba
            if hasattr(_RF, "predict_proba"):
                proba = _RF.predict_proba(x)[0]
                idx = int(proba.argmax())
                labels = getattr(_RF, "classes_", ["A", "H", "V", "X"])
                pred_label = str(labels[idx])
                conf = float(proba[idx])
                if conf >= threshold:
                    return pred_label, conf, "ml"
                # Low confidence → fallback to rules
                rule_label = _rule_based_shape(ratios)
                # Blend confidence slightly above threshold for transparency
                return rule_label, conf, "rule_fallback"
            else:
                pred = _RF.predict(x)[0]
                return str(pred), 0.6, "ml_no_proba"
        except Exception:
            pass
    # No model or error → rule-based with heuristic confidence
    s = ratios["shoulder_ratio"]; h = ratios["hip_ratio"]
    margin_shoulder_hip = abs(s - h)
    # Confidence from how clear shoulder vs hip dominance is
    raw = min(1.0, max(0.0, (margin_shoulder_hip - 0.02) * 12))
    conf = 0.5 + 0.4 * raw
    return _rule_based_shape(ratios), float(conf), "rule"
