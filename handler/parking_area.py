from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.parking_area import ParkingAreaDAO
from fastapi import HTTPException

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
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

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
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

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
    def create_parking_area(self, new_parking_data: ParkingAreaCreate):
        dao = ParkingAreaDAO()
        try:
            if isinstance(new_parking_data, ParkingAreaCreate):
                new_parking = new_parking_data.model_dump(exclude_none=False)
            else:
                new_parking = ParkingAreaCreate.model_validate(new_parking_data).model_dump(exclude_none=False)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")  

        result = dao.create_parking_area(new_parking)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return result

    def get_parking_areas(self, limit: int, offset: int, name: Optional[str]=None, bbox: Optional[str]= None):
        dao = ParkingAreaDAO()
        
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")

        if name is not None:
            name = name.strip()

        result = dao.get_parking_areas(limit, offset, bbox)
        if result is None:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        return result

    def get_parking_by_id(self, parking_area_id: int):
        dao = ParkingAreaDAO()
        
        if parking_area_id <= 0:
            raise HTTPException(status_code=400, detail="parking_area_id must be a positive integer.")
        if not dao.parking_area_exists(parking_area_id):
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")

        result = dao.get_parking_by_id(parking_area_id)
        if result is None:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        return result

    def update_parking_area(self, parking_area_id: int, new_parking_data: dict[str, Any] | ParkingAreaUpdate):
        dao = ParkingAreaDAO()
        try:
            if isinstance(new_parking_data, ParkingAreaUpdate):
                new_parking = new_parking_data.model_dump(exclude_unset=True)
            else:
                new_parking = ParkingAreaUpdate.model_validate(new_parking_data).model_dump(exclude_unset=True)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        
        if not new_parking:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")

        if not dao.parking_area_exists(parking_area_id):
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")

        if "name" in new_parking:
            new_parking["name"] = new_parking["name"].strip()

        result = dao.update_parking_area(parking_area_id, new_parking)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return result

    def delete_parking_area(self, parking_area_id: int):
        dao = ParkingAreaDAO()

        if not dao.parking_area_exists(parking_area_id):
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")

        result = dao.delete_parking_area(parking_area_id)
        if result is None:
            raise HTTPException(status_code=404, detail="parking_area_id does not exist.")
        return {"message": "Parking area deleted successfully.", 
                "parking_area_id": parking_area_id}