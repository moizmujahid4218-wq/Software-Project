import sqlite3
from config import Config
from werkzeug.security import generate_password_hash

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(Config.DATABASE)
    # This row_factory allows us to access columns by name, just like a dictionary
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the database tables if they don't exist yet."""
    conn = get_db_connection()
    
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'Staff',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            user_id INTEGER,
            total_amount REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price_at_time REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')
    
    # Automatically create the default admin user if it doesn't exist
    admin = conn.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not admin:
        hashed = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)', 
                     ('admin', hashed, 'Admin'))
                     
    # Automatically create some default categories
    cats = conn.execute('SELECT COUNT(*) FROM categories').fetchone()[0]
    if cats == 0:
        conn.executescript('''
            INSERT INTO categories (name, description) VALUES ('Cakes', 'Whole cakes and slices');
            INSERT INTO categories (name, description) VALUES ('Bread', 'Freshly baked daily breads');
            INSERT INTO categories (name, description) VALUES ('Pastries', 'Croissants, danishes, and more');
        ''')
        
    conn.commit()
    conn.close()
