import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_values
import transform
import numpy as np

# Order matters here because of Foreign Key.
# Parent tables (like vehicle_kind) must be populated before child tables (like trip).
load_order: list[str] = [
    'vehicle_kind',
    'fuel_type',
    'vehicle_status',
    'vehicle_type',
    'parking_area',
    'driver',
    'vehicle',
    'road_segment',
    'location_ping',
    'vehicle_assignment',
    'trip'
]

# Maps which tables have spatial data and the exact names of their PostGIS geometry columns
geometry_columns: dict[str, list[str]] = {
    'location_ping': ['geom'],
    'parking_area': ['geom'],
    'road_segment': ['geom'],
    'trip': ['start_geom', 'end_geom']
}

# Pulls DB credentials from environment variables so passwords aren't hardcoded
def get_connection():
    """ Builds a psycopg2 connection from environment variables of the database
    Args:
        No arguments
    Returns:
        an live psycopg2 connection to the database
    """
    env_path = Path(__file__).resolve().parents[1] / '.env'
    load_dotenv(env_path) 

    return psycopg2.connect(
        user = os.environ['PGUSER'],
        password = os.environ['PGPASSWORD'],
        host = os.environ.get('PGHOST', 'localhost'),
        port = os.environ.get('PGPORT', '5432'),
        database = os.environ['PGDATABASE']
    )

def table_row_count(conn, table: str) -> int:
    """
    Args:
        conn: the connection to the database
        table (str): a selected table
    Returns:
        a singular number of the rows that are currently in the given table
    """
    with conn.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table}";')
        return cur.fetchone()[0]

# Wipes all table rows, resets auto-increment primary keys to 1, and CASCADE handles dependent FK references
def truncate_table(conn, table: str) -> None:
    with conn.cursor() as cur:
        cur.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')

# Inserts a dataframe into Postgres. Uses a staging table for geometry columns 
# so we don't spam thousands of UPDATE queries over the network connection.
def insert_dataframe(conn, table: str, df: pd.DataFrame, geom_cols: list[str] | None = None) -> int:
    if df.empty:
        return 0

    geom_cols = [c for c in (geom_cols or []) if c in df.columns]

    # Simple case: no geometry columns, just do a normal bulk insert directly
    if not geom_cols:
        return simple_insert(conn, table, df)

    # Complex case: has geometry, then use a staging table
    return insert_with_geom(conn, table, df, geom_cols)

# helper function
def simple_insert(conn, table:str, df:pd.DataFrame) -> int:
    # 1. Bulk insert a dataframe with no geometry columns using execute_variables
    cols = list(df.columns)
    col_list = ", ".join(f'"{c}"' for c in cols)
    temp = "(" + ", ".join(["%s"] * len(cols)) + ")"

    # converts every value to a plain python type psycopg2 can bind
    # rows = [tuple(None if pd.isna(v) else v for v in row) for row in df.itertuples(index=False, name=None)]
    rows = [
        tuple(
            None if pd.isna(v)
            else v.item() if isinstance(v, np.generic) # converts a NumPy scalar such as numpy.int64 into a native Python value such as int, which psycopg2 can adapt.
            else v
            for v in row
        )
        for row in df.itertuples(index=False, name=None)
    ]

    with conn.cursor() as cur:
        execute_values(cur, f'INSERT INTO "{table}" ({col_list}) VALUES %s', rows, template=temp, page_size=10000)

    return len(rows)

