from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.trip import TripDAO
from datetime import datetime
from fastapi import HTTPException

class TripCreate(BaseModel):
    vehicle_id: int
    start_ts: datetime
    end_ts: datetime
    start_geom: Optional[dict[str, Any]] | None = None
    end_geom: Optional[dict[str, Any]] | None = None
    distance_km: Optional[float] | None = None

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value
    @field_validator("distance_km")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="distance_km must be greater-than or equal-to 0.")
        return value
    @field_validator("start_geom", "end_geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Point":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        lon, lat = coords

        if type(lon) not in (int, float) or type(lat) not in (int, float):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class TripUpdate(BaseModel):
    vehicle_id: Optional[int] | None = None
    start_ts: Optional[datetime] | None = None
    end_ts: Optional[datetime] | None = None
    start_geom: Optional[dict[str, Any]] | None = None
    end_geom: Optional[dict[str, Any]] | None = None
    distance_km: Optional[float] | None = None

    @field_validator("vehicle_id")
    @classmethod
    def validate_vehicle_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value
    @field_validator("distance_km")
    @classmethod
    def validate_speed(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="distance_km must be greater-than or equal-to 0.")
        return value
    @field_validator("start_geom", "end_geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "Point":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        lon, lat = coords

        if type(lon) not in (int, float) or type(lat) not in (int, float):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class TripHandler:
    def create_trip(self, new_trip_data: dict[str,Any] | TripCreate):
        dao = TripDAO()
        try:
            if isinstance(new_trip_data, TripCreate):
                new_trip = new_trip_data
            else:
                new_trip = TripCreate.model_validate(new_trip_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON. VALIDATE")
                
        if not dao.vehicle_exists(new_trip.vehicle_id):
            raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        try:
            result = dao.create_trip(new_trip.model_dump(exclude_none=True))
            return result
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Malformed geometry or invalid JSON. Error: {e}")

    def get_all_trips(self, limit: int, offset: int, from_ts: datetime, to_ts: datetime, vehicle_id: Optional[int]=None):
        dao = TripDAO()
                
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        if vehicle_id is not None:
            if vehicle_id < 0  or not dao.vehicle_exists(vehicle_id):
                raise HTTPException(status_code=400, detail="Invalid query parameter values.")
                
        if from_ts is not None and to_ts is not None and from_ts > to_ts:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        try:
            result = dao.get_all_trips(limit, offset, from_ts, to_ts, vehicle_id)
            if result is None:
                return None
            return result
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid query parameter values.")

    def get_trip_by_id(self, trip_id: int):
        dao = TripDAO()
        if trip_id < 0:
            raise HTTPException(status_code=404, detail="trip_id does not exist.")

        result = dao.get_trip_by_id(trip_id)
        if result is None:
            return None
        return result

    def update_trip(self, trip_id: int, new_trip_data: dict[str, Any] | TripUpdate):
        dao = TripDAO()
        try:
            if isinstance(new_trip_data, TripUpdate):
                new_trip = new_trip_data.model_dump(exclude_unset=True)
            else:
                new_trip = TripUpdate.model_validate(new_trip_data)
                new_trip = new_trip_data
        except ValidationError:
            raise HTTPException(status_code=422, detail="Validation failed.")
                
        if not new_trip:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        if trip_id < 0:
            raise HTTPException(status_code=404, detail="trip_id does not exist.")

        if "vehicle_id" in new_trip:
            if new_trip["vehicle_id"] < 0 or not dao.vehicle_exists(new_trip["vehicle_id"]):
                raise HTTPException(status_code=404, detail=" referenced vehicle_id does not exist.")
        if "start_ts" in new_trip and "end_ts" in new_trip:
            if new_trip["start_ts"] > new_trip["end_ts"]:
                raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        try:
            result = dao.update_trip(trip_id, new_trip)
            if result is None:
                return None
            return result
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

    def delete_trip(self, trip_id: int):
        dao = TripDAO()
        if trip_id < 0:
            raise HTTPException(status_code=404, detail="trip_id does not exist.")
        
        result = dao.delete_trip(trip_id)
        if result is None:
            raise HTTPException(status_code=404, detail="trip_id does not exist.")
        
        return {"message": "Trip deleted successfully.", 
                        "trip_id": trip_id}

    def get_trips_by_vehicle(self, vehicle_id: int, limit: int, offset: int, from_ts: Optional[datetime]=None, to_ts: Optional[datetime]=None):
        dao = TripDAO()
                
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")
        
        if vehicle_id is not None:
            if vehicle_id < 0 or not dao.vehicle_exists(vehicle_id):
                    raise HTTPException(status_code=404, detail="vehicle_id does not exist.")
        
        if from_ts is not None and to_ts is not None and from_ts > to_ts:
                raise HTTPException(status_code=400, detail="Invalid query parameters.")
        
        try:
            result = dao.get_trips_by_vehicle(vehicle_id, limit, offset, from_ts, to_ts)
            if result is None:
                return None
            return result
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid query parameters.")