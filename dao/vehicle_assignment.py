from datetime import datetime
from typing import Any, Optional
from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor
import json

class VehicleAssignmentDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_vehicle_assignment(self, new_assginment_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)    
            query = """
            INSERT INTO vehicle_assignment(vehicle_id, driver_id, assigned_from, assigned_to)
            VALUES (%(vehicle_id)s, %(driver_id)s,%(assigned_from)s, %(assigned_to)s)
            RETURNING assignment_id, vehicle_id, driver_id, assigned_from, assigned_to""" 
            
            params = dict(new_assginment_data)            
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

    def get_vehicle_assignments(self, limit:int, offset: int, vehicle_id: Optional[int]=None, driver_id: Optional[int]=None, active: Optional[bool]=None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}

            if vehicle_id is not None:
                where_conditions.append("vehicle_id = %(vehicle_id)s")
                params["vehicle_id"] = vehicle_id
            if driver_id is not None:
                where_conditions.append("driver_id = %(driver_id)s")
                params["driver_id"] = driver_id

            if active is not None:
                if active == True:
                    where_conditions.append("assigned_to IS NULL")
                if active == False:
                    where_conditions.append("assigned_to IS NOT NULL")

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                    
            count_query = f"""
            SELECT COUNT(*) AS result
            FROM vehicle_assignment
            {full_sql}"""  
                            
            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
                    
            query = f"""
            SELECT assignment_id, vehicle_id, driver_id, assigned_from, assigned_to
            FROM vehicle_assignment
            {full_sql}
            ORDER BY assignment_id
            LIMIT %(limit)s OFFSET %(offset)s"""
        
            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]
            if result is None:
                return None #type: ignore

            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_assignment_by_id(self, assignment_id:int) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT assignment_id, vehicle_id, driver_id, assigned_from, assigned_to
            FROM vehicle_assignment
            WHERE assignment_id = %s"""

            cur.execute(query, (assignment_id,))
            result = cur.fetchone()
            if result is None:
                return None #type: ignore
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_vehicle_assignment(self, assignment_id: int, new_assignment_data: dict[str, Any]):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            set_sql = ", ".join([f"{field} = %({field})s" for field in new_assignment_data.keys()])
            params = dict(new_assignment_data)
            params["assignment_id"] = assignment_id

            query = f"""
            update vehicle_assignment
            set {set_sql}
            where assignment_id = %(assignment_id)s
            returning assignment_id, vehicle_id, driver_id, assigned_from, assigned_to"""

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

    def delete_vehicle_assignment(self, assignment_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM vehicle_assignment
            WHERE assignment_id = %s
            RETURNING assignment_id"""
            cur.execute(query, (assignment_id,))
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

    def driver_exists(self, driver_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM driver
            WHERE driver_id = %s"""

            cur.execute(query, (driver_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def assignment_exists(self, assignment_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM vehicle_assignment
            WHERE assignment_id = %s"""

            cur.execute(query, (assignment_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)