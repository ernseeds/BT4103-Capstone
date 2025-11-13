from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import joblib
from pathlib import Path
from contextlib import asynccontextmanager
import pandas as pd
import numpy as np
import datetime as dt
from decimal import Decimal
import math
from typing import List, Optional
from landscanner import landscanner_bq_df, coe_gcs_df, dashboard_gcs_df, ml_gcs_df, get_all_omv, prepare_derived, filter_by, order_by, order_by_multi
from price_prediction.explainer import to_model_df, compute_shap_rows, build_price_explanation_markdown, build_drivers_for_ui
import threading

# =============================== Paths / Constants ===============================

BACKEND_DIR = Path(__file__).resolve().parent
MODEL_PATH = BACKEND_DIR / "price_prediction" / "xgb_price_prediction_model.pkl"

# =============================== Schemas ===============================

class CarFeatures(BaseModel):
    brand: str
    year: int
    previous_coe: float
    omv: float
    coe_left: float
    mileage: float
    engine_cc: float
    horse_power: float
    road_tax: float
    fuel_type: str
    vehicle_age_days: int

class FilterQuery(BaseModel):
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    brand_in: Optional[List[str]] = None
    make_contains: Optional[str] = None
    website_in: Optional[List[str]] = None
    mileage_max: Optional[int] = None
    owners_max: Optional[int] = None
    age_min: Optional[float] = None
    age_max: Optional[float] = None
    coe_cat_in: Optional[List[str]] = None
    coe_months_min: Optional[int] = None
    coe_renewed: Optional[bool] = None
    five_year: Optional[bool] = None
    classic: Optional[bool] = None
    fuel_in: Optional[List[str]] = None
    trans_in: Optional[List[str]] = None
    engine_cc_min: Optional[int] = None
    engine_cc_max: Optional[int] = None
    hp_kw_min: Optional[float] = None
    hp_kw_max: Optional[float] = None
    sold: Optional[bool] = None
    freshness_max: Optional[int] = None
    sort_key: Optional[str] = None
    sort_keys: Optional[list[str]] = None
    # extras
    sort_by: Optional[str] = "Price"
    sort_dir: Optional[str] = "asc"  # "asc" | "desc"
    page: int = 1
    page_size: Optional[int] = None

# =============================== Utilities ===============================

def _to_py(v):
    """Convert pandas/numpy/decimal/datetime to JSON-safe Python."""
    try:
        # pandas missing
        if pd.isna(v):
            return None
    except Exception:
        pass
    # numpy scalars
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        # handle inf/nan
        return float(v) if np.isfinite(v) else None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    # decimals
    if isinstance(v, Decimal):
        return float(v)
    # datetimes/dates/times
    if isinstance(v, (pd.Timestamp, dt.datetime, dt.date)):
        if isinstance(v, (pd.Timestamp, dt.datetime)):
            if getattr(v, "tzinfo", None) is not None:
                v = v.astimezone(dt.timezone.utc).replace(tzinfo=None)
            v = v.date()
        return v.isoformat()  # "YYYY-MM-DD"

    if isinstance(v, dt.time):
        return v.strftime("%H:%M:%S")
    return v

def rows_from(df: pd.DataFrame) -> list[dict]:
    safe = df.replace([np.inf, -np.inf], np.nan).copy()

    # Convert datetime columns:
    def as_date_col(s: pd.Series) -> pd.Series:
        if pd.api.types.is_datetime64tz_dtype(s):
            return s.dt.tz_convert("UTC").dt.tz_localize(None).dt.date
        if pd.api.types.is_datetime64_dtype(s):
            return s.dt.date
        return s

    safe = safe.apply(as_date_col)

    # NaN/NaT -> None (JSON null), numpy scalars handled by jsonable_encoder
    safe = safe.astype(object).where(pd.notna(safe), None)
    return jsonable_encoder(safe.to_dict("records"))

# =============================== Cache / Ensurers ===============================

_cache_lock = threading.RLock()

def _ensure_dashboard_ready():
    """Lazy-load dashboard data and its derived frame once."""
    if getattr(app.state, "df_full", None) is not None:
        return app.state.df_full

    with _cache_lock:
        if getattr(app.state, "df_full", None) is None:
            df_full = dashboard_gcs_df()  # your existing loader
            if not isinstance(df_full, pd.DataFrame) or df_full.empty:
                raise HTTPException(status_code=503, detail="Dashboard dataset unavailable")
            app.state.df_full = df_full
    return app.state.df_full

