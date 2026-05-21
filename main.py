import os
import subprocess
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
import qrcode
from io import BytesIO
from pydantic import BaseModel
from typing import List, Optional
import random
import string
import database
import qris
from bot import send_new_order_notification, start_bot_task
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_bot_task()
    yield
    # We could stop the bot here if needed

app = FastAPI(lifespan=lifespan)

# Default QRIS String
DEFAULT_QRIS = "00020101021126610014COM.GO-JEK.WWW01189360091439188482260210G9188482260303UMI51440014ID.CO.QRIS.WWW0215ID10264831152460303UMI5204581253033605802ID5924Hehe foodstore, PGDANGAN6009TANGERANG61051533462070703A016304BF71"

# Initialize DB
database.init_db()

# Pydantic Models
class OrderItemModel(BaseModel):
    name: str
    qty: int
    temperature: str
    sweetness: str
    price: int

class OrderPayload(BaseModel):
    customerName: str
    customerWA: str
    deliveryOption: str
    selectedFloor: str
    roomNumber: str
    discount: int
    items: List[OrderItemModel]

def generate_order_id():
    chars = string.ascii_uppercase + string.digits
    return "KONI-" + "".join(random.choice(chars) for _ in range(4))

def generate_dynamic_qris(amount: int) -> str:
    try:
        return qris.generate_dynamic_qris(DEFAULT_QRIS, amount)
    except Exception as e:
        print(f"Error generating QRIS: {e}")
        return DEFAULT_QRIS  # Fallback to static if it fails

@app.post("/api/orders")
async def create_order(order: OrderPayload):
    subtotal = sum(item.price * item.qty for item in order.items)
    total = subtotal - order.discount
    if total < 0:
        total = 0

    order_id = generate_order_id()
    qris_payload = generate_dynamic_qris(total)
    
    # Insert to DB
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (id, customer_name, customer_wa, total_price, qris_payload, delivery_mode, delivery_floor, delivery_room) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (order_id, order.customerName, order.customerWA, total, qris_payload, order.deliveryOption, order.selectedFloor, order.roomNumber)
    )
    
    for item in order.items:
        c.execute(
            "INSERT INTO order_items (order_id, menu_name, qty, temperature, sweetness, subtotal) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, item.name, item.qty, item.temperature, item.sweetness, item.price * item.qty)
        )
    
    conn.commit()
    conn.close()

    # Format items for telegram
    items_str = "\\n".join([f"- {item.qty}x {item.name} ({item.temperature}, {item.sweetness})" for item in order.items])
    delivery_str = f"Pickup di Kamar 4.02" if order.deliveryOption == "pickup" else f"Delivery ke Kamar ({order.selectedFloor} - {order.roomNumber})"
    
    # Notify Admin via Telegram (Async)
    await send_new_order_notification(
        order_id=order_id,
        customer_name=order.customerName,
        customer_wa=order.customerWA,
        total=total,
        delivery=delivery_str,
        items=items_str
    )

    return JSONResponse({"id": order_id, "qris_payload": qris_payload})

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    conn = database.get_db_connection()
    c = conn.cursor()
    
    # Get order
    order_row = c.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order_row:
        conn.close()
        return JSONResponse({"error": "Order not found"}, status_code=404)
        
    order = dict(order_row)
    
    # Get items
    items_rows = c.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    items = [dict(row) for row in items_rows]
    
    conn.close()
    
    # Prepare times array for tracking
    times = []
    # Index 0: Created
    times.append(order['created_at'].split(" ")[1][:5]) # "15:43"
    # Wait, the DB stores UTC timestamps. The frontend might need to be adjusted, but it expects strings like "14:20"
    # For now we mock the rest
    for i in range(1, 5):
        if order['status'] >= i:
            times.append(order['created_at'].split(" ")[1][:5])
        else:
            times.append(None)
            
    order['times'] = times
    
    return JSONResponse({
        "order": order,
        "items": items
    })

@app.get("/api/qris/{order_id}")
async def get_qris_image(order_id: str):
    conn = database.get_db_connection()
    c = conn.cursor()
    order_row = c.execute("SELECT qris_payload FROM orders WHERE id = ?", (order_id,)).fetchone()
    conn.close()
    
    if not order_row:
        return JSONResponse({"error": "Order not found"}, status_code=404)
        
    payload = order_row["qris_payload"]
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return Response(content=img_io.getvalue(), media_type="image/png")

@app.get("/api/menu")
async def get_menu():
    conn = database.get_db_connection()
    c = conn.cursor()
    menu_rows = c.execute("SELECT * FROM menus").fetchall()
    conn.close()
    
    menus = {}
    for row in menu_rows:
        cat = row["category"]
        if cat not in menus:
            menus[cat] = []
        menus[cat].append({
            "id": row["id"],
            "name": row["name"],
            "desc": row["description"],
            "price": row["price"],
            "available": bool(row["is_available"])
        })
    return JSONResponse(menus)

@app.get("/api/store_status")
async def get_store_status():
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT setting_value FROM store_settings WHERE setting_key = 'is_open'").fetchone()
    conn.close()
    is_open = True if row and row["setting_value"] == '1' else False
    return JSONResponse({"is_open": is_open})

class VoucherPayload(BaseModel):
    code: str
    subtotal: int

@app.post("/api/vouchers/validate")
async def validate_voucher(payload: VoucherPayload):
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT * FROM vouchers WHERE code = ? AND is_active = 1", (payload.code.upper(),)).fetchone()
    conn.close()
    
    if not row:
        return JSONResponse({"error": "Voucher tidak valid atau sudah tidak aktif"}, status_code=400)
        
    discount = 0
    if row["discount_type"] == "percent":
        discount = int(payload.subtotal * (row["discount_amount"] / 100))
    else:
        discount = int(row["discount_amount"])
        
    return JSONResponse({"discount": discount, "code": row["code"]})

# Serve static files for the frontend
app.mount("/", StaticFiles(directory=".", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
