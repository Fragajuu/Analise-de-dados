import requests
import pandas as pd
import numpy as np
from io import StringIO
from datetime import datetime
import math

# ---------------- INITIAL CONFIGURATION ----------------
MAP_KEY = "map-key"
SATELLITES = ["MODIS_NRT", "VIIRS_NOAA20_NRT", "VIIRS_SUOMI_NPP_NRT"]
TIMEOUT = 30  # seconds for requests

# ---------------- HELPER FUNCTIONS ----------------
def generate_bbox(lat, lon, radius_km):
    delta_lat = radius_km / 111
    cos_lat = math.cos(math.radians(lat)) if abs(lat) < 89.9 else 0.0001
    delta_lon = radius_km / (111 * cos_lat)
    return f"{lon - delta_lon},{lat - delta_lat},{lon + delta_lon},{lat + delta_lat}"

def haversine_np(lat0, lon0, lats, lons):
    R = 6371.0
    lat0_rad = np.radians(lat0)
    lon0_rad = np.radians(lon0)
    lats_rad = np.radians(lats.astype(float))
    lons_rad = np.radians(lons.astype(float))
    dlat = lats_rad - lat0_rad
    dlon = lons_rad - lon0_rad
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat0_rad) * np.cos(lats_rad) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# ---------------- MAIN FUNCTION ----------------
def check_fires(lat, lon, sat_list=SATELLITES, radius_km=200, days=7):
    dfs = []

    # 1) Data collection
    for sat in sat_list:
        bbox = generate_bbox(lat, lon, radius_km)
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{sat}/{bbox}/{days}"
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            df = pd.read_csv(StringIO(response.text))
            if df.empty:
                continue
            df['satellite'] = sat
            dfs.append(df)
        except Exception as e:
            print(f"❌ Error accessing {sat}: {e}")
            continue

    if not dfs:
        print("✅ No fires detected (no data returned from satellites).")
        return pd.DataFrame()

    # 2) Process data
    df = pd.concat(dfs, ignore_index=True)

    for col in ['latitude', 'longitude', 'frp', 'confidence', 'acq_time', 'acq_date']:
        if col not in df.columns:
            df[col] = np.nan

    df['frp'] = pd.to_numeric(df['frp'], errors='coerce').fillna(0)

    # Confidence as percentage
    mapping = {'low': 30, 'nominal': 60, 'high': 90}
    conf_raw = df['confidence'].astype(str).str.strip().str.lower()
    mask_map = conf_raw.isin(mapping.keys())
    confidence_pct = pd.Series(index=df.index, dtype=float)
    confidence_pct[mask_map] = conf_raw[mask_map].map(mapping)
    numeric_conf = pd.to_numeric(df['confidence'], errors='coerce')
    confidence_pct = confidence_pct.fillna(numeric_conf).clip(0, 100)
    confidence_pct = confidence_pct.fillna(0)

    df['confidence_percent'] = confidence_pct.apply(lambda x: f"{x:.0f}%")

    # Fire intensity
    df['intensity'] = np.select(
        [df['frp'] < 30, df['frp'] < 100],
        ['Low', 'Moderate'],
        default='High'
    )

    # Distance from reference point
    df['distance_km'] = haversine_np(lat, lon, df['latitude'], df['longitude'])

    # Convert acquisition time to HH:MM and rename acquisition date
    df['time'] = df['acq_time'].apply(lambda x: f"{int(x)//100:02d}:{int(x)%100:02d}" if not pd.isna(x) else "00:00")
    df['date'] = df['acq_date']

    # Filter reliable data
    df = df[confidence_pct >= 40].copy()

    if df.empty:
        print("✅ No reliable fires detected within the specified radius.")
        return pd.DataFrame()

    def classify_risk(conf):
        if conf >= 70:
            return "High"
        elif conf >= 50:
            return "Medium"
        else:
            return "Low"

    df['fire_risk'] = confidence_pct.apply(classify_risk)
    df = df.sort_values(by='distance_km').reset_index(drop=True)

    # ---------------- CENTERED TABLE ----------------
    columns = ['satellite', 'latitude', 'longitude', 'date', 'time', 
               'frp', 'intensity', 'confidence_percent', 'fire_risk', 'distance_km']

    widths = [max(df[col].astype(str).map(len).max(), len(col)) for col in columns]

    def center_text(val, width):
        return str(val).center(width)

    print(f"\n🔥 FIRE ALERT 🔥")
    print(f"Detected {len(df)} reliable fires within {radius_km} km of coordinates ({lat}, {lon}) over the last {days} days\n")

    # Header
    header = " | ".join([center_text(c, w) for c, w in zip(columns, widths)])
    divider = "-+-".join(['-'*w for w in widths])
    print(header)
    print(divider)

    # Rows
    for _, row in df.iterrows():
        print(" | ".join([center_text(row[col], w) for col, w in zip(columns, widths)]))

    return df

# ---------------- EXECUTION ----------------
if __name__ == "__main__":
    try:
        latitude = float(input("Enter latitude: "))
        longitude = float(input("Enter longitude: "))
        radius_km = float(input("Enter radius in km: "))
        days = int(input("Enter number of days to check: "))
    except ValueError:
        print("❌ Invalid input. Please enter valid numbers.")
        exit()

    print(f"\n🔍 Checking for fires near ({latitude}, {longitude}) on {datetime.now().date()} within {radius_km} km over the last {days} days...")
    check_fires(latitude, longitude, radius_km=radius_km, days=days)
