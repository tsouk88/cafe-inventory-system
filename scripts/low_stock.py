import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import smtplib
from email.mime.text import MIMEText
from database import SessionLocal
from models import Product, StockMovement, Direction , Batch , Variety , TrackingType
from datetime import datetime, timezone , timedelta


gmail=os.getenv("GMAIL_ADDRESS")
password = os.getenv("GMAIL_PASSWORD") 
db = SessionLocal()
sales = db.query(StockMovement, Product.variety_id).filter(StockMovement.direction == Direction.OUT).filter(StockMovement.timestamp >= datetime.now(timezone.utc) - timedelta(weeks=1)).join(Product, StockMovement.barcode == Product.barcode)
moves = {}
remaining = {}
for movement , variety_id  in sales:
    moves[variety_id]=moves.get(variety_id , 0) + movement.grams
for variety_id in moves:
    batches = db.query(Batch).filter(Batch.variety_id == variety_id)
    variety=db.query(Variety).filter(variety_id == Variety.id).first()
    if variety.tracking_type == TrackingType.WEIGHT:
        for batch in batches:
            remaining[variety_id]= remaining.get(variety_id , 0) + batch.grams_remaining
    else:
        for batch in batches:
            remaining[variety_id]= remaining.get(variety_id , 0) + batch.units_remaining
days_left = {}
for variety_id in remaining:
    consumed = moves.get(variety_id, 0)
    if consumed == 0:
        continue
    days_left[variety_id] = remaining[variety_id] * 7 / consumed
low_stock_items = []
for variety_id in days_left:
    if days_left[variety_id] < 5:
        variety=db.query(Variety).filter(variety_id == Variety.id).first()
        low_stock_items.append(variety.name)
if len(low_stock_items) == 0:
    print("No low stocks detected")
else:
    low_stock = ", ".join(low_stock_items)
    msg = MIMEText(f"Watchout! {low_stock} have low stock..")
    msg["Subject"] = "LOW STOCK WARNING"
    msg["From"] = gmail
    msg["To"] = gmail
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail, password)
        server.send_message(msg)
db.close()