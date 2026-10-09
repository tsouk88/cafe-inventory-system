from fastapi import FastAPI, Depends , HTTPException 
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from models import Variety , Product , Batch , StockMovement , Direction , TrackingType , Reason
from schemas import VarietyCreate , VarietyOut , ProductCreate , ProductOut , BatchOut , BatchCreate , ScanRequest , ProductDeduct
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.frontend("/", directory="frontend/dist")

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
    new_batch=Batch(variety_id=batch.variety_id , grams_remaining=batch.grams_remaining, units_remaining=batch.units_remaining , expiry_date=batch.expiry_date )
    db.add(new_batch)
    db.flush()  
    if new_batch.units_remaining is None:
        new_movement = StockMovement(
            barcode = None,
            direction=Direction.IN,
            grams=new_batch.grams_remaining,
            reason=Reason.RESTOCK,
            batch_id=new_batch.id
                    )
    else:
        new_movement = StockMovement(
            barcode = None,
            direction=Direction.IN,
            grams=new_batch.units_remaining,
            reason=Reason.RESTOCK,
            batch_id=new_batch.id
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
        batches = db.query(Batch).filter(Batch.variety_id == product.variety_id , Batch.expiry_date >= date.today()).order_by(Batch.expiry_date).with_for_update().all()
        for batch in batches:
            if remaining_to_subtract == 0:
                break
            elif batch.grams_remaining >= remaining_to_subtract:
                taken = remaining_to_subtract
                batch.grams_remaining -= remaining_to_subtract
                remaining_to_subtract = 0
            else:
                taken=batch.grams_remaining
                remaining_to_subtract -= batch.grams_remaining
                batch.grams_remaining = 0
            if taken > 0:
                new_movement = StockMovement(
                    barcode=scan.barcode,
                    direction=Direction.OUT,
                    grams=taken,
                    reason=Reason.SALE,
                    batch_id=batch.id
                                )
                db.add(new_movement)
        # The package physically left the shop, so the movements always add up to
        # the full package size. Whatever the batches could not cover is recorded
        # as one movement with no batch - the data disagrees with the shelf, and
        # someone has to look.
        stock_shortfall = remaining_to_subtract
        if stock_shortfall > 0:
            new_movement = StockMovement(
                                barcode=scan.barcode,
                                direction=Direction.OUT,
                                grams=stock_shortfall,
                                reason=Reason.SALE,
                                batch_id=None
                                            )
            db.add(new_movement)
        db.commit()
        if stock_shortfall == 0:
            status = "completed"
        else:
            status = "stock_mismatch"
       
       
        return  {"barcode": product.barcode,
                "grams_removed": product.package_size_grams,
                "stock_shortfall": stock_shortfall,
                "status": status
                }
    else:
        batch = db.query(Batch).filter(Batch.variety_id == product.variety_id).filter(Batch.units_remaining > 0 , Batch.expiry_date >= date.today()).order_by(Batch.expiry_date).with_for_update().first()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        batch.units_remaining -= 1
        new_movement = StockMovement(
        barcode=scan.barcode,
        direction=Direction.OUT,
        grams=1,
        reason=Reason.SALE,
        batch_id=batch.id
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
        batches = db.query(Batch).filter(Batch.variety_id == deduct.variety_id , Batch.expiry_date >= date.today()).order_by(Batch.expiry_date).with_for_update().all()
        for batch in batches:
            if remaining_to_subtract == 0:
                break
            elif batch.grams_remaining >= remaining_to_subtract:
                taken = remaining_to_subtract
                batch.grams_remaining -= remaining_to_subtract
                remaining_to_subtract = 0
            else:
                taken= batch.grams_remaining
                remaining_to_subtract -= batch.grams_remaining
                batch.grams_remaining = 0
            if taken > 0:
                new_movement = StockMovement(
                barcode=None,
                direction=Direction.OUT,
                grams=taken,
                reason=Reason.SALE,
                batch_id=batch.id
                        )
                db.add(new_movement)
        db.commit()
        return  {"barcode": "MANUAL",
                "grams_removed": deduct.grams,
                "status": "completed"
                }
    else :
        batches = db.query(Batch).filter(Batch.variety_id == deduct.variety_id).filter(Batch.units_remaining > 0, Batch.expiry_date >= date.today()).order_by(Batch.expiry_date).with_for_update().all()
        if not batches:
            raise HTTPException(status_code=404, detail="Batch not found")
        remaining_to_subtract = deduct.units
        for batch in batches:
            if remaining_to_subtract == 0:
                break
            elif batch.units_remaining >= remaining_to_subtract:
                taken=remaining_to_subtract
                batch.units_remaining -= remaining_to_subtract
                remaining_to_subtract = 0
            else:
                taken=batch.units_remaining
                remaining_to_subtract -= batch.units_remaining
                batch.units_remaining = 0
            if taken > 0:
                new_movement = StockMovement(
                        barcode=None,
                        direction=Direction.OUT,
                        grams=taken,
                        reason=Reason.SALE,
                        batch_id=batch.id
                            )
                db.add(new_movement)
        db.commit()
        units_removed = deduct.units - remaining_to_subtract
        return  {"barcode": "MANUAL",
            "units_removed": units_removed,
            "status": "completed" if remaining_to_subtract == 0 else "stock_mismatch"
            }

@app.post("/batches/{batch_id}/discard")
def discard(batch_id: int , db: Session= Depends(get_db) ):
    batch = db.query(Batch).filter(Batch.id==batch_id).with_for_update().first()
    if batch is None :
        raise HTTPException(status_code=404, detail="Batch not found")
    if batch.grams_remaining == 0 or batch.units_remaining == 0:
        raise HTTPException(status_code=409, detail="Batch is already 0")
    if batch.expiry_date >= date.today():
        raise HTTPException(status_code=409 , detail="Batch hasn't expired yet")
    if batch.grams_remaining is not None:     
        remaining=batch.grams_remaining 
        batch.grams_remaining = 0      
    else:  
        remaining = batch.units_remaining
        batch.units_remaining = 0   
    new_movement = StockMovement(
                        barcode=None,
                        direction=Direction.OUT,
                        grams=remaining,
                        reason=Reason.EXPIRED,
                        batch_id=batch.id
                            )         
    db.add(new_movement)
    db.commit()
    return  {"Removed Batch" : batch.id,
             "Expired at" : batch.expiry_date
            }

@app.post("/batches/{batch_id}/correct")
def correct(counted: int , batch_id: int , db: Session= Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id==batch_id).with_for_update().first()
    if counted < 0 :
        raise HTTPException(status_code=400, detail="Wrong Number")
    if batch is None :
        raise HTTPException(status_code=404, detail="Batch not found")
    if counted == batch.grams_remaining or counted == batch.units_remaining:
        raise HTTPException(status_code=409, detail="Stock already matches")
    if batch.grams_remaining is not None:
        if counted > batch.grams_remaining :
            added = counted - batch.grams_remaining
            new_movement = StockMovement(
                            barcode=None,
                            direction=Direction.IN,
                            grams=added,
                            reason=Reason.CORRECTION,
                            batch_id=batch.id
                                )
            batch.grams_remaining = counted         
            db.add(new_movement)
        else:
            added=batch.grams_remaining-counted
            new_movement = StockMovement(
                            barcode=None,
                            direction=Direction.OUT,
                            grams=added,
                            reason=Reason.CORRECTION,
                            batch_id=batch.id
                            )
            batch.grams_remaining = counted 
            db.add(new_movement)
    else:
        if counted > batch.units_remaining :
            added = counted - batch.units_remaining
            new_movement = StockMovement(
                            barcode=None,
                            direction=Direction.IN,
                            grams=added,
                            reason=Reason.CORRECTION,
                            batch_id=batch.id
                                )    
            batch.units_remaining = counted     
            db.add(new_movement)
        else:
            added=batch.units_remaining-counted
            new_movement = StockMovement(
                    barcode=None,
                    direction=Direction.OUT,
                    grams=added,
                    reason=Reason.CORRECTION,
                    batch_id=batch.id
                    )
            batch.units_remaining = counted 
            db.add(new_movement)
    db.commit()
    return {"Changes on batch" : batch_id}

                



@app.get("/reports/fefo-next")
def getreports(db: Session = Depends(get_db)):
    fefo_nextbatch = db.execute(text("""select
        first.name,
        first.min_expiry,
        coalesce(b2.units_remaining, b2.grams_remaining) as remaining
        from
        (
            select
            v.id as variety_id,
            v.name,
            min(b.expiry_date) as min_expiry
            from
            varieties v
            join batches b on b.variety_id = v.id
            and b.expiry_date >= current_date
            and coalesce(b.units_remaining, b.grams_remaining) > 0
            group by
            v.id,
            v.name
        ) as first
        join batches b2 on b2.variety_id = first.variety_id
        and b2.expiry_date = first.min_expiry
        order by
        first.min_expiry""")).mappings().all()
    return fefo_nextbatch

@app.get("/reports/last7")
def getlastseven (db: Session = Depends(get_db)):
    last7=db.execute(text("""select coalesce(vb.name, vp.name) as name , s.timestamp , s.reason , s.direction , s.grams as stock
        from stock_movements s
        left join batches b on s.batch_id = b.id
        left join varieties vb on b.variety_id = vb.id
        left join products p on s.barcode = p.barcode
        left join varieties vp on p.variety_id = vp.id
        where s.timestamp > now() - interval '7 days'
        order by s.timestamp desc
        """)).mappings().all()
    return last7

@app.get("/reports/stock-per-variety")
def getstockpervariety(db: Session= Depends(get_db)):
    getstock=db.execute(text("""select v.name , coalesce(sum(coalesce(units_remaining, grams_remaining)), 0) as remaining , count(b.id) as active_batches , v.tracking_type
        from varieties v
        left join batches b on b.variety_id = v.id
        and coalesce(b.units_remaining , b.grams_remaining) > 0 and b.expiry_date >= current_date
        group by v.id , v.name
        order by remaining desc""")).mappings().all()
    return getstock

@app.get("/reports/expired-with-stock")
def expired(db: Session= Depends(get_db)):
    expired = db.execute(text("""select v.name , v.tracking_type , coalesce(b.units_remaining, b.grams_remaining) as stock , b.expiry_date as expired_at 
        from varieties v
        join batches b on b.variety_id = v.id
        and b.expiry_date < current_date
        and coalesce(b.units_remaining, b.grams_remaining) > 0
        order by expired_at desc
        """)).mappings().all()
    return expired

@app.get("/reports/waste")
def wasted(db:Session=Depends(get_db)):
    wasted = db.execute(text("""select v.name , sum(s.grams) as thrown , v.tracking_type
                    from stock_movements s
                    join batches b on s.batch_id = b.id
                    join varieties v on b.variety_id = v.id
                    where s.reason='EXPIRED'
                    group by v.name , v.tracking_type
                    order by thrown DESC""")).mappings().all()
    return wasted
