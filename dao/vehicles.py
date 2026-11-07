from typing import Any, Optional
from psycopg2.pool import SimpleConnectionPool
from config.dbconfig import POOL_CONFIG, PG_DB_CONFIG
from psycopg2.extras import DictCursor

class VehicleDAO:
    def __init__(self) -> None:
        #Connection pools serve to create several connections to the DB
        #This makes the app faster because creating connections is
        #expensive. With the pool, you recycle existing connections
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                         POOL_CONFIG["maxconn"],
                                         **PG_DB_CONFIG)

    def create_vehicle(self, new_vehicle_data: dict[str, Any]) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            
            query = """
            INSERT INTO vehicle(vehicle_type_id, vehicle_status_id, plate_number, make, model, year, created_at)
            VALUES (%(vehicle_type_id)s, %(vehicle_status_id)s, %(plate_number)s, %(make)s, %(model)s, %(year)s, DATE_TRUNC('second', NOW()))
            RETURNING vehicle_id, vehicle_type_id, vehicle_status_id, plate_number, make, model, year, created_at"""

            payload = dict(new_vehicle_data)
            cur.execute(query, payload)
            row = cur.fetchone()
            conn.commit()
            return dict(row) #type: ignore
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_all_vehicles(self, limit: int, offset: int, status: Optional[str] = None, plate_number: Optional[str] = None) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory= DictCursor)
            where_conditions = []
            params: dict[str, Any] = {"limit": limit, "offset": offset}
            
            if plate_number is not None and plate_number.strip():
                where_conditions.append("plate_number ILIKE %(plate_number)s")
                params["plate_number"] = f"%{plate_number.strip()}%"
            
            if status is not None and str(status).strip() != "":
                status_raw = str(status).strip()
                if status_raw.isdigit():
                    params["status_id"] = int(status_raw)
                    where_conditions.append("vehicle_status_id = %(vehicle_status_id)s")
                else:
                    params["status_name"] = status_raw.lower()
                    where_conditions.append("vehicle_status_id = (SELECT vehicle_status_id FROM vehicle_status  WHERE LOWER(name) = %(status_name)s)")

            full_sql = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""

            count_query = f"""
            SELECT COUNT(*) AS result
            FROM vehicle
            {full_sql}"""  

            cur.execute(count_query, params)
            result = cur.fetchone()['result'] #type: ignore
            
            query = f"""
            SELECT vehicle_id, plate_number, make, model, year, vehicle_type_id, vehicle_status_id, created_at
            FROM vehicle
            {full_sql}
            ORDER BY vehicle_id
            LIMIT %(limit)s OFFSET %(offset)s"""

            cur.execute(query, params)
            results = [dict(row) for row in cur.fetchall()]

            return {"items": results, "limit": limit, "offset": offset, "count": result}
        finally:
            cur.close()
            self.pool.putconn(conn)

    def get_vehicle_by_id(self, vehicle_id:int) -> dict:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT vehicle_id, vehicle_type_id, vehicle_status_id, plate_number, make, model, year, created_at
            FROM vehicle
            WHERE vehicle_id = %s"""

            cur.execute(query, (vehicle_id,))
            result = cur.fetchone()
            if result is None:
                return None #type: ignore
            return dict(result)
        finally:
            cur.close()
            self.pool.putconn(conn)

    def update_vehicle(self, vehicle_id: int, new_vehicle_data: dict[str, Any]) -> dict[str, Any]:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            set_sql =  ", ".join([f"{field} = %({field})s" for field in new_vehicle_data.keys()])
            params = dict(new_vehicle_data)
            params["vehicle_id"] = vehicle_id

            query= f"""
            UPDATE VEHICLE
            SET {set_sql}
            WHERE vehicle_id = %(vehicle_id)s
            RETURNING vehicle_id, vehicle_type_id, vehicle_status_id, plate_number, make, model, year, created_at"""
            cur.execute(query, params)

            row = cur.fetchone()
            
            conn.commit()
            return dict(row) if row is not None else None # type: ignore
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            self.pool.putconn(conn)

    def delete_vehicle(self, vehicle_id: int) -> dict[str, Any]:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            DELETE FROM vehicle
            WHERE vehicle_id = %s
            RETURNING vehicle_id"""
            cur.execute(query, (vehicle_id,))

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

    def get_vehicle_current_location(self, vehicle_id: int):
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            SELECT v.vehicle_id, v.plate_number, 
            vs.name AS status, 
            vk.name AS vehicle_kind,
            ft.name AS fuel_type,
            vt.emissions_rating,
            lp.ts AS last_ts,
            ST_AsGeoJSON(lp.geom)::json AS last_geom,
            lp.speed_kph, lp.heading_deg
            FROM vehicle AS v JOIN vehicle_status AS vs 
                ON vs.vehicle_status_id = v.vehicle_status_id
            JOIN vehicle_type AS vt 
                ON vt.vehicle_type_id = v.vehicle_type_id
            LEFT JOIN vehicle_kind AS vk 
                ON vk.vehicle_kind_id = vt.vehicle_kind_id
            LEFT JOIN fuel_type AS ft 
                ON ft.fuel_type_id = vt.fuel_type_id
            LEFT JOIN location_ping AS lp
                ON lp.ping_id = (SELECT p.ping_id
                                FROM location_ping AS p
                                WHERE p.vehicle_id = v.vehicle_id
                                ORDER BY p.ts DESC
                                LIMIT 1)
            WHERE v.vehicle_id = %s"""

            cur.execute(query, (vehicle_id,))
            result = cur.fetchone()
            if result is None or result["last_ts"] is None:
                return None
            return dict(result)
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

    def vehicle_status_exists(self, vehicle_status_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM vehicle_status
            WHERE vehicle_status_id = %s"""

            cur.execute(query, (vehicle_status_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def vehicle_type_exists(self, vehicle_type_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)

            query = """
            SELECT 1
            FROM vehicle_type
            WHERE vehicle_type_id = %s"""

            cur.execute(query, (vehicle_type_id,))
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def plate_in_use(self, plate_number: str, vehicle_id: Optional[int] = None) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            if vehicle_id is None:
                query = """
                SELECT 1
                FROM vehicle
                WHERE TRIM(plate_number) = %s"""
                cur.execute(query, (plate_number,))
            else:
                query = """
                SELECT 1
                FROM vehicle
                WHERE TRIM(plate_number) = %s
                AND vehicle_id != %s"""
                cur.execute(query, (plate_number, vehicle_id,))

            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def has_location_pings(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            SELECT 1
            FROM location_ping
            WHERE vehicle_id = %s
            LIMIT 1"""
            cur.execute(query, (vehicle_id,))

            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def has_trips(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            SELECT 1
            FROM trip
            WHERE vehicle_id = %s
            LIMIT 1"""
            cur.execute(query, (vehicle_id,))

            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)

    def has_assignments(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            cur = conn.cursor(cursor_factory=DictCursor)
            query = """
            SELECT 1
            FROM vehicle_assignment
            WHERE vehicle_id = %s
            LIMIT 1"""
            cur.execute(query, (vehicle_id,))   
            result = cur.fetchone()
            return result is not None
        finally:
            cur.close()
            self.pool.putconn(conn)