def _get_all_omv():
    df_price_pred = _ensure_dashboard_ready()

    df_price_pred = df_price_pred[['Brand', 'Make', 'Registration_Date', 'OMV', 'Engine_Capacity_cc', 'Horse_Power_kW', 'Fuel_Type']]
    df_price_pred['Registration_Year'] = pd.to_datetime(df_price_pred['Registration_Date'], errors='coerce').dt.year
    df_price_pred['Prefix_Make'] = df_price_pred['Make'].str.split(' ').str[:3].str.join(' ')

    # 1. Define the aggregation rules
    aggregations = {
        'OMV': 'mean',
        'Engine_Capacity_cc': 'mean',
        'Horse_Power_kW': 'mean',
        'Fuel_Type': 'first'
    }

    # 2. Apply the groupby and aggregation
    df_grouped = df_price_pred.groupby(
        ['Brand', 'Registration_Year', 'Prefix_Make']
    ).agg(aggregations).reset_index()
    df_grouped['OMV'] = df_grouped['OMV'].round().astype(int)
    df_grouped['Brand'] = df_grouped['Brand'].str.upper()
    return df_grouped

def _ensure_omv_df():
    """Build and cache OMV aggregate (using _get_all_omv) on first use."""
    df = getattr(app.state, "omv_df", None)
    if isinstance(df, pd.DataFrame) and not df.empty:
        return df

    with _cache_lock:
        df = getattr(app.state, "omv_df", None)
        if not (isinstance(df, pd.DataFrame) and not df.empty):
            df = _get_all_omv()
            if not isinstance(df, pd.DataFrame) or df.empty:
                raise HTTPException(status_code=503, detail="OMV dataset unavailable")
            app.state.omv_df = df
    return app.state.omv_df

def _ensure_bq_dashboard_ready():
    """Lazy-load dashboard data and its derived frame once."""
    if getattr(app.state, "prepared_df", None) is not None:
        return app.state.prepared_df

    with _cache_lock:
        if getattr(app.state, "prepared_df", None) is None:
            df_full = landscanner_bq_df()
            if not isinstance(df_full, pd.DataFrame) or df_full.empty:
                raise HTTPException(status_code=503, detail="Dashboard dataset unavailable")
            app.state.prepared_df = prepare_derived(df_full)
    return app.state.prepared_df

# =============================== App / Middleware ===============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = None
    app.state.omv_df = None
    app.state.df_full = None
    app.state.prepared_df = None
    app.state.coe_df = None
    yield
    print("App shutting down...")

