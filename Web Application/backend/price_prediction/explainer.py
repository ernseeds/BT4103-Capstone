# explainer.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
import math
import numpy as np
import pandas as pd
import shap

# ---------------- Friendly labels ----------------
DEFAULT_FRIENDLY_NAMES = {
    "OMV": "OMV (Open Market Value)",
    "Vehicle_Age_Days": "Vehicle age (days)",
    "Horse_Power_kW": "Horsepower (kW)",
    "Previous_COE": "Previous COE",
    "COE_Left_Days": "COE left (days)",
    "Mileage_km": "Mileage (km)",
    "Engine_Capacity_cc": "Engine capacity (cc)",
    "Brand": "Brand",
    "Road_Tax_Payable": "Road tax payable",
    "Fuel_Type": "Fuel type",
}

# ---------------- Formatting helpers ----------------
def _days_to_years_months(days: float) -> str:
    """
    Convert 'days' back into years and months using the same logic as frontend:
    days = (years * 12 + months) * 30
    """
    if days is None:
        return "0 months"
    try:
        total_months = int(round(float(days) / 30.0))
    except (TypeError, ValueError):
        return str(days)

    years = total_months // 12
    months = total_months % 12

    parts = []
    if years > 0:
        parts.append(f"{years} year{'s' if years != 1 else ''}")
    if months > 0 or not parts:
        parts.append(f"{months} month{'s' if months != 1 else ''}")

    return " ".join(parts)

def _format_currency(x: float, symbol: str = "S$") -> str:
    if x is None:
        return "N/A"
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return "N/A"
    return f"{symbol}{x:,.0f}"

def _parse_feature(raw: str) -> Tuple[str, str, Optional[str]]:
    """
    Return (kind, base, category).
    Handles names like 'num__OMV' and 'cat__Brand_Toyota'.
    Falls back to ('raw', raw, None) if no prefix.
    """
    if "__" not in raw:
        return "raw", raw, None
    prefix, rest = raw.split("__", 1)
    if prefix == "num":
        return "num", rest, None
    if prefix == "cat":
        if "_" in rest:
            base, category = rest.split("_", 1)
            return "cat", base, category
        return "cat", rest, None
    return "raw", rest, None

def _friendly_label(kind: str, base: str, category: Optional[str],
                    friendly_map: Dict[str, str]) -> str:
    label = friendly_map.get(base, base.replace("_", " ").title())
    return f"{label}: {category}" if (kind == "cat" and category) else label

def _describe_item(item: Dict[str, Any],
                   input_data: Dict[str, Any],
                   currency_symbol: str,
                   friendly_map: Dict[str, str]) -> str:
    label = _friendly_label(item["kind"], item["base"], item["category"], friendly_map)
    dir_word = "increased" if item["shap"] >= 0 else "reduced"
    amount = _format_currency(abs(float(item["shap"])), currency_symbol)

    note = ""
    if item["kind"] == "num":
        if item["base"] in input_data:
            raw_val = input_data[item["base"]]
            # special handling for age & COE in days
            if item["base"] in ("Vehicle_Age_Days", "COE_Left_Days"):
                pretty = _days_to_years_months(raw_val)
            else:
                pretty = raw_val
            note = f" (your value: {pretty})"
    elif item["kind"] == "cat" and item["base"] in input_data:
        user_val = input_data[item["base"]]
        if isinstance(user_val, str) and item.get("category") == user_val:
            note = f" (your value: {user_val})"

    return f"- **{label}**: {dir_word} the price by about **{amount}**{note}."

