from datetime import datetime
from typing import Any, Optional
from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class TripDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_trip(self, new_trip_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)    
            query = """
            insert into trip(vehicle_id, start_ts, end_ts, start_geom, end_geom, distance_km)
            values (%(vehicle_id)s, %(start_ts)s, %(end_ts)s, ST_SetSRID(ST_GeomFromGeoJSON(%(start_geom)s), 4326), ST_SetSRID(ST_GeomFromGeoJSON(%(end_geom)s), 4326), %(distance_km)s)
            returning trip_id, vehicle_id, start_ts, end_ts, ST_AsGeoJSON(start_geom)::json AS start_geom, ST_AsGeoJSON(end_geom)::json AS end_geom, distance_km""" 
            
            params = dict(new_trip_data)
            if "start_geom" in params:
                params["start_geom"] = json.dumps(params["start_geom"]) 
            if "end_geom" in params:
                params["end_geom"] = json.dumps(params["end_geom"]) 
            
            cur.execute(query, params)
            result = dict(cur.fetchone()) #type: ignore
            conn.commit()
            return result
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_all_trips(self, limit: int, offset: int, from_ts: datetime, to_ts: datetime, vehicle_id: Optional[int]=None):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset} 
            if vehicle_id is not None:
                where_conditions.append("vehicle_id = %(vehicle_id)s")
                params["vehicle_id"] = vehicle_id
            if from_ts is not None:
                where_conditions.append("start_ts >= %(from_ts)s")
                params["from_ts"] = from_ts
            if to_ts is not None:
                where_conditions.append("end_ts <= %(to_ts)s")
                params["to_ts"] = to_ts

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM trip
            {full_sql}"""  
                            
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
                    
            query = f"""
            SELECT trip_id, vehicle_id, start_ts, end_ts, distance_km
            FROM trip
            {full_sql}
            ORDER BY trip_id
            LIMIT %(limit)s OFFSET %(offset)s"""
        
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
                                
            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_trip_by_id(self, trip_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            params: dict[str, Any] = {"trip_id": trip_id}
            
            query = """
            select trip_id, vehicle_id, start_ts, end_ts,
            ST_AsGeoJSON(start_geom)::json AS start_geom, 
            ST_AsGeoJSON(end_geom)::json AS end_geom, distance_km
            from trip
            where trip_id = %(trip_id)s"""
                        
            cur.execute(query, params)
            result = cur.fetchone()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_trip(self, trip_id: int, new_trip_data: dict[str, Any]):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            set_sql = ", ".join([f"{field} = %({field})s" for field in new_trip_data.keys()])
            params = dict(new_trip_data)
            params["trip_id"] = trip_id

            query = f"""
            update trip
            set {set_sql}
            where trip_id = %(trip_id)s
            returning trip_id, vehicle_id, start_ts, end_ts, ST_AsGeoJSON(start_geom)::json AS start_geom, ST_AsGeoJSON(end_geom)::json AS end_geom, distance_km"""

            cur.execute(query, params)
            result = cur.fetchone()

            conn.commit()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_trip(self, trip_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM trip
            WHERE trip_id = %s
            RETURNING trip_id"""
            cur.execute(query, (trip_id,))
            result = cur.fetchone()
            if result is None:
                return None  #type: ignore
            conn.commit()
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_trips_by_vehicle(self, vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}
        
            if vehicle_id:
                where_conditions.append("vehicle_id = %(vehicle_id)s")
                params["vehicle_id"] = vehicle_id
        
            if from_ts is not None:
                where_conditions.append("start_ts >= %(from_ts)s")
                params["from_ts"] = from_ts
            if to_ts is not None:
                where_conditions.append("end_ts <= %(to_ts)s")
                params["to_ts"] = to_ts
                    
            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM trip
            {full_sql}"""  
                                
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
        
            query = f"""
            SELECT trip_id, start_ts, end_ts, distance_km
            FROM trip
            {full_sql}
            ORDER BY trip_id
            LIMIT %(limit)s OFFSET %(offset)s"""
                    
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            
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