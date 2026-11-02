from pydantic import BaseModel, ValidationError, field_validator
from typing import Optional, Any
from dao.road_segments import RoadSegmentDAO
from fastapi import HTTPException, Response
from psycopg2 import errors

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

class RoadSegmentUpdate(BaseModel):
    name: Optional[str] | None = None
    speed_limit_kph: Optional[int] | None = None
    is_oneway: Optional[bool] | None = None
    direction: Optional[str] | None = None
    geom: Optional[dict[str, Any]] | None = None

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
    @staticmethod
    def validate_geom(value: dict[str, Any], error_detail: str) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("type") != "LineString":
            raise HTTPException(status_code=400, detail=error_detail)

        coords = value.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2: #type: ignore
            raise HTTPException(status_code=400, detail=error_detail)
        
        for point in coords: #type: ignore
            if not isinstance(point, list) or len(point) != 2:
                raise HTTPException(status_code=400, detail=error_detail)
            lon, lat = point

            if type(lon) not in (int, float) or type(lat) not in (int, float):
                raise HTTPException(status_code=400, detail=error_detail)
            if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                raise HTTPException(status_code=400, detail=error_detail)
        return value

    def create_road_segment(self, new_road_data: RoadSegmentCreate):
        dao = RoadSegmentDAO()
        try:
            if isinstance(new_road_data, RoadSegmentCreate):
                new_road = new_road_data
            else:
                new_road = RoadSegmentCreate.model_validate(new_road_data)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

        try:
            result = dao.create_road_segment(new_road.model_dump(exclude_none=False))
            return result
        except Exception as e:
            # raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=400, detail=f"error: {e}")

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

        bbox_params: Optional[dict[str, float]] = None
        if bbox and bbox.strip(): 
            try:
                params = [float(p.strip()) for p in bbox.split(",")] #split string into values
                if len(params) != 4:
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                min_lon, min_lat, max_lon, max_lat = params

                if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
                    raise HTTPException(status_code=400, detail="Invalid field values.")
                if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                if min_lon > max_lon or min_lat > max_lat:
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                bbox_params = {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat
                }
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid field values.")
        
        try:
            result = dao.get_road_segments(limit, offset, name, min_speed_kph, max_speed_kph, bbox_params)
            return result if not None else None
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid field values.")

    def get_road_by_id(self, road_id: int, bbox: Optional[str]=None):
        dao = RoadSegmentDAO()

        if road_id <= 0:
            raise HTTPException(status_code=404, detail="road_id does not exist.INVALID")

        bbox_params: Optional[dict[str, float]] = None
        if bbox and bbox.strip(): 
            try:
                params = [float(p.strip()) for p in bbox.split(",")] #split string into values
                if len(params) != 4:
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                min_lon, min_lat, max_lon, max_lat = params

                if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
                    raise HTTPException(status_code=400, detail="Invalid field values.")
                if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                if min_lon > max_lon or min_lat > max_lat:
                    raise HTTPException(status_code=400, detail="Invalid field values.")

                bbox_params = {
                    "min_lon": min_lon,
                    "min_lat": min_lat,
                    "max_lon": max_lon,
                    "max_lat": max_lat
                }
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid field values.")
        try:
            result = dao.get_road_by_id(road_id, bbox_params)
            if result is None:
                raise HTTPException(status_code=404, detail="road_id does not exist.NONE")
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            # raise HTTPException(status_code=404, detail="road_id does not exist.")
            raise HTTPException(status_code=400, detail=f"Database Error: {str(e)}")

    def update_road_segment(self, road_id: int, new_road_data: dict[str, Any] | RoadSegmentUpdate):
        dao = RoadSegmentDAO()
        try:
            if isinstance(new_road_data, RoadSegmentUpdate):
                new_road = new_road_data.model_dump(exclude_unset=True)
            else:
                new_road = RoadSegmentUpdate.model_validate(new_road_data)
                new_road = new_road_data
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        
        if not new_road:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload.")
        if road_id <= 0:
            raise HTTPException(status_code=404, detail="road_id does not exist.")

        if "name" in new_road:
            new_road["name"] = new_road["name"].strip()
            if new_road["name"] == "":
                raise HTTPException(status_code=400, detail="name cannot be empty.")

        if "speed_limit_kph" in new_road and new_road["speed_limit_kph"] < 0:
            raise HTTPException(status_code=400, detail="speed_limit_kph must be greater-than or equal-to 0.")

        if "direction" in new_road:
            new_road["direction"] = new_road["direction"].strip().lower()
            if new_road["direction"] not in {"both", "forward"}: #type: ignore
                raise HTTPException(status_code=400, detail="name cannot be empty.")

        if "geom" in new_road:
            self.validate_geom(new_road["geom"], "Malformed geometry or invalid JSON.")

        try:
            result = dao.update_road_segment(road_id, new_road)
            if result is None:
                return None
            return result
        except Exception:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")

    def delete_road_segment(self, road_id:int):
        dao = RoadSegmentDAO()
        if road_id <= 0:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        result = dao.delete_road_segment(road_id)
        if result is None:
            raise HTTPException(status_code=404, detail="road_id does not exist.")
        
        return {"message": "Road segment deleted successfully.", 
                        "road_id": road_id}

    def get_road_geojson(self, limit:int, offset: int, name: Optional[str]=None, min_speed_kph: Optional[int]=None, max_speed_kph: Optional[int]=None, response: Optional[Response]=None):
        dao = RoadSegmentDAO()

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

            if response is not None:
                response.headers["Content-Type"] = "application/geo+json"

            return result
        except ValueError:
            raise HTTPException(status_code=422, detail="A query parameter fails type or range validation.")
        except Exception:
            raise HTTPException(status_code=500, detail=f"The service could not complete the request.")