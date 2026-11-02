from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime
from fastapi import HTTPException

from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class RoadSegmentDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_road_segment(self, new_road_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            insert into road_segment(name, speed_limit_kph, is_oneway, direction, geom, created_at)
            values (%(name)s, %(speed_limit_kph)s, %(is_oneway)s, %(direction)s, ST_SetSRID(ST_GeomFromGeoJSON(%(geom)s), 4326), DATE_TRUNC('second', NOW()))
            returning road_id, name, speed_limit_kph, is_oneway, direction, ST_AsGeoJSON(geom)::json AS geom, created_at"""

            params = dict(new_road_data)
            params["geom"] = json.dumps(params["geom"])

            cur.execute(query, params)
            result = dict(cur.fetchone()) #type: ignore
            conn.commit()
            return result
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_road_segments(self, limit:int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None, bbox: Optional[dict]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if name:
                where_conditions.append("name ILIKE %(name)s")
                params["name"] = f"%{name.strip()}%"

            if min_speed_kph is not None:
                where_conditions.append("speed_limit_kph >= %(min_speed_kph)s")
                params["min_speed_kph"] = min_speed_kph
            if max_speed_kph is not None:
                where_conditions.append("speed_limit_kph <= %(max_speed_kph)s")
                params["max_speed_kph"] = max_speed_kph
            
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
            FROM road_segment
            {full_sql}"""  
            
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
            
            query = f"""
            SELECT road_id, name, speed_limit_kph, created_at
            FROM road_segment
            {full_sql}
            ORDER BY road_id
            LIMIT %(limit)s OFFSET %(offset)s"""

            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
                        
            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_road_by_id(self, road_id: int, bbox: Optional[dict[str, float]]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            params: dict[str, Any] = {"road_id": road_id}
            bbox_filter_sql = ""

            if bbox is not None:
                params.update({
                "min_lon": bbox["min_lon"],
                "min_lat": bbox["min_lat"],
                "max_lon": bbox["max_lon"],
                "max_lat": bbox["max_lat"]
                })
                bbox_filter_sql = """AND ST_Intersects(geom, ST_MakeEnvelope(%(min_lon)s, %(min_lat)s, %(max_lon)s, %(max_lat)s, 4326))"""

            query = f"""
            select road_id, name, speed_limit_kph, 
            ST_AsGeoJSON(geom)::json AS geom, created_at
            from road_segment
            where road_id = %(road_id)s
            {bbox_filter_sql}"""
            
            cur.execute(query, params)
            result = cur.fetchone()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_road_segment(self, road_id: int, new_road_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            set_sql = ", ".join([f"{field} = %({field})s" for field in new_road_data.keys()])
            params = dict(new_road_data)
            params["road_id"] = road_id

            query = f"""
            update road_segment
            set {set_sql}
            where road_id = %(road_id)s
            returning road_id, name, speed_limit_kph, ST_AsGeoJSON(geom)::json AS geom, created_at"""

            cur.execute(query, params)
            result = cur.fetchone()

            conn.commit()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_road_segment(self, road_id: int) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM road_segment
            WHERE road_id = %s
            RETURNING road_id"""
            cur.execute(query, (road_id,))
        
            result = cur.fetchone()
            if result is None:
                return None  #type: ignore
            conn.commit()
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_road_geojson(self, limit: int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if name:
                where_conditions.append("name ILIKE %(name)s")
                params["name"] = f"%{name.strip()}%"

            if min_speed_kph is not None:
                where_conditions.append("speed_limit_kph >= %(min_speed_kph)s")
                params["min_speed_kph"] = min_speed_kph
            if max_speed_kph is not None:
                where_conditions.append("speed_limit_kph <= %(max_speed_kph)s")
                params["max_speed_kph"] = max_speed_kph
            
            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM road_segment
            {full_sql}"""  
                        
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore

            query = f"""
            SELECT road_id, name, speed_limit_kph, is_oneway, direction, ST_AsGeoJSON(geom)::json as geometry
            FROM road_segment
            {full_sql}
            ORDER BY road_id
            LIMIT %(limit)s OFFSET %(offset)s"""
            
            cur.execute(query, params)
            results = cur.fetchall()

            features = []
            for row in results:
                result_row = dict(row)
                geometry = result_row.pop("geometry")
                feature = {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": result_row
                }
                features.append(feature)

                        
            return {"type": "FeatureCollection", "count": result, "limit": limit, "offset": offset, "features": features}
        finally:
            cur.close()
            self.pool.putconn(conn)