from database import Base
import enum
from sqlalchemy import Column, Integer, String , ForeignKey , Date, DateTime , Enum
from datetime import datetime, timezone

class Direction(enum.Enum):
    IN = "IN"
    OUT = "OUT"

class TrackingType(enum.Enum):
    WEIGHT = "weight"
    UNITS = "units"

class Variety(Base):
    __tablename__ = "varieties"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True )
    tracking_type = Column(Enum(TrackingType))

class Product(Base):
    __tablename__ = "products"

    barcode = Column(String, primary_key=True)
    variety_id = Column(Integer, ForeignKey("varieties.id"))
    package_size_grams =  Column(Integer , nullable=True)

class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    variety_id = Column(Integer, ForeignKey("varieties.id"))
    grams_remaining = Column(Integer , nullable=True)
    units_remaining = Column(Integer , nullable=True)
    expiry_date = Column(Date)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True)
    barcode = Column(String, ForeignKey("products.barcode"), nullable=True)
    direction = Column(Enum(Direction))
    grams = Column(Integer)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))