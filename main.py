from fastapi import FastAPI, Depends , HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from models import Variety , Product , Batch , StockMovement , Direction , TrackingType
from schemas import VarietyCreate , VarietyOut , ProductCreate , ProductOut , BatchOut , BatchCreate , ScanRequest , ProductDeduct

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/varieties", response_model=list[VarietyOut])
def get_varieties(db: Session = Depends(get_db)):
    varieties = db.query(Variety).all()
    return varieties

@app.post("/varieties", response_model=VarietyOut)
def create_variety(variety: VarietyCreate, db: Session = Depends(get_db)):
    new_variety = Variety(name=variety.name , tracking_type=variety.tracking_type)   
    db.add(new_variety)                          
    db.commit()                                  
    db.refresh(new_variety)                      
    return new_variety

@app.post("/products", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    new_product = Product(barcode=product.barcode , variety_id =product.variety_id , package_size_grams = product.package_size_grams)
    db.add(new_product)
    db.commit()
    return new_product

@app.get("/products" , response_model=list[ProductOut])
def get_products( db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return products

@app.post("/batches" , response_model=BatchOut)
def create_batch(batch: BatchCreate, db: Session = Depends(get_db)):
    new_batch=Batch(variety_id=batch.variety_id , grams_remaining=batch.grams_remaining, units_remaining=batch.units_remaining , expiry_date=batch.expiry_date)
    db.add(new_batch)
    if new_batch.units_remaining is None:
        new_movement = StockMovement(
            barcode = None,
            direction=Direction.IN,
            grams=new_batch.grams_remaining
                    )
    else:
        new_movement = StockMovement(
            barcode = None,
            direction=Direction.IN,
            grams=new_batch.units_remaining
                    )
    db.add(new_movement)
    db.commit()
    db.refresh(new_batch)
    return new_batch

@app.get("/batches" , response_model=list[BatchOut])
def get_batches( db: Session = Depends(get_db)):
    batches = db.query(Batch).all()
    return batches

@app.post("/scan")
def scan_barcode(scan: ScanRequest, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.barcode == scan.barcode).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    variety = db.query(Variety).filter(Variety.id == product.variety_id).first()
    if variety.tracking_type == TrackingType.WEIGHT:
        if product.package_size_grams is None:
            raise HTTPException(status_code=400, detail="Weight product χωρίς package_size_grams")
        remaining_to_subtract = product.package_size_grams
        batches = db.query(Batch).filter(Batch.variety_id == product.variety_id).order_by(Batch.expiry_date).all()
        for batch in batches:
            if remaining_to_subtract == 0:
                break
            elif batch.grams_remaining >= remaining_to_subtract:
                batch.grams_remaining -= remaining_to_subtract
                remaining_to_subtract = 0
            else:
                remaining_to_subtract -= batch.grams_remaining
                batch.grams_remaining = 0
        new_movement = StockMovement(
        barcode=scan.barcode,
        direction=Direction.OUT,
        grams=product.package_size_grams
                )
        db.add(new_movement)
        db.commit()
        return  {"barcode": product.barcode,
                "grams_removed": product.package_size_grams,
                "status": "completed"
                }
    else:
        batch = db.query(Batch).filter(Batch.variety_id == product.variety_id).filter(Batch.units_remaining > 0).order_by(Batch.expiry_date).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        batch.units_remaining -= 1
        new_movement = StockMovement(
        barcode=scan.barcode,
        direction=Direction.OUT,
        grams=1
            )
        db.add(new_movement)
        db.commit()
        return  {"barcode": product.barcode,
            "units_removed": 1,
            "status": "completed"
            }

@app.post("/deduct")
def manual_deduct(deduct: ProductDeduct, db: Session = Depends(get_db)):
    variety = db.query(Variety).filter(Variety.id == deduct.variety_id).first()
    if variety is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if variety.tracking_type == TrackingType.WEIGHT:
        remaining_to_subtract = deduct.grams
        batches = db.query(Batch).filter(Batch.variety_id == deduct.variety_id).order_by(Batch.expiry_date).all()
        for batch in batches:
            if remaining_to_subtract == 0:
                break
            elif batch.grams_remaining >= remaining_to_subtract:
                batch.grams_remaining -= remaining_to_subtract
                remaining_to_subtract = 0
            else:
                remaining_to_subtract -= batch.grams_remaining
                batch.grams_remaining = 0
        new_movement = StockMovement(
        barcode=None,
        direction=Direction.OUT,
        grams=deduct.grams
                )
        db.add(new_movement)
        db.commit()
        return  {"barcode": "MANUAL",
                "grams_removed": deduct.grams,
                "status": "completed"
                }
    else :
        batch = db.query(Batch).filter(Batch.variety_id == deduct.variety_id).filter(Batch.units_remaining > 0).order_by(Batch.expiry_date).first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        batch.units_remaining -= deduct.units
        new_movement = StockMovement(
        barcode=None,
        direction=Direction.OUT,
        grams=deduct.units
            )
        db.add(new_movement)
        db.commit()
        return  {"barcode": "MANUAL",
            "units_removed": deduct.units,
            "status": "completed"
            }