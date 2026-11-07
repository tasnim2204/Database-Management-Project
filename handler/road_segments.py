import json
from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.road_segments import RoadSegmentDAO
from fastapi import HTTPException, Response

class RoadSegmentCreate(BaseModel):
    name: str
    speed_limit_kph: Optional[int] | None = None
    is_oneway: bool
    direction: str
    geom: dict[str, Any]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="name must be non-empty.")
        return value.strip()

    @field_validator("speed_limit_kph")
    @classmethod
    def validate_speed_limit(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="speed_limit_kph must be greater-than or equal-to 0.")
        return value

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value:str) -> str:
        if value is None:
            return None
        direction = value.strip().lower()
        if direction not in {"both", "forward"}:
            raise HTTPException(status_code=400, detail="direction can be 'both' or 'forward'.")
        return direction

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "LineString":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        for point in coords:
            if not isinstance(point, list) or len(point) != 2:
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            lon, lat = point

            if type(lon) not in (int, float) or type(lat) not in (int, float):
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class RoadSegmentUpdate(BaseModel):
    name: Optional[str] | None = None
    speed_limit_kph: Optional[int] | None = None
    is_oneway: Optional[bool] | None = None
    direction: Optional[str] | None = None
    geom: Optional[dict[str, Any]] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value:str) -> str:
        if not value or not value.strip():
            raise HTTPException(status_code=400, detail="name must be non-empty.")
        return value.strip()
    
    @field_validator("speed_limit_kph")
    @classmethod
    def validate_speed_limit(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise HTTPException(status_code=400, detail="speed_limit_kph must be greater-than or equal-to 0.")
        return value

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value:str) -> str:
        if value is None:
            return None
        direction = value.strip().lower()
        if direction not in {"both", "forward"}:
            raise HTTPException(status_code=400, detail="direction can be 'both' or 'forward'.")
        return direction

    @field_validator("geom")
    @classmethod
    def validate_geom(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "LineString":
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2: #type: ignore
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        for point in coords: #type: ignore
            if not isinstance(point, list) or len(point) != 2:
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            lon, lat = point

            if type(lon) not in (int, float) or type(lat) not in (int, float):
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
        return value

class RoadHandler:
    def create_road_segment(self, new_road_data: RoadSegmentCreate):
        dao = RoadSegmentDAO()
        try:
            if isinstance(new_road_data, RoadSegmentCreate):
                new_road = new_road_data.model_dump(exclude_none=False)
            else:
                new_road = RoadSegmentCreate.model_validate(new_road_data).model_dump(exclude_none=False)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        result = dao.create_road_segment(new_road)
        return result

    def get_road_segments(self, limit: int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None, bbox: Optional[str]=None):
        dao = RoadSegmentDAO()

        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="invalid field values.")

        if min_speed_kph is not None and min_speed_kph < 0:
            raise HTTPException(status_code=400, detail="Invalid field values.")
        if max_speed_kph is not None and max_speed_kph < 0:
            raise HTTPException(status_code=400, detail="Invalid field values.")
        if min_speed_kph is not None and max_speed_kph is not None and min_speed_kph > max_speed_kph:
            raise HTTPException(status_code=400, detail="Invalid field values.")

        result = dao.get_road_segments(limit, offset, name, min_speed_kph, max_speed_kph, bbox)
        return result

    def get_road_by_id(self, road_id: int, bbox: Optional[str]=None):
        dao = RoadSegmentDAO()

        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be a positive integer.")

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
            
        result = dao.get_road_by_id(road_id, bbox_params)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        return result

    def update_road_segment(self, road_id: int, new_road_data: dict[str, Any] | RoadSegmentUpdate):
        dao = RoadSegmentDAO()
        try:
            if isinstance(new_road_data, RoadSegmentUpdate):
                new_road = new_road_data.model_dump(exclude_unset=True)
            else:
                new_road = RoadSegmentUpdate.model_validate(new_road_data).model_dump(exclude_unset=True)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        
        if not new_road:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        if road_id <= 0 or not dao.road_exists(road_id):
            raise HTTPException(status_code=404, detail="road_id does not exist.")

        result = dao.update_road_segment(road_id, new_road)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        return result

    def delete_road_segment(self, road_id:int):
        dao = RoadSegmentDAO()
        if not dao.road_exists(road_id):
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        
        result = dao.delete_road_segment(road_id)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        
        return {"message": "Road segment deleted successfully.", 
                        "road_id": road_id}

    def get_road_geojson(self, limit:int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None, response: Optional[Response]=None):
        dao = RoadSegmentDAO()

        if response is not None:
            response.headers["Content-Type"] = "application/geo+json"

        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")

        if min_speed_kph is not None and min_speed_kph < 0:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")
        if max_speed_kph is not None and max_speed_kph < 0:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")
        if min_speed_kph is not None and max_speed_kph is not None and min_speed_kph > max_speed_kph:
            raise HTTPException(status_code=400, detail="Invalid or inconsistent filter values.")

        try:
            result = dao.get_road_geojson(limit, offset, name, min_speed_kph, max_speed_kph)

            return result
        except ValueError:
            raise HTTPException(status_code=422, detail="A query parameter fails type or range validation.")
        except Exception:
            raise HTTPException(status_code=500, detail="The service could not complete the request.")