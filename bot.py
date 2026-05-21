import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import database

# Use the provided token
TELEGRAM_BOT_TOKEN = "8927370450:AAHbxORL3JtvDXjKk-SOsv7AE6oqxULr0xs"
# Admin Chat ID. In a real scenario, the admin would start the bot to register their chat ID.
# For now, we'll store the chat ID of whoever sends /start to the bot.
# Or if it's already known, we could hardcode it. Let's make it so /start registers them as an admin.

admin_chat_ids = set()

# Initialize bot app
bot_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

def is_admin(chat_id: int) -> bool:
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT 1 FROM admin_whitelist WHERE telegram_chat_id = ?", (str(chat_id),)).fetchone()
    conn.close()
    return bool(row)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    admin_name = update.effective_chat.first_name
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admin_whitelist (telegram_chat_id, admin_name) VALUES (?, ?)", (chat_id, admin_name))
    conn.commit()
    conn.close()
    admin_chat_ids.add(chat_id)
    await update.message.reply_text(f"Halo {admin_name}, berhasil mendaftar sebagai Admin Kopi Koni! (Chat ID: {chat_id})\n\nPerintah tersedia:\n/toggle_store - Buka/Tutup Toko\n/toggle_stock - Ubah status stok menu\n/voucher - Kelola voucher")

