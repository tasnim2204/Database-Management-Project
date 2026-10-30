import extract
import pandas as pd
from pathlib import Path

# TODO: CONVERT THIS TO LOOK LIKE HOW MIGUEL DOCUMENTED HIS FILE

def to_timestamp_us(series):
    timestamps = pd.to_datetime(series, errors="raise")
    return timestamps.dt.as_unit("us", round_ok=False)

def transform_driver(df):
    df = df.copy()
    df["driver_id"] = pd.to_numeric(df["driver_id"], errors="raise").astype("Int64")
    df["hired_at"] = to_timestamp_us(df["hired_at"])
    for column in ["first_name", "last_name", "license_number"]:
        df[column] = to_string(df[column], errors="raise")
    return df

def transform_fuel_type(df):
    df = df.copy()
    df["fuel_type_id"] = pd.to_numeric(df["fuel_type_id"], errors="raise").astype("Int64")
    df["name"] = to_string(df["name"], errors="raise")
    return df

def transform_location_ping(df):
    df = df.copy()
    df["ping_id"] = pd.to_numeric(df["ping_id"], errors="raise").astype("Int64")
    df["vehicle_id"] = pd.to_numeric(df["vehicle_id"], errors="raise").astype("Int64")
    df["ts"] = to_timestamp_us(df["ts"])
    df["geom"] = to_ewkb_hex(df["geom"])
    df["speed_kph"] = pd.to_numeric(df["speed_kph"], errors="raise").astype("float64")
    df["heading_deg"] = pd.to_numeric(df["heading_deg"], errors="raise").astype("float64")

    return df

def transform_parking_area(df):
    df = df.copy()
    df["parking_area_id"] = pd.to_numeric(df["parking_area_id"], errors="raise").astype("Int64")
    df["name"] = to_string(df["name"], errors="raise")
    df["capacity"] = pd.to_numeric(df["capacity"], errors="raise").astype("Int64")
    df["geom"] = to_ewkb_hex(df["geom"])
    df["created_at"] = to_timestamp_us(df["created_at"])
    return df

def transform_road_segment(df):
    df = df.copy()
    df["road_id"] = pd.to_numeric(df["road_id"], errors="raise").astype("Int64")
    df["name"] = to_string(df["name"], errors="raise")
    df["speed_limit_kph"] = pd.to_numeric(df["speed_limit_kph"], errors="raise").astype("Int64")
    df["geom"] = to_ewkb_hex(df["geom"])
    df["created_at"] = to_timestamp_us(df["created_at"])
    df["is_oneway"] = to_boolean(df["is_oneway"], errors="raise")
    df["direction"] = to_string(df["direction"], errors="raise")
    return df

def transform_trip(df):
    df = df.copy()
    df["trip_id"] = pd.to_numeric(df["trip_id"], errors="raise").astype("Int64")
    df["vehicle_id"] = pd.to_numeric(df["vehicle_id"], errors="raise").astype("Int64")
    df["start_ts"] = to_timestamp_us(df["start_ts"])
    df["end_ts"] = to_timestamp_us(df["end_ts"])
    df["start_geom"] = to_ewkb_hex(df["start_geom"])
    df["end_geom"] = to_ewkb_hex(df["end_geom"])
    df["distance_km"] = pd.to_numeric(df["distance_km"], errors="raise").astype("float64")
    return df

def transform_vehicle(df):
    df = df.copy()
    df["vehicle_id"] = pd.to_numeric(df["vehicle_id"], errors="raise").astype("Int64")
    df["vehicle_type_id"] = pd.to_numeric(df["vehicle_type_id"], errors="raise").astype("Int64")
    df["vehicle_status_id"] = pd.to_numeric(df["vehicle_status_id"], errors="raise").astype("Int64")
    df["plate_number"] = to_string(df["plate_number"], errors="raise")
    df["make"] = to_string(df["make"], errors="raise")
    df["model"] = to_string(df["model"], errors="raise")
    df["year"] = pd.to_numeric(df["year"], errors="raise").astype("Int64")
    df["created_at"] = to_timestamp_us(df["created_at"])
    return df