# helper function
# Note: the geometry data is stored as EWKB hex strings in the transformed dataframes,
# so we need to convert them to PostGIS geometry in the SQL query.
# However we don't want to spam thousands of UPDATE queries over the network connection,
# so we use a staging table for each table with geometry columns.
# Basically we create a temporary staging table with all columns as TEXT, bulk load the raw values into it,
# and then move everything from the staging table to the target table in one single SQL query on
def insert_with_geom(conn, table:str, df:pd.DataFrame, geom_cols: list[str]) -> int:
    # Insert via a staging table so ST_GeomFromEWKB runs in one server-side query
    staging_table = f"temp_staging_{table}"
    cols = list(df.columns)
    col_list = ", ".join(f'"{c}"' for c in cols)
    temp = "(" + ", ".join(["%s"] * len(cols)) + ")"

    try:
        # create staging table with all columns as TEXT (safe for hex strings, numbers, and nulls)
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{staging_table}";')
            staging_cols = ", ".join(f'"{c}" TEXT' for c in cols)
            cur.execute(f'CREATE TABLE "{staging_table}" ({staging_cols});')

            # bulk load raw values into staging
            rows = [
                tuple(
                    None if pd.isna(v)
                    else v.item() if isinstance(v, np.generic)
                    else v
                    for v in row
                )
                for row in df.itertuples(index=False, name=None)
            ]

            execute_values(
                cur,
                f'INSERT INTO "{staging_table}" ({col_list}) VALUES %s',
                rows,
                template=temp,
                page_size=10000,
            )

            select_exprs = []

            for c in cols:
                if c in geom_cols:
                    select_exprs.append(
                        f'CASE WHEN "{c}" IS NULL OR "{c}" = \'\' '
                        f'THEN NULL '
                        f'ELSE ST_GeomFromEWKB(decode("{c}", \'hex\')) END AS "{c}"'
                    )
                else:
                    select_exprs.append(
                        f'"{c}"::{pg_type_for(df[c])} AS "{c}"'
                    )
        
            target_columns = ", ".join(f'"{c}"' for c in cols)
            select_clause = ', '.join(select_exprs)
        
            # 3. Move everything from staging to the target table in one single SQL query on the server
            cur.execute(f"""
                INSERT INTO "{table}" ({target_columns})
                SELECT {select_clause}
                FROM "{staging_table}";
            """)
        
            return len(df)
    finally:
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS "{staging_table}";')

# maps a pandas dtpye to a Postgres type name for staging_table columns defs
def pg_type_for(series: pd.Series) -> str:
    dtype = series.dtype

    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    if pd.api.types.is_integer_dtype(dtype):
        return "bigint"
    if pd.api.types.is_float_dtype(dtype):
        return "double precision"
    if pd.api.types.is_datetime64_any_dtype(dtype):
        return "timestamp with time zone" if getattr(dtype, "tz", None) else "timestamp"

    return "text"

# Loops through load_order, clears target tables, and loads transformed dataframes
def load_all(transformed: dict[str, pd.DataFrame], conn, skip_existing: bool = True) -> dict[str, int]:
    report: dict[str, int] = {}

    for table in load_order:
        if table not in transformed:
            raise KeyError(f"Table '{table}' not present in transformed data")
        
        #getting table from transformed tables, and looking up if it has a geometry column
        df = transformed[table]
        geom_cols = geometry_columns.get(table)

        try:
            if skip_existing: # skips if there's already existing data
                existing = table_row_count(conn, table)
                if existing > 0:
                    print(f"Skipped {table}: already has {existing} rows")
                    report[table] = 0
                    continue
            else: # truncates the table if skip_existing is False
                truncate_table(conn, table)
                print(f"Truncated '{table}'")

            inserted = insert_dataframe(conn, table, df ,geom_cols)
            report[table] = inserted
            conn.commit()
            print(f"Loaded '{table}': {inserted} rows")
        except Exception:
            conn.rollback()
            raise
    return report

def main() -> None:
    print("Running extract + transform...")
    transformed = transform.transform_all()
    
    conn = get_connection()
    try:
        report = load_all(transformed, conn, skip_existing=False)
    finally:
        conn.close()

    # Summary report of inserted row counts
    print("\nLoad complete. Row counts:")
    for table, count in report.items():
        print(f"  {table:25s} {count}")

if __name__ == "__main__":
    main()