from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class JobBase(BaseModel):
    filename: str

class JobCreate(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    status: str
    image_paths: Optional[List[str]] = None  # CRITICAL FIX: Add image_paths field
    created_at: datetime
    
    class Config:
        orm_mode = True

class TestCaseResponse(BaseModel):
    test_id: str
    description: str
    preconditions: str
    steps: List[str]
    expected_output: str

    class Config:
        orm_mode = True