def transform_vehicle_assignment(df):
    df = df.copy()
    df["assignment_id"] = pd.to_numeric(df["assignment_id"], errors="raise").astype("Int64")
    df["vehicle_id"] = pd.to_numeric(df["vehicle_id"], errors="raise").astype("Int64")
    df["driver_id"] = pd.to_numeric(df["driver_id"], errors="raise").astype("Int64")

    df["assigned_from"] = to_timestamp_us(df["assigned_from"])
    df["assigned_to"] = to_timestamp_us(df["assigned_to"])
    return df

def transform_vehicle_kind(df):
    df = df.copy()
    df["vehicle_kind_id"] = pd.to_numeric(df["vehicle_kind_id"], errors="raise").astype("Int64")
    df["name"] = to_string(df["name"], errors="raise")
    return df

def transform_vehicle_status(df):
    df = df.copy()
    df["vehicle_status_id"] = pd.to_numeric(df["vehicle_status_id"], errors="raise").astype("Int64")
    df["name"] = to_string(df["name"], errors="raise")
    return df

def transform_vehicle_type(df):
    df = df.copy()
    df["vehicle_type_id"] = pd.to_numeric(df["vehicle_type_id"], errors="raise").astype("Int64")
    df["vehicle_kind_id"] = pd.to_numeric(df["vehicle_kind_id"], errors="raise").astype("Int64")
    df["fuel_type_id"] = pd.to_numeric(df["fuel_type_id"], errors="raise").astype("Int64")
    df["emissions_rating"] = pd.to_numeric(df["emissions_rating"], errors="raise").astype("float64")
    df["created_at"] = to_timestamp_us(df["created_at"])
    return df

TRANSFORMS = {
    "driver": transform_driver,
    "fuel_type": transform_fuel_type,
    "location_ping": transform_location_ping,
    "parking_area": transform_parking_area,
    "road_segment": transform_road_segment,
    "trip": transform_trip,
    "vehicle": transform_vehicle,
    "vehicle_assignment": transform_vehicle_assignment,
    "vehicle_kind": transform_vehicle_kind,
    "vehicle_status": transform_vehicle_status,
    "vehicle_type": transform_vehicle_type,
}

def transform_all():
    """Extract and transform each supported Parquet table, keyed by table name."""
    parquet_folder = Path(__file__).resolve().parent / "phase1_official_dataset"
    transformed = {}

    for parquet_path in sorted(parquet_folder.glob("*.parquet")):
        table_name = parquet_path.stem
        if table_name not in TRANSFORMS:
            raise ValueError(f"No transform is defined for table '{table_name}'")
        dataframe = extract.extract(str(parquet_path))
        transformed[table_name] = TRANSFORMS[table_name](dataframe)

    return transformed

# Helper function
def to_string(series, errors="raise"):
    if series.isna().any():
        if errors == "raise":
            raise ValueError(f"Column '{series.name}' has {series.isna().sum()} null value(s)")
        elif errors == "coerce":
            return series.astype("string")  # keeps nulls as <NA>
    return series.astype(str)

# Helper function
def to_ewkb_hex(series):
    def convert(value):
        if pd.isna(value):
            raise ValueError(f"Column '{series.name}' contains a null geometry")

        if isinstance(value, (bytes, bytearray, memoryview)):
            return bytes(value).hex()

        if isinstance(value, str):
            hex_value = value.strip()
            try:
                bytes.fromhex(hex_value)
            except ValueError as error:
                raise ValueError(
                    f"Column '{series.name}' contains a value that is not valid EWKB hex"
                ) from error
            return hex_value

        raise TypeError(
            f"Column '{series.name}' contains unsupported geometry type "
            f"{type(value).__name__}"
        )

    return series.map(convert)


# Helper function
def to_boolean(series, errors="raise"):
    if errors not in ("raise", "coerce"):
        raise ValueError("errors must be 'raise' or 'coerce'")

    def convert(value):
        if pd.isna(value):
            if errors == "raise":
                raise ValueError(f"Column '{series.name}' contains a null value")
            return pd.NA

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1"):
                return True
            if normalized in ("false", "0"):
                return False

        if errors == "raise":
            raise ValueError(
                f"Column '{series.name}' contains an invalid boolean value: {value!r}"
            )
        return pd.NA

    return series.map(convert).astype("boolean")


if __name__ == "__main__":
    transformed_tables = transform_all()
    print("Transformed table shapes:", {
        name: dataframe.shape for name, dataframe in transformed_tables.items()
    })