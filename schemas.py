from pydantic import BaseModel , model_validator
from datetime import date , datetime
from typing import Optional


class VarietyCreate(BaseModel):
    name: str
    tracking_type: str

class VarietyOut(BaseModel):
    id: int
    name: str
    tracking_type: Optional[str] = None

class ProductCreate(BaseModel):
    barcode : str
    variety_id : int
    package_size_grams : Optional[int] = None


class ProductOut(BaseModel):
    barcode : str
    variety_id : int
    package_size_grams : Optional[int] = None

class ProductDeduct(BaseModel):
    variety_id: int
    grams : Optional[int] = None
    units : Optional[int] = None
    @model_validator(mode="after")
    def check_quantity(self):
        if self.grams is None and self.units is None:
            raise ValueError("Πρέπει να δώσεις είτε grams είτε units")
        return self

class BatchCreate(BaseModel):
    variety_id: int
    grams_remaining : Optional[int] = None
    units_remaining : Optional[int] = None
    expiry_date : date

    @model_validator(mode="after")
    def check_quantity(self):
        if self.grams_remaining is None and self.units_remaining is None:
            raise ValueError("Πρέπει να δώσεις είτε grams_remaining είτε units_remaining")
        return self

class BatchOut(BaseModel):
    id : int
    variety_id : int
    grams_remaining : Optional[int] = None
    units_remaining : Optional[int] = None
    expiry_date : date
    received_at : datetime

class ScanRequest(BaseModel):
    barcode: str



    