def get_status_keyboard(order_id: str):
    keyboard = [
        [
            InlineKeyboardButton("Terima & Konfirmasi", callback_data=f"status_{order_id}_1"),
            InlineKeyboardButton("Mulai Dibuat", callback_data=f"status_{order_id}_2"),
        ],
        [
            InlineKeyboardButton("Siap Diambil", callback_data=f"status_{order_id}_3"),
            InlineKeyboardButton("Selesai", callback_data=f"status_{order_id}_4"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_new_order_notification(order_id: str, customer_name: str, customer_wa: str, total: int, delivery: str, items: str):
    message = (
        f"🚨 *PESANAN BARU!* 🚨\n\n"
        f"💳 *Order ID*: {order_id}\n"
        f"👤 *Pemesan*: {customer_name}\n"
        f"📱 *WA*: {customer_wa}\n"
        f"💰 *Total*: Rp {total:,}\n"
        f"📦 *Pengiriman*: {delivery}\n\n"
        f"🛒 *Detail Pesanan*:\n{items}\n\n"
        f"Pilih status pesanan di bawah ini:"
    )
    
    keyboard = get_status_keyboard(order_id)
    
    for chat_id in admin_chat_ids:
        try:
            await bot_app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except Exception as e:
            print(f"Error sending message to {chat_id}: {e}")

async def status_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("status_"):
        parts = data.split("_")
        if len(parts) == 3:
            order_id = parts[1]
            new_status = int(parts[2])
            
            # Update DB
            conn = database.get_db_connection()
            c = conn.cursor()
            c.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
            conn.commit()
            conn.close()
            
            status_map = {
                1: "Pesanan Diterima & Pembayaran Dikonfirmasi",
                2: "Sedang Dibuat Barista",
                3: "Siap Diambil",
                4: "Pesanan Selesai"
            }
            
            new_text = query.message.text + f"\n\n✅ *Status Update*: {status_map[new_status]}"
            
            try:
                # If finished, maybe remove the buttons
                if new_status == 4:
                    await query.edit_message_text(text=new_text, parse_mode='Markdown')
                else:
                    await query.edit_message_text(text=new_text, parse_mode='Markdown', reply_markup=get_status_keyboard(order_id))
            except Exception as e:
                pass # Message is not modified error if clicking the same button

async def toggle_store(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_admin(chat_id): return
    
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT setting_value FROM store_settings WHERE setting_key = 'is_open'").fetchone()
    new_val = '1' if not row or row["setting_value"] == '0' else '0'
    c.execute("INSERT OR REPLACE INTO store_settings (setting_key, setting_value) VALUES ('is_open', ?)", (new_val,))
    conn.commit()
    conn.close()
    
    status_str = "DIBUKA" if new_val == '1' else "DITUTUP"
    await update.message.reply_text(f"Pemesanan toko sekarang: *{status_str}*", parse_mode='Markdown')

async def toggle_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    args = context.args
    if not args:
        conn = database.get_db_connection()
        c = conn.cursor()
        menus = c.execute("SELECT id, name, is_available FROM menus").fetchall()
        conn.close()
        text = "Daftar Menu:\n"
        for m in menus:
            status = "✅" if m["is_available"] else "❌"
            text += f"{m['id']}. {m['name']} - {status}\n"
        text += "\nBalas dengan: `/toggle_stock <id_menu>`"
        await update.message.reply_text(text, parse_mode='Markdown')
        return
        
    menu_id = args[0]
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT name, is_available FROM menus WHERE id = ?", (menu_id,)).fetchone()
    if not row:
        await update.message.reply_text("Menu ID tidak ditemukan.")
        conn.close()
        return
        
    new_status = 0 if row["is_available"] else 1
    c.execute("UPDATE menus SET is_available = ? WHERE id = ?", (new_status, menu_id))
    conn.commit()
    conn.close()
    status_str = "Tersedia" if new_status else "Habis"
    await update.message.reply_text(f"Stok *{row['name']}* sekarang: *{status_str}*", parse_mode='Markdown')

async def manage_voucher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    args = context.args
    if len(args) == 0:
        conn = database.get_db_connection()
        c = conn.cursor()
        vs = c.execute("SELECT code, discount_amount, discount_type, is_active FROM vouchers").fetchall()
        conn.close()
        text = "Daftar Voucher:\n"
        for v in vs:
            status = "✅" if v["is_active"] else "❌"
            sym = "%" if v["discount_type"] == "percent" else "Rp"
            val = f"{v['discount_amount']}{sym}" if sym=="%" else f"{sym}{v['discount_amount']}"
            text += f"- {v['code']} ({val}) - {status}\n"
        text += "\nTambah: `/voucher add <CODE> <AMOUNT> <fixed|percent>`\nUbah status: `/voucher toggle <CODE>`"
        await update.message.reply_text(text, parse_mode='Markdown')
        return
        
    cmd = args[0].lower()
    if cmd == "add" and len(args) >= 4:
        code = args[1].upper()
        amount = int(args[2])
        dtype = args[3].lower()
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO vouchers (code, discount_amount, discount_type) VALUES (?, ?, ?)", (code, amount, dtype))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"Voucher {code} ditambahkan.")
    elif cmd == "toggle" and len(args) >= 2:
        code = args[1].upper()
        conn = database.get_db_connection()
        c = conn.cursor()
        row = c.execute("SELECT is_active FROM vouchers WHERE code = ?", (code,)).fetchone()
        if row:
            new_status = 0 if row["is_active"] else 1
            c.execute("UPDATE vouchers SET is_active = ? WHERE code = ?", (new_status, code))
            conn.commit()
            await update.message.reply_text(f"Voucher {code} {'diaktifkan' if new_status else 'dinonaktifkan'}.")
        conn.close()

async def add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    args = context.args
    # Format: /addmenu "Nama Menu" "Kategori" "Deskripsi" Harga
    if len(args) < 4:
        await update.message.reply_text('Format salah. Gunakan:\n`/addmenu "Kopi Hitam" "Kopi" "Kopi tradisional" 10000`', parse_mode='Markdown')
        return
        
    try:
        price = int(args[-1])
        # Assuming args are split correctly if user used quotes, otherwise it's hard. 
        # A simpler way is to just let them use underscores for spaces: /addmenu Kopi_Hitam Kopi Deskripsi 10000
        # But telegram handles quotes in args? No, python-telegram-bot's context.args splits by space.
        # Let's just use string parsing from the raw text
        raw = update.message.text.split(maxsplit=1)[1]
        import re
        matches = re.findall(r'"([^"]*)"', raw)
        if len(matches) == 3:
            name, cat, desc = matches
            price_str = raw.split()[-1]
            price = int(price_str)
            conn = database.get_db_connection()
            c = conn.cursor()
            c.execute("INSERT INTO menus (name, category, description, price) VALUES (?, ?, ?, ?)", (name, cat, desc, price))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"Menu '{name}' berhasil ditambahkan.")
            return
    except Exception as e:
        pass
    await update.message.reply_text('Format salah. Gunakan tanda kutip:\n`/addmenu "Kopi Hitam" "Kopi" "Kopi tradisional" 10000`', parse_mode='Markdown')

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    args = context.args
    if not args:
        await update.message.reply_text('Gunakan: `/deletemenu <id_menu>`', parse_mode='Markdown')
        return
    menu_id = args[0]
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM menus WHERE id = ?", (menu_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Menu ID {menu_id} dihapus.")

# Handlers
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("toggle_store", toggle_store))
bot_app.add_handler(CommandHandler("toggle_stock", toggle_stock))
bot_app.add_handler(CommandHandler("voucher", manage_voucher))
bot_app.add_handler(CommandHandler("addmenu", add_menu))
bot_app.add_handler(CommandHandler("deletemenu", delete_menu))
bot_app.add_handler(CallbackQueryHandler(status_button_callback))

async def run_bot_polling():
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()

# We need a way to run the bot alongside FastAPI.
# FastAPI runs in an event loop. We can start the bot polling in the same loop.
def start_bot_task():
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot_polling())

# This will be called from main.py's startup event
