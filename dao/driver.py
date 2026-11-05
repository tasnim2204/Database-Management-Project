from datetime import datetime
from typing import Any, Optional
from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class DriverDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_driver(self, new_driver_data: dict[str, Any]):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)    
            query = """
            insert into driver(first_name, last_name, license_number, hired_at)
            values (%(first_name)s, %(last_name)s,%(license_number)s, %(hired_at)s)
            returning driver_id, first_name, last_name, license_number, hired_at""" 
            
            params = dict(new_driver_data)            
            cur.execute(query, params)
            result = dict(cur.fetchone()) #type: ignore
            conn.commit()
            return result
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_all_drivers(self, limit: int, offset: int, name: Optional[str]=None, license_number: Optional[str]=None):
        conn = self.pool.getconn()
        cur = conn.cursor(cursor_factory= DictCursor)
        try:
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if name is not None and name.strip():
                where_conditions.append("first_name ILIKE %(first_name)s OR last_name ILIKE %(last_name)s")
                params["first_name"] = f"%{name.strip()}%"
                params["last_name"] = f"%{name.strip()}%"

            if license_number is not None and license_number.strip():
                where_conditions.append("license_number ILIKE %(license_number)s")
                params["license_number"] = f"%{license_number.strip()}%"

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            count_query = f"""
            SELECT COUNT(*) AS result
            FROM driver
            {full_sql}"""  

            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
            
            query = f"""
            SELECT driver_id, first_name, last_name, license_number, hired_at
            FROM driver
            {full_sql}
            ORDER BY driver_id
            LIMIT %(limit)s OFFSET %(offset)s"""

            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            
            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_driver_by_id(self, driver_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT driver_id, first_name, last_name, license_number, hired_at
            FROM driver
            WHERE driver_id = %s"""

            cur.execute(query, (driver_id,))
            result = cur.fetchone() # type: ignore
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_driver(self, driver_id: int, new_driver_data: dict[str,Any]):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            set_sql = ", ".join([f"{field} = %({field})s" for field in new_driver_data.keys()])
            params = dict(new_driver_data)
            params["driver_id"] = driver_id

            query = f"""
            update driver
            set {set_sql}
            where driver_id = %(driver_id)s
            returning driver_id, first_name, last_name, license_number, hired_at"""

            cur.execute(query, params)
            result = cur.fetchone()

            conn.commit()
            return dict(result) if result is not None else None #type: ignore
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_driver(self, driver_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM driver
            WHERE driver_id = %s
            RETURNING driver_id"""
            cur.execute(query, (driver_id,))

            result = cur.fetchone()
            if result is None:
                return None  #type: ignore
            conn.commit()
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    # ---------- HELPER FUNCTIONS -----------
    def license_in_use(self, plate_number: str, driver_id: Optional[int] = None) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            if driver_id is None:
                query = """
                SELECT 1
                FROM driver
                WHERE TRIM(license_number) = %s"""
                cur.execute(query, (plate_number,))
            else:
                query = """
                SELECT 1
                FROM driver
                WHERE TRIM(license_number) = %s
                AND driver_id != %s"""
                cur.execute(query, (plate_number, driver_id,))

            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def has_assignments(self, driver_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            SELECT 1
            FROM vehicle_assignment
            WHERE driver_id = %s
            LIMIT 1"""
            cur.execute(query, (driver_id,))   
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)