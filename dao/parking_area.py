from typing import Any, Optional

from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class ParkingAreaDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_parking_area(self, new_parking_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            INSERT INTO parking_area(name, capacity, geom, created_at)
            VALUES (%(name)s, %(capacity)s, ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326), DATE_TRUNC('second', NOW()))
            RETURNING parking_area_id, name, capacity, ST_AsGeoJSON(geom)::json AS geom, created_at"""

            params = dict(new_parking_data)
            params["geom"] = json.dumps(params["geom"])

            cur.execute(query, params)
            result = dict(cur.fetchone()) #type: ignore
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_parking_areas(self, limit:int, offset: int, name:Optional[str]=None, bbox: Optional[str]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if bbox is not None:
                min_lon, min_lat, max_lon, max_lat = [float(val.strip()) for val in bbox.split(",")]

                where_conditions.append("ST_Intersects(geom, ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326))")
                params.update({
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat
                })

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM parking_area
            {full_sql}"""  
                    
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
                    
            query = f"""
            SELECT parking_area_id, name, capacity, created_at
            FROM parking_area
            {full_sql}
            ORDER BY parking_area_id
            LIMIT %(limit)s OFFSET %(offset)s"""
        
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]

            if results is None:
                return None #type: ignore
            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_parking_by_id(self, parking_area_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            params: dict[str, Any] = {"parking_area_id": parking_area_id}

            query = """
            SELECT parking_area_id, name, capacity, 
                        ST_AsGeoJSON(geom)::json AS geom, created_at
                        FROM parking_area
                        WHERE parking_area_id = %(parking_area_id)s"""
                        
            cur.execute(query, params)
            result = cur.fetchone()
            return dict(result) if result is not None else None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_parking_area(self, parking_area_id: int, new_parking_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            fields = []
            params = dict(new_parking_data)
            for field in new_parking_data.keys():
                if field == "geom":
                    fields.append("geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326)")
                    params["geom"] = json.dumps(new_parking_data["geom"])
                else:
                    fields.append(f"{field} = %({field})s")
            set_sql = ", ".join(fields)
            params["parking_area_id"] = parking_area_id
        
            query = f"""
            UPDATE parking_area
            SET {set_sql}
            WHERE parking_area_id = %(parking_area_id)s
            RETURNING parking_area_id, name, capacity, ST_AsGeoJSON(geom)::json AS geom, created_at"""
        
            cur.execute(query, params)
            result = cur.fetchone()

            conn.commit()
            return dict(result) if result is not None else None #type: ignore
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_parking_area(self, parking_area_id: int) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM parking_area
            WHERE parking_area_id = %s
            RETURNING parking_area_id"""
            cur.execute(query, (parking_area_id,))
        
            result = cur.fetchone()
            if result is None:
                return None  #type: ignore
            conn.commit()
            return dict(result)
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pool.putconn(conn)

    # ---------- HELPER FUNCTIONS -----------
    def parking_area_exists(self, parking_area_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM parking_area
            WHERE parking_area_id = %s"""

            cur.execute(query, (parking_area_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)