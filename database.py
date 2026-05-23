import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kopi_koni.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create orders table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_name TEXT,
            customer_wa TEXT,
            total_price INTEGER,
            status INTEGER DEFAULT 0,
            qris_payload TEXT,
            delivery_mode TEXT,
            delivery_floor TEXT,
            delivery_room TEXT,
            customer_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if customer_note column exists (for migrations)
    c.execute("PRAGMA table_info(orders)")
    columns = [col[1] for col in c.fetchall()]
    if "customer_note" not in columns:
        c.execute("ALTER TABLE orders ADD COLUMN customer_note TEXT")
    
    # Create order_items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT,
            menu_name TEXT,
            qty INTEGER,
            temperature TEXT,
            sweetness TEXT,
            subtotal INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')
    
    # Create store_settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS store_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE,
            setting_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create menus table
    c.execute('''
        CREATE TABLE IF NOT EXISTS menus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            description TEXT,
            price INTEGER,
            is_available BOOLEAN DEFAULT 1,
            allow_ice_hot BOOLEAN DEFAULT 1,
            allow_sweetness BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create vouchers table
    c.execute('''
        CREATE TABLE IF NOT EXISTS vouchers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            discount_amount INTEGER,
            discount_type TEXT DEFAULT 'fixed', -- 'fixed' or 'percent'
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create admin_whitelist table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_whitelist (
            telegram_chat_id TEXT PRIMARY KEY,
            admin_name TEXT,
            role TEXT DEFAULT 'admin'
        )
    ''')
    
    # Insert initial store settings
    c.execute("INSERT OR IGNORE INTO store_settings (setting_key, setting_value) VALUES ('is_open', '1')")
    
    # Check if menus are empty, then seed
    c.execute("SELECT COUNT(*) FROM menus")
    if c.fetchone()[0] == 0:
        initial_menus = [
            ("Kopi Susu Aren", "Kopi", "Espresso, susu segar, dan gula aren asli.", 15000),
            ("Americano", "Kopi", "Double shot espresso dengan air.", 12000),
            ("Cafe Latte", "Kopi", "Espresso dengan paduan susu creamy.", 18000),
            ("Matcha Latte", "Non Kopi", "Premium Uji Matcha dengan susu segar.", 20000),
            ("Chocolate", "Non Kopi", "Coklat signature yang kental dan manis.", 18000),
            ("Lychee Tea", "Non Kopi", "Teh leci segar dengan buah asli.", 15000)
        ]
        c.executemany("INSERT INTO menus (name, category, description, price) VALUES (?, ?, ?, ?)", initial_menus)
        
    # Check if vouchers are empty, then seed
    c.execute("SELECT COUNT(*) FROM vouchers")
    if c.fetchone()[0] == 0:
        initial_vouchers = [
            ("KONI10", 10, "percent"),
            ("KONI5K", 5000, "fixed")
        ]
        c.executemany("INSERT INTO vouchers (code, discount_amount, discount_type) VALUES (?, ?, ?)", initial_vouchers)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized with extended tables.")
