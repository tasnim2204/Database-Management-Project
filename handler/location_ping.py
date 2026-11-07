from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.location_ping import LocationPingDAO
from datetime import datetime
from fastapi import HTTPException

class LocationPingCreate(BaseModel):
    vehicle_id: int
    ts: datetime
    geom: dict[str, Any]
    speed_kph: Optional[float] | None = None
    heading_deg: Optional[float] | None = None

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value
    @field_validator("speed_kph")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="speed_kph must be greater-than or equal-to 0.")
        return value
    @field_validator("heading_deg")
    @classmethod
    def validate_heading_deg(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not (0 <= value < 360):
            raise HTTPException(status_code=400, detail="heading_deg must be between greater-than or equal-to 0 and less-than 360.")
        return value
    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Point":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 2:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        lon, lat = coords

        if type(lon) not in (int, float) or type(lat) not in (int, float):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class LocationPingUpdate(BaseModel):
    vehicle_id: Optional[int] | None = None
    ts: Optional[datetime] | None = None
    geom: Optional[dict[str, Any]] | None = None
    speed_kph: Optional[float] | None = None
    heading_deg: Optional[float] | None = None

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value
    @field_validator("speed_kph")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="speed_kph must be greater-than or equal-to 0.")
        return value
    @field_validator("heading_deg")
    @classmethod
    def validate_heading_deg(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not (0 <= value < 360):
            raise HTTPException(status_code=400, detail="heading_deg must be between greater-than or equal-to 0 and less-than 360.")
        return value
    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Point":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) != 2:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        lon, lat = coords

        if type(lon) not in (int, float) or type(lat) not in (int, float):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class LocationHandler:
    def create_location_ping(self, new_ping_data: dict[str, Any] | LocationPingCreate):
        dao = LocationPingDAO()
        try:
            if isinstance(new_ping_data, LocationPingCreate):
                new_location = new_ping_data.model_dump(exclude_none=False)
            else:
                new_location = LocationPingCreate.model_validate(new_ping_data).model_dump(exclude_none=False)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        
        if not dao.vehicle_exists(new_location["vehicle_id"]):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")

        result = dao.create_location_ping(new_location)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return result

    def get_all_pings(self, limit: int, offset: int, vehicle_id: Optional[int]= None, from_ts: Optional[datetime] = None, to_ts: Optional[datetime]=None, bbox: Optional[str]=None):
        dao = LocationPingDAO()
        
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        if vehicle_id is not None:
            if vehicle_id <= 0:
                raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        
        if from_ts is not None and to_ts is not None and from_ts > to_ts:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")

        bbox_params=None
        if bbox and bbox.strip():
            try:
                parts = [float(p.strip()) for p in bbox.split(",")]
                if len(parts) != 4:
                    raise ValueError
                min_lon, min_lat, max_lon, max_lat = parts
            except ValueError:
                raise HTTPException(400, "Invalid query parameter values.")

            if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
                raise HTTPException(400, "Invalid query parameter values.")
            if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                raise HTTPException(400, "Invalid query parameter values.")
            if min_lon >= max_lon or min_lat >= max_lat:
                raise HTTPException(400, "Invalid query parameter values.")

            bbox_params = dict(min_lon=min_lon, min_lat=min_lat,
                               max_lon=max_lon, max_lat=max_lat)

        result = dao.get_all_pings(limit, offset, vehicle_id, from_ts, to_ts, bbox_params)
        return result

    def get_ping_by_id(self, ping_id: int):
        dao = LocationPingDAO()
        if ping_id <= 0:
            raise HTTPException(status_code=400, detail="ping_id must be a positive integer.")
        if not dao.location_exists(ping_id):
            raise HTTPException(status_code=404, detail="ping_id does not exist.")

        result = dao.get_ping_by_id(ping_id)
        if result is None:
            raise HTTPException(status_code=404, detail="ping_id does not exist.")
        return result

    def update_location_ping(self, ping_id: int, new_ping_data: dict | LocationPingUpdate):
        dao = LocationPingDAO()
        try:
            if isinstance(new_ping_data, LocationPingUpdate):
                new_location = new_ping_data.model_dump(exclude_unset=True)
            else:
                new_location = LocationPingUpdate.model_validate(new_ping_data).model_dump(exclude_unset=True)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
                
        if not new_location:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")

        if ping_id <= 0:
            raise HTTPException(status_code=400, detail="ping_id must be a positive integer.")
        if not dao.location_exists(ping_id):
            raise HTTPException(status_code=404, detail="ping_id does not exist.")

        result = dao.update_location_ping(ping_id, new_location)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return result

    def delete_location_ping(self, ping_id: int):
        dao = LocationPingDAO()
        if not dao.location_exists(ping_id):
            raise HTTPException(status_code=404, detail="ping_id does not exist.")
        
        result = dao.delete_location_ping(ping_id)
        if result is None:
            raise HTTPException(status_code=404, detail="ping_id does not exist.")

        return {"message": "Location ping deleted successfully.", 
                        "ping_id": ping_id}

    def get_pings_by_vehicle(self, vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None):
        dao = LocationPingDAO()
        
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")

        if not dao.vehicle_exists(vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        
        if from_ts is not None and to_ts is not None and from_ts > to_ts:
                raise HTTPException(status_code=400, detail="Invalid query parameters.")

        result = dao.get_pings_by_vehicle(vehicle_id, limit, offset, from_ts, to_ts)
        if result is None:
            raise HTTPException(status_code=400, detail="Invalid query parameters.")
        return result