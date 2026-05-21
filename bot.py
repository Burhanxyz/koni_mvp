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
    await update.message.reply_text(f"Halo {admin_name}, berhasil mendaftar sebagai Admin Kopi Koni! (Chat ID: {chat_id})\n\nKetik `/help` untuk melihat panduan lengkap perintah admin beserta format penggunaannya.", parse_mode='Markdown')

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
        text = "📋 *Daftar Menu & Stok Saat Ini* 📋\n\n"
        for m in menus:
            status = "✅ Tersedia" if m["is_available"] else "❌ Habis"
            text += f"`{m['id']}`. *{m['name']}* - {status}\n"
        text += "\n✍️ *Cara mengubah stok:* `/toggle_stock <id_menu>`"
        await update.message.reply_text(text, parse_mode='Markdown')
        return
        
    menu_id = args[0]
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT name, is_available FROM menus WHERE id = ?", (menu_id,)).fetchone()
    if not row:
        await update.message.reply_text("⚠️ Menu ID tidak ditemukan. Gunakan `/toggle_stock` untuk melihat daftar ID.")
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
        text = "🎫 *Daftar Voucher Toko* 🎫\n\n"
        for v in vs:
            status = "✅ Aktif" if v["is_active"] else "❌ Nonaktif"
            sym = "%" if v["discount_type"] == "percent" else "Rp"
            val = f"{v['discount_amount']}{sym}" if sym=="%" else f"{sym} {v['discount_amount']:,}"
            text += f"- *{v['code']}* ({val}) - {status}\n"
        text += (
            "\n✍️ *Format Tambah Voucher:*\n"
            "`/voucher add <KODE> <NILAI> <fixed|percent>`\n"
            "Contoh: `/voucher add KONI20 20 percent`\n"
            "Contoh: `/voucher add POTONGAN5K 5000 fixed`\n\n"
            "✍️ *Format Ubah Status Aktif:*\n"
            "`/voucher toggle <KODE>`\n"
            "Contoh: `/voucher toggle KONI20`"
        )
        await update.message.reply_text(text, parse_mode='Markdown')
        return
        
    cmd = args[0].lower()
    if cmd == "add" and len(args) >= 4:
        code = args[1].upper()
        try:
            amount = int(args[2])
            dtype = args[3].lower()
            if dtype not in ('fixed', 'percent'):
                await update.message.reply_text("⚠️ Jenis voucher harus `fixed` atau `percent`.")
                return
            conn = database.get_db_connection()
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO vouchers (code, discount_amount, discount_type, is_active) VALUES (?, ?, ?, 1)", (code, amount, dtype))
            conn.commit()
            conn.close()
            sym = "%" if dtype == "percent" else "Rp"
            val = f"{amount}{sym}" if sym=="%" else f"{sym} {amount:,}"
            await update.message.reply_text(f"✅ Voucher *{code}* dengan diskon *{val}* berhasil ditambahkan dan aktif!", parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("⚠️ Nilai voucher harus berupa angka.")
    elif cmd == "toggle" and len(args) >= 2:
        code = args[1].upper()
        conn = database.get_db_connection()
        c = conn.cursor()
        row = c.execute("SELECT is_active FROM vouchers WHERE code = ?", (code,)).fetchone()
        if row:
            new_status = 0 if row["is_active"] else 1
            c.execute("UPDATE vouchers SET is_active = ? WHERE code = ?", (new_status, code))
            conn.commit()
            status_str = "diaktifkan" if new_status else "dinonaktifkan"
            await update.message.reply_text(f"✅ Voucher *{code}* telah *{status_str}*.", parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Kode voucher tidak ditemukan.")
        conn.close()
    else:
        await update.message.reply_text("⚠️ Format salah. Ketik `/voucher` untuk bantuan format.")

async def add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    raw = update.message.text.strip()
    import re
    # Match pattern: /addmenu "Name" "Category" "Description" Price
    pattern = r'^\/addmenu\s+"([^"]+)"\s+(?:"([^"]+)"|(\S+))\s+"([^"]+)"\s+(\d+)$'
    match = re.match(pattern, raw)
    if not match:
        await update.message.reply_text(
            '⚠️ *Format Salah!*\n\n'
            'Gunakan format berikut:\n'
            '`/addmenu "<Nama Menu>" "<Kategori (c/nc)>" "<Deskripsi>" <Harga>`\n\n'
            '*Contoh Kopi (c):*\n'
            '`/addmenu "Espresso Avocado" "c" "Kopi espresso dengan alpukat" 18000`\n\n'
            '*Contoh Non-Kopi (nc):*\n'
            '`/addmenu "Vanilla Latte" "nc" "Susu vanilla premium" 15000`',
            parse_mode='Markdown'
        )
        return
        
    try:
        name = match.group(1)
        cat_raw = match.group(2) or match.group(3)
        desc = match.group(4)
        price = int(match.group(5))
        
        # Translate category shortcut
        cat_lower = cat_raw.lower()
        if cat_lower in ('c', 'kopi'):
            category = 'Kopi'
        elif cat_lower in ('nc', 'non-kopi', 'non kopi', 'nonkopi'):
            category = 'Non-Kopi'
        else:
            await update.message.reply_text(
                '⚠️ *Kategori tidak dikenal!*\n'
                'Gunakan `c` untuk Kopi atau `nc` untuk Non-Kopi.'
            )
            return
            
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute("INSERT INTO menus (name, category, description, price) VALUES (?, ?, ?, ?)", (name, category, desc, price))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ *Menu berhasil ditambahkan!*\n\n• Nama: {name}\n• Kategori: {category}\n• Deskripsi: {desc}\n• Harga: Rp {price:,}", parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"⚠️ Gagal menambahkan menu: {e}")

async def delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    args = context.args
    if not args:
        await update.message.reply_text('✍️ Gunakan: `/deletemenu <id_menu>`\n_Contoh: /deletemenu 5_', parse_mode='Markdown')
        return
    menu_id = args[0]
    conn = database.get_db_connection()
    c = conn.cursor()
    row = c.execute("SELECT name FROM menus WHERE id = ?", (menu_id,)).fetchone()
    if not row:
        await update.message.reply_text("⚠️ Menu ID tidak ditemukan. Gunakan `/toggle_stock` untuk melihat daftar ID.")
        conn.close()
        return
    c.execute("DELETE FROM menus WHERE id = ?", (menu_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Menu *{row['name']}* (ID: {menu_id}) berhasil dihapus.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id): return
    help_text = (
        "💡 *Panduan Perintah Bot Admin Kopi Koni* 💡\n\n"
        "Berikut adalah daftar semua fungsi manajemen toko beserta format penggunaannya:\n\n"
        "🟢 *Manajemen Toko*\n"
        "• `/toggle_store` \n"
        "  _Fungsi: Membuka atau menutup toko secara instan._\n"
        "  _Status saat ini akan langsung diubah di website pelanggan._\n\n"
        "🟢 *Manajemen Stok Menu*\n"
        "• `/toggle_stock` \n"
        "  _Fungsi: Melihat daftar menu dan mengubah ketersediaan stok._\n"
        "• `/toggle_stock <id_menu>` \n"
        "  _Fungsi: Mengubah stok menu (Tersedia ↔ Habis)._\n"
        "  _Contoh: /toggle_stock 3_\n\n"
        "🟢 *Manajemen Menu (Tambah/Hapus)*\n"
        "• `/addmenu \"<Nama Menu>\" \"<Kategori (c/nc)>\" \"<Deskripsi>\" <Harga>` \n"
        "  _Fungsi: Menambahkan menu baru ke database._\n"
        "  _Gunakan shortcut Kategori: `c` (Kopi) atau `nc` (Non-Kopi)._\n"
        "  _Contoh: /addmenu \"Espresso Avocado\" \"c\" \"Kopi espresso dengan buah alpukat segar\" 18000_\n"
        "• `/deletemenu <id_menu>` \n"
        "  _Fungsi: Menghapus menu secara permanen dari database._\n"
        "  _Contoh: /deletemenu 5_\n\n"
        "🟢 *Manajemen Voucher*\n"
        "• `/voucher` \n"
        "  _Fungsi: Melihat daftar seluruh voucher aktif._\n"
        "• `/voucher add <KODE> <NILAI> <fixed|percent>` \n"
        "  _Fungsi: Menambahkan voucher diskon baru._\n"
        "  _Contoh: /voucher add PROMO15 15 percent (Diskon 15%)_\n"
        "  _Contoh: /voucher add POTONGAN10K 10000 fixed (Potongan Rp 10.000)_\n"
        "• `/voucher toggle <KODE>` \n"
        "  _Fungsi: Mengaktifkan atau menonaktifkan voucher._\n"
        "  _Contoh: /voucher toggle POTONGAN10K_\n\n"
        "📌 _Gunakan perintah /start terlebih dahulu untuk mendaftarkan akun Telegram Anda sebagai admin._"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Handlers
bot_app.add_handler(CommandHandler("start", start_command))
bot_app.add_handler(CommandHandler("help", help_command))
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
