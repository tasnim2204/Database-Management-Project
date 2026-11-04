from datetime import datetime
from typing import Any, Optional
from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class LocationPingDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_location_ping(self, new_ping_data: dict[str,Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)    
            query = """
            insert into location_ping(vehicle_id, ts, geom, speed_kph, heading_deg)
            values (%(vehicle_id)s, %(ts)s, ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326), %(speed_kph)s, %(heading_deg)s)
            returning ping_id, vehicle_id, ts, ST_AsGeoJSON(geom)::json AS geom, speed_kph, heading_deg""" 
            
            params = dict(new_ping_data)
            params["geom"] = json.dumps(params["geom"]) 
            
            cur.execute(query, params)
            result = dict(cur.fetchone()) #type: ignore
            conn.commit()
            return result
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_all_pings(self, limit: int, offset: int, vehicle_id: Optional[int]=None, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None, bbox: Optional[dict]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if vehicle_id is not None:
                where_conditions.append("vehicle_id = %(vehicle_id)s")
                params["vehicle_id"] = vehicle_id
            if from_ts is not None:
                where_conditions.append("ts >= %(from_ts)s")
                params["from_ts"] = from_ts
            if to_ts is not None:
                where_conditions.append("ts <= %(to_ts)s")
                params["to_ts"] = to_ts
        
            if bbox is not None:
                where_conditions.append("ST_Intersects(geom, ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326))")
                params.update({
                    "min_lon": bbox["min_lon"],
                    "min_lat": bbox["min_lat"],
                    "max_lon": bbox["max_lon"],
                    "max_lat": bbox["max_lat"]
                })

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM location_ping
            {full_sql}"""  
                    
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
                    
            query = f"""
            SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg
            FROM location_ping
            {full_sql}
            ORDER BY ping_id
            LIMIT %(limit)s OFFSET %(offset)s"""
        
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
                                
            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_ping_by_id(self, ping_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            params: dict[str, Any] = {"ping_id": ping_id}
            
            query = """
            select ping_id, vehicle_id, ts,
            ST_AsGeoJSON(geom)::json AS geom, speed_kph, heading_deg
            from location_ping
            where ping_id = %(ping_id)s"""
                        
            cur.execute(query, params)
            result = cur.fetchone()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_location_ping(self, ping_id: int, new_ping_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            set_sql = ", ".join([f"{field} = %({field})s" for field in new_ping_data.keys()])
            params = dict(new_ping_data)
            params["ping_id"] = ping_id

            query = f"""
            update location_ping
            set {set_sql}
            where ping_id = %(ping_id)s
            returning ping_id, vehicle_id, ts, ST_AsGeoJSON(geom)::json AS geom, speed_kph, heading_deg"""

            cur.execute(query, params)
            result = cur.fetchone()

            conn.commit()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_location_ping(self, ping_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM location_ping
            WHERE ping_id = %s
            RETURNING ping_id"""
            cur.execute(query, (ping_id,))
            result = cur.fetchone()
            if result is None:
                return None  #type: ignore
            conn.commit()
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_pings_by_vehicle(self, vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}
        
            if vehicle_id:
                where_conditions.append("vehicle_id = %(vehicle_id)s")
                params["vehicle_id"] = vehicle_id
        
            if from_ts is not None:
                where_conditions.append("ts >= %(from_ts)s")
                params["from_ts"] = from_ts
            if to_ts is not None:
                where_conditions.append("ts <= %(to_ts)s")
                params["to_ts"] = to_ts
                    
            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM location_ping
            {full_sql}"""  
                                
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
        
            query = f"""
            SELECT ping_id, vehicle_id, ts, 
            ST_AsGeoJSON(geom)::json as geom, speed_kph, heading_deg
            FROM location_ping
            {full_sql}
            ORDER BY ping_id
            LIMIT %(limit)s OFFSET %(offset)s"""
                    
            cur.execute(query, params)
            results = cur.fetchall()
            
            return {"vehicle_id": vehicle_id, "items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    # ---------- HELPER FUNCTIONS -----------
    def vehicle_exists(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM vehicle
            WHERE vehicle_id = %s"""

            cur.execute(query, (vehicle_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)