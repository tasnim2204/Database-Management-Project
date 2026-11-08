from datetime import datetime
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Optional, Any
from dao.vehicle_assignment import VehicleAssignmentDAO
from fastapi import HTTPException

class VehicleAssignmentCreate(BaseModel):
    vehicle_id: int
    driver_id: int
    assigned_from: datetime
    assigned_to: Optional[datetime] | None = None

    @field_validator("vehicle_id", "driver_id")
    @classmethod
    def validate_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value

class VehicleAssignmentUpdate(BaseModel):
    vehicle_id: Optional[int] | None = None
    driver_id: Optional[int] | None = None
    assigned_from: Optional[datetime] | None = None
    assigned_to: Optional[datetime] | None = None

    @field_validator("vehicle_id", "driver_id")
    @classmethod
    def validate_id(cls, value: int) -> int:
        if value <= 0:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape.")
        return value
    @model_validator(mode="after")
    def check_assigned_order(self):
        if self.assigned_from is not None and self.assigned_to is not None and self.assigned_from >= self.assigned_to:
            raise HTTPException(status_code=422, detail="The assignment time interval is invalid.")
        return self

class VehicleAssignmentHandler:
    def create_vehicle_assignment(self, new_assignment_data: dict[str, Any] | VehicleAssignmentCreate):
        dao = VehicleAssignmentDAO()
        try:
            if isinstance(new_assignment_data, VehicleAssignmentCreate):
                new_veh_assignment = new_assignment_data.model_dump(exclude_none=False)
            else:
                new_veh_assignment = VehicleAssignmentCreate.model_validate(new_assignment_data).model_dump(exclude_none=False)
        except ValidationError:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON.")
                
        if not dao.vehicle_exists(new_veh_assignment["vehicle_id"]):
            raise HTTPException(status_code=404, detail="Referenced vehicle_id does not exist.")
        if not dao.driver_exists(new_veh_assignment["driver_id"]):
            raise HTTPException(status_code=404, detail="Referenced driver_id does not exist.")
        if new_veh_assignment["assigned_to"] is not None:
            if new_veh_assignment["assigned_from"] >= new_veh_assignment["assigned_to"]:
                raise HTTPException(status_code=422, detail="The assignment time interval is invalid.")

        result = dao.create_vehicle_assignment(new_veh_assignment)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid payload shape.")
        return result

    def get_vehicle_assignments(self, limit: int, offset: int, vehicle_id: Optional[int]=None, driver_id: Optional[int]=None, active: Optional[bool]=None):
        dao = VehicleAssignmentDAO()
                        
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        if vehicle_id is not None:
            if vehicle_id <= 0  or not dao.vehicle_exists(vehicle_id):
                raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        if driver_id is not None:
            if driver_id <= 0  or not dao.driver_exists(driver_id):
                raise HTTPException(status_code=400, detail="Invalid query parameter values.")

        result = dao.get_vehicle_assignments(limit, offset, vehicle_id, driver_id, active)
        if result is None:
            raise HTTPException(status_code=400, detail="Invalid query parameter values.")
        return result

    def get_assignment_by_id(self, assignment_id: int):
        dao = VehicleAssignmentDAO()

        if assignment_id <= 0:
            raise HTTPException(status_code=400, detail="assignment_id must be a positive integer.")  
        
        result = dao.get_assignment_by_id(assignment_id)
        if result is None:
            raise HTTPException(status_code=404, detail="assignment_id does not exist.")  
        return result

    def update_vehicle_assignment(self, assignment_id: int, new_assignment_data: dict[str, Any] | VehicleAssignmentUpdate):
        dao = VehicleAssignmentDAO()
        try:
            if isinstance(new_assignment_data, VehicleAssignmentUpdate):
                new_assignment = new_assignment_data.model_dump(exclude_unset=True)
            else:
                new_assignment = VehicleAssignmentUpdate.model_validate(new_assignment_data).model_dump(exclude_unset=True)
        except ValidationError:
            raise HTTPException(status_code=422, detail="The resulting assignment interval is invalid.")
                
        if not new_assignment:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload.")
        if assignment_id <= 0 or not dao.assignment_exists(assignment_id):
            raise HTTPException(status_code=404, detail="assignment_id does not exist.")

        if "vehicle_id" in new_assignment:
            if new_assignment["vehicle_id"] is None or not dao.vehicle_exists(new_assignment["vehicle_id"]):
                raise HTTPException(status_code=404, detail=" referenced foreign key does not exist.")
        if "driver_id" in new_assignment:
            if new_assignment["driver_id"] is None or not dao.driver_exists(new_assignment["driver_id"]):
                raise HTTPException(status_code=404, detail=" referenced foreign key does not exist.")

        if "assigned_from" in new_assignment and "assigned_to" in new_assignment:
            if new_assignment["assigned_from"] >= new_assignment["assigned_to"]:
                raise HTTPException(status_code=422, detail="The resulting assignment interval is invalid.")

        result = dao.update_vehicle_assignment(assignment_id, new_assignment)
        if result is None:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload.")
        return result

    def delete_vehicle_assignment(self, assignment_id: int):
        dao = VehicleAssignmentDAO()
        if not dao.assignment_exists(assignment_id):
            raise HTTPException(status_code=404, detail="assignment_id does not exist.")
        
        result = dao.delete_vehicle_assignment(assignment_id)
        if result is None:
            raise HTTPException(status_code=404, detail="assignment_id does not exist.")
        
        return {"message": "Vehicle assignment deleted successfully.", 
                        "assignment_id": assignment_id}