def _rank_shap(shap_rows: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    enriched = []
    for r in shap_rows:
        raw = r["Feature"]
        shap_val = float(r["SHAP"])
        kind, base, cat = _parse_feature(raw)
        enriched.append({
            "feature_raw": raw,
            "kind": kind,
            "base": base,
            "category": cat,
            "shap": shap_val,
            "abs_shap": abs(shap_val),
            "Prediction": r.get("Prediction"),
            "Base Value": r.get("Base Value"),
        })
    enriched.sort(key=lambda x: x["abs_shap"], reverse=True)
    return enriched[:top_k]

# ---------------- Public helpers  ----------------
def to_model_df(features) -> pd.DataFrame:
    """
    Build the exact same model input layout as your /predict route.
    Keep this in sync with app.py’s predict builder.
    """
    return pd.DataFrame({
        "Brand": [features.brand],
        "Vehicle_Age_Days": [features.vehicle_age_days],
        "Mileage_km": [features.mileage],
        "Engine_Capacity_cc": [features.engine_cc],
        "Fuel_Type": [features.fuel_type],
        "OMV": [features.omv],
        "COE_Left_Days": [features.coe_left],
        "Horse_Power_kW": [features.horse_power],
        "Previous_COE": [features.previous_coe],
        "Road_Tax_Payable": [features.road_tax],
    })

def compute_shap_rows(model, X: pd.DataFrame, prediction: float) -> List[Dict[str, Any]]:
    """
    Return a list of {Feature, SHAP, Base Value, Prediction} for one row.

    Strategy:
    1) If model is a Pipeline with 'preprocessor' and 'regressor' (XGBRegressor),
       run SHAP on the **transformed features** with TreeExplainer (fast & accurate).
       Feature names come from preprocessor.get_feature_names_out(), e.g.:
         - 'num__OMV'
         - 'cat__Brand_Toyota'
    2) Otherwise, fall back to model-agnostic permutation explainer over the original X.
    """
    if shap is None:
        raise RuntimeError("shap is not installed. Please `pip install shap`.")

    # ---- Try fast path: Pipeline(preprocessor -> regressor) with TreeExplainer ----
    try:
        is_pipe = hasattr(model, "named_steps")
        if is_pipe and "preprocessor" in model.named_steps and "regressor" in model.named_steps:
            pre = model.named_steps["preprocessor"]
            reg = model.named_steps["regressor"]

            # transform features as the regressor sees them
            X_trans = pre.transform(X)

            # get aligned feature names from the ColumnTransformer
            try:
                feat_names = pre.get_feature_names_out()
            except Exception:
                # fallback if older sklearn
                feat_names = np.array([f"f{i}" for i in range(X_trans.shape[1])])
            feat_names = list(map(str, list(feat_names)))

            # TreeExplainer for XGBoost
            # (interventional is usually best for tabular; default also works)
            explainer = shap.TreeExplainer(reg)
            # Prefer the modern API returning an Explanation
            try:
                exp = explainer(X_trans)
                values = exp.values[0]
                base_value = float(exp.base_values[0]) if np.ndim(exp.base_values) > 0 else float(exp.base_values)
            except Exception:
                # legacy path
                values = explainer.shap_values(X_trans)[0]
                ev = getattr(explainer, "expected_value", 0.0)
                base_value = float(ev[0]) if np.ndim(ev) > 0 else float(ev)

            rows = []
            for fname, shap_val in zip(feat_names, values):
                rows.append({
                    "Feature": fname,
                    "SHAP": float(shap_val),
                    "Base Value": float(base_value),
                    "Prediction": float(prediction),
                })
            return rows

    except Exception as fast_err:
        # fall through to permutation explainer
        # (you can log fast_err if you want)
        pass

    # ---- Fallback: model-agnostic permutation explainer over original X ----
    def predict_fn(data_array):
        # SHAP feeds numpy arrays -> wrap back to DataFrame with same columns
        df = pd.DataFrame(data_array, columns=X.columns)
        return model.predict(df)

    explainer = shap.Explainer(predict_fn, X, algorithm="permutation")
    exp = explainer(X)

    values = exp.values[0]
    base_value = float(exp.base_values[0]) if np.ndim(exp.base_values) > 0 else float(exp.base_values)
    feature_names = list(exp.feature_names) if getattr(exp, "feature_names", None) else list(X.columns)

    rows = []
    for fname, shap_val in zip(feature_names, values):
        rows.append({
            "Feature": fname,
            "SHAP": float(shap_val),
            "Base Value": float(base_value),
            "Prediction": float(prediction),
        })
    return rows

def build_price_explanation_markdown(
    input_data: Dict[str, Any],
    shap_rows: List[Dict[str, Any]],
    *,
    currency_symbol: str = "S$",
    top_k: int = 6,
    friendly_names: Optional[Dict[str, str]] = None
) -> str:
    """Return a clean Markdown explanation for end users."""
    friendly_map = {**DEFAULT_FRIENDLY_NAMES, **(friendly_names or {})}
    if not shap_rows:
        return "We couldn't compute an explanation for this prediction."

    pred = float(shap_rows[0].get("Prediction", float("nan")))
    base = float(shap_rows[0].get("Base Value", float("nan")))
    ranked = _rank_shap(shap_rows, top_k=top_k)

    bullets = [_describe_item(it, input_data, currency_symbol, friendly_map) for it in ranked]
    positives = [it for it in ranked if it["shap"] > 0]
    negatives = [it for it in ranked if it["shap"] < 0]

    def _sumline(part: List[Dict[str, Any]]) -> str:
        if not part:
            return ""
        labels = [_friendly_label(p["kind"], p["base"], p["category"], friendly_map) for p in part[:3]]
        return ", ".join(labels)

    pos_txt = _sumline(positives)
    neg_txt = _sumline(negatives)

    lines = [
        f"**Predicted Price:** {_format_currency(pred, currency_symbol)}",
        "",
        f"**Base Price (average market estimate):** {_format_currency(base, currency_symbol)}",
        "",
        "Here’s what influenced your price the most:",
        *bullets
    ]
    if pos_txt or neg_txt:
        summary = "In summary, the price was"
        if pos_txt:
            summary += f" higher mainly due to {pos_txt}"
        if neg_txt:
            summary += f" but lower mainly due to {neg_txt}"
        lines += ["", summary + "."]

    return "\n".join(lines)

def build_drivers_for_ui(shap_rows: List[Dict[str, Any]], top_k: int = 6) -> List[Dict[str, Any]]:
    """Compact ‘chips’ style drivers for your frontend."""
    ranked = _rank_shap(shap_rows, top_k=top_k)
    return [{
        "feature": _friendly_label(d["kind"], d["base"], d["category"], DEFAULT_FRIENDLY_NAMES),
        "raw_feature": d["feature_raw"],
        "direction": "up" if d["shap"] >= 0 else "down",
        "impact_value": float(d["shap"])
    } for d in ranked]
