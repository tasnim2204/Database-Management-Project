from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.parking_area import ParkingAreaDAO
from fastapi import HTTPException, Response
from psycopg2 import errors

class ParkingAreaCreate(BaseModel):
    name: str
    capacity: Optional[int] | None = None
    geom: dict[str, Any]
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="name must be non-empty.")
        return value.strip()
    
    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="capacity must be greater-than or equal-to 0.")
        return value

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Polygon":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.POLG")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) == 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        
        for ring in coords:
            if not isinstance(ring, list) or len(ring) < 4:
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            if ring[0] != ring[-1]: #confirmando que el ring esta cerrado
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            
            for point in ring:
                if not isinstance(point, list) or len(point) != 2:
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
                lon, lat = point
                if type(lon) not in (int, float) or type(lat) not in (int, float):
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
                if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class ParkingAreaUpdate(BaseModel):
    name: Optional[str] | None = None
    capacity: Optional[int] | None = None
    geom: Optional[dict[str, Any]] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="name must be non-empty.")
        return value.strip()
    
    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="capacity must be greater-than or equal-to 0.")
        return value
    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Polygon":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.POLG")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) == 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        
        for ring in coords:
            if not isinstance(ring, list) or len(ring) < 4:
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            if ring[0] != ring[-1]: #confirmando que el ring esta cerrado
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            
            for point in ring:
                if not isinstance(point, list) or len(point) != 2:
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
                lon, lat = point
                if type(lon) not in (int, float) or type(lat) not in (int, float):
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
                if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                    raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value
    
class ParkingHandler:
    @staticmethod
    def validate_geom( value: dict[str, Any], error_detail: str) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Polygon":
            raise HTTPException(status_code=400, detail=error_detail)  
        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) == 0:
            raise HTTPException(status_code=400, detail=error_detail)

        for ring in coords:
            if not isinstance(ring, list) or len(ring) < 4:
                raise HTTPException(status_code=400, detail=error_detail)
            if ring[0] != ring[-1]: #confirmando que el ring esta cerrado
                raise HTTPException(status_code=400, detail=error_detail)

            for point in ring:
                if not isinstance(point, list) or len(point) != 2:
                    raise HTTPException(status_code=400, detail=error_detail)
                lon, lat = point
                if type(lon) not in (int, float) or type(lat) not in (int, float):
                    raise HTTPException(status_code=400, detail=error_detail)
                if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                    raise HTTPException(status_code=400, detail=error_detail)
        return value

    def create_parking_area(self, new_parking_data: ParkingAreaCreate):
        dao = ParkingAreaDAO()
        try:
            if isinstance(new_parking_data, ParkingAreaCreate):
                new_parking = new_parking_data
            else:
                new_parking = ParkingAreaCreate.model_validate(new_parking_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON. VALDATION")  
        try:
            result = dao.create_parking_area(new_parking.model_dump(exclude_none=True))
            return result
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON. Except")

    def get_parking_areas(self, limit: int, offset: int, bbox: Optional[str]= None):
        dao = ParkingAreaDAO()
        
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")

        if bbox and bbox.strip():
            try:
                params = [float(p.strip()) for p in bbox.split(",")] #split string into values
                if len(params) != 4:
                    raise HTTPException(status_code=400, detail="Invalid query parameter values.")

                min_lon, min_lat, max_lon, max_lat = params
                if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
                    raise HTTPException(status_code=400, detail="Invalid query parameter values.")
                if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                    raise HTTPException(status_code=400, detail="Invalid query parameter values.")
                if min_lon > max_lon or min_lat > max_lat:
                    raise HTTPException(status_code=400, detail="Invalid query parameter values.")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid query parameter values.")

        try:
            result = dao.get_parking_areas(limit, offset, bbox)
            if result is None:
                return None
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid query parameter values. Error: {e}")

    def get_parking_by_id(self, parking_area_id: int):
        dao = ParkingAreaDAO()
        
        if parking_area_id <= 0:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        try:
            result = dao.get_parking_by_id(parking_area_id)
            if result is None:
                raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
            return result
        except Exception:
            raise HTTPException(status_code=404, detail="road_id does not exist.")

    def update_parking_area(self, parking_area_id: int, new_parking_data: dict[str, Any] | ParkingAreaUpdate):
        dao = ParkingAreaDAO()
        try:
            if isinstance(new_parking_data, ParkingAreaUpdate):
                new_parking = new_parking_data.model_dump(exclude_unset=True)
            else:
                new_parking = ParkingAreaUpdate.model_validate(new_parking_data)
                new_parking = new_parking_data
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        
        if not new_parking:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")

        if parking_area_id <= 0:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")

        if "name" in new_parking:
            new_parking["name"] = new_parking["name"].strip()
            if new_parking["name"] == "":
                raise HTTPException(status_code=400, detail="name cannot be empty.")
        if "capacity" in new_parking and new_parking["capacity"] < 0:
                    raise HTTPException(status_code=400, detail="capacity must be greater-than or equal-to 0.")
        if "geom" in new_parking:
            self.validate_geom(new_parking["geom"], "Malformed JSON or empty patch payload.")
        
        try:
            result = dao.update_parking_area(parking_area_id, new_parking)
            if result is None:
                return None
            return result
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

    def delete_parking_area(self, parking_area_id: int):
        dao = ParkingAreaDAO()

        if parking_area_id <= 0:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        try:
            result = dao.delete_parking_area(parking_area_id)
            if result is None:
                return None
            return {"message": "Parking area deleted successfully.", "parking_area_id": parking_area_id}
        except Exception:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")