app = FastAPI(
    title="Car Price Prediction API",
    version="1.0.0",
    description="Predict resale car prices from features",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

# Compression for large responses
app.add_middleware(GZipMiddleware, minimum_size=1024)

# CORS (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://landscanner-ml.web.app",
        "https://landscanner-ml.firebase.com",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try loading model
try:
    model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None
except Exception:
    model = None

# =============================== Endpoints ===============================

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Car Price Prediction API"}

@app.post("/predict")
def predict_price(features: CarFeatures):

    ### Need to convert brand names from OMV dataset to match ML model ###
    
    try:
        # print(features)
        # turn into DataFrame with same columns as training
        data = {
            "Brand": [features.brand],
            "Vehicle_Age_Days": [features.vehicle_age_days],
            "Mileage_km": [features.mileage],
            "Engine_Capacity_cc": [features.engine_cc],
            "Fuel_Type": [features.fuel_type],
            "OMV": [features.omv],
            "COE_Left_Days": [features.coe_left],
            "Horse_Power_kW": [features.horse_power],
            "Previous_COE": [features.previous_coe],
            "Road_Tax_Payable": [features.road_tax]
        }
        df = pd.DataFrame(data)
        # print(df)
        # predict
        pred = model.predict(df)[0]

        return {
            "predicted_price": round(float(pred), 2),
            "currency": "SGD",  
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/predict_explain")
def predict_explain(features: CarFeatures):
    """
    Same input as /predict.
    Returns: predicted_price, currency, explanation_markdown, drivers[]
    """
    try:
        if model is None:
            raise RuntimeError("Model is not loaded.")

        # Use the same DataFrame layout as /predict
        X = to_model_df(features)  # matches your /predict columns exactly

        # Predict
        pred = float(model.predict(X)[0])
        rounded_pred = int(math.floor((pred + 50) / 100.0) * 100)

        # Compute SHAP rows for this single prediction
        shap_rows = compute_shap_rows(model, X, pred)

        # Build user-friendly explanation
        input_data = {
            "OMV": features.omv,
            "Vehicle_Age_Days": features.vehicle_age_days,
            "Horse_Power_kW": features.horse_power,
            "Previous_COE": features.previous_coe,
            "COE_Left_Days": features.coe_left,
            "Mileage_km": features.mileage,
            "Engine_Capacity_cc": features.engine_cc,
            "Brand": features.brand,
            "Road_Tax_Payable": features.road_tax,
            "Fuel_Type": features.fuel_type
        }
        explanation_md = build_price_explanation_markdown(
            input_data, shap_rows, currency_symbol="S$", top_k=6
        )
        drivers = build_drivers_for_ui(shap_rows, top_k=6)

        return {
            "predicted_price": rounded_pred,
            "currency": "SGD",
            "explanation_markdown": explanation_md,
            "drivers": drivers
        }

    except Exception as e:
        print(e)
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/get_model_year")
def get_model_year(brand: str):
    # Filter df by brand and year
    # print(app.state.omv_df[(app.state.omv_df['Brand'] == brand)])
    omv_df = _ensure_omv_df()
    filtered = omv_df[(omv_df['Brand'] == brand)]
    years = sorted(filtered['Registration_Year'].unique().tolist())
    return JSONResponse(content={"years": years})

@app.get("/available-makes")
def get_available_makes(brand: str = Query(...), year: int = Query(...)):
    # Filter df by brand and year
    # print(app.state.omv_df[(app.state.omv_df['Brand'] == brand)])
    omv_df = _ensure_omv_df()
    filtered = omv_df[(omv_df['Brand'] == brand) & (omv_df['Registration_Year'] == year)]
    makes = sorted(filtered['Prefix_Make'].unique().tolist())
    return JSONResponse(content={"makes": makes})

@app.get("/get-omv")
def get_omv(brand: str, year: int, make: str):
    omv_df = _ensure_omv_df()
    filtered = omv_df[
        (omv_df["Brand"] == brand) &
        (omv_df["Registration_Year"] == year) &
        (omv_df["Prefix_Make"] == make)
    ]

    if filtered.empty:
        # Return None for all fields if no match
        return {
            "omv": None,
            "engine_cc": None,
            "horse_power": None,
            "fuel_type": None
        }

    # Extract values safely
    row = filtered.iloc[0]
    omv = float(row["OMV"]) if row["OMV"] is not None else None
    engine_cc = float(row["Engine_Capacity_cc"]) if row["Engine_Capacity_cc"] is not None else None
    horse_power = int(row["Horse_Power_kW"]) if row["Horse_Power_kW"] is not None else None
    fuel_type = row["Fuel_Type"] if row["Fuel_Type"] is not None else None

    return {
        "omv": omv,
        "engine_cc": engine_cc,
        "horse_power": horse_power,
        "fuel_type": fuel_type
    }

@app.get("/fetch_coe_gcs")
def get_coe_gcs_df():
    try:
        # lazy-load on first call
        if getattr(app.state, "coe_df", None) is None:
            df = coe_gcs_df()
            if not isinstance(df, pd.DataFrame):
                raise RuntimeError("coe_gcs_df() did not return a DataFrame")
            app.state.coe_df = df
        else:
            df = app.state.coe_df

        rows = rows_from(df)
        return JSONResponse({"rows": rows})

    except Exception as e:
        # return a predictable shape so frontend can show error
        return JSONResponse(
            {"rows": [], "error": str(e)},
            status_code=500,
        )

@app.get("/fetch_downloaded_dashboard")
def get_downloaded_dashboard_df():
    # lazy-load dashboard data on first request
    df = _ensure_dashboard_ready()

    if not isinstance(df, pd.DataFrame):
        raise RuntimeError(f"get_df() returned {type(df)} instead of DataFrame")

    rows = rows_from(df)
    return JSONResponse({"rows": rows})

@app.post("/cars/search")
def filter_rows(q: FilterQuery):
    base = _ensure_bq_dashboard_ready()
    
    kwargs    = q.model_dump(exclude_none=True)
    sort_key  = kwargs.pop("sort_key", "price_asc")
    sort_keys = kwargs.pop("sort_keys", None)
    page      = max(1, kwargs.pop("page", 1))
    page_size = kwargs.pop("page_size", 20) or 20

    try:
        out = filter_by(base, **kwargs)
    except Exception as e:
        out = base 

    total = len(out)
    if sort_keys:
        sorted_df = order_by_multi(out, sort_keys)
    else:
        sorted_df = order_by(out, key=sort_key or "price_asc", limit=None, offset=0)

    start  = (page - 1) * page_size
    page_df = sorted_df.iloc[start:start + page_size]
    rows = rows_from(page_df)
    return {"total": total, "page": page, "page_size": page_size, "rows": rows}

@app.get('/get_brands', response_model=List[str])
def get_brands():
    """
    API endpoint to fetch the list of car brands.
    """
    omv_df = _ensure_omv_df()
    # omv_df["Brand"] = omv_df["Brand"].str.upper()
    CAR_BRANDS = sorted(omv_df["Brand"].unique().tolist())
    print(CAR_BRANDS)
    return CAR_BRANDS
