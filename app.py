from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from database import get_db_connection

app = Flask(__name__)
app.config.from_object(Config)

# Helper function to check if user is logged in
def is_logged_in():
    return 'user_id' in session

@app.route('/', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        else:
            flash('Database connection failed. Check your setup.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not is_logged_in(): return redirect(url_for('login'))
    
    conn = get_db_connection()
    if not conn: return "Database connection error."
    
    cursor = conn.cursor(dictionary=True)
    
    # Get stats
    cursor.execute("SELECT COUNT(*) as count FROM products")
    total_products = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM orders")
    total_orders = cursor.fetchone()['count']
    
    cursor.execute("SELECT * FROM products WHERE stock < 10")
    low_stock_items = cursor.fetchall()
    
    cursor.execute("""
        SELECT orders.id, customers.name, orders.total_amount, orders.order_date
        FROM orders 
        LEFT JOIN customers ON orders.customer_id = customers.id
        ORDER BY orders.order_date DESC LIMIT 5
    """)
    recent_orders = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', 
                           total_products=total_products, 
                           total_orders=total_orders,
                           low_stock_items=low_stock_items,
                           recent_orders=recent_orders)

@app.route('/products', methods=['GET', 'POST'])
def products():
    if not is_logged_in(): return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Add a new product
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category_id = request.form.get('category_id') # Can be empty
        if not category_id: category_id = None
        
        cursor.execute("INSERT INTO products (name, price, stock, category_id) VALUES (%s, %s, %s, %s)",
                       (name, price, stock, category_id))
        conn.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
        
    # Get all products and categories for the form
    search_query = request.args.get('search', '')
    if search_query:
        cursor.execute("""
            SELECT p.*, c.name as category_name 
            FROM products p LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.name LIKE %s
        """, ('%' + search_query + '%',))
    else:
        cursor.execute("""
            SELECT p.*, c.name as category_name 
            FROM products p LEFT JOIN categories c ON p.category_id = c.id
        """)
    products_list = cursor.fetchall()
    
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('products.html', products=products_list, categories=categories, search_query=search_query)

@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Product deleted!', 'info')
    return redirect(url_for('products'))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        cursor.execute("INSERT INTO customers (name, email, phone) VALUES (%s, %s, %s)", (name, email, phone))
        conn.commit()
        flash('Customer added!', 'success')
        return redirect(url_for('customers'))
        
    cursor.execute("SELECT * FROM customers")
    customers_list = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('customers.html', customers=customers_list)

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Simple order creation for demo purposes
        customer_id = request.form['customer_id']
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        
        # 1. Get product price and check stock
        cursor.execute("SELECT price, stock FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        
        if product and product['stock'] >= quantity:
            total_amount = product['price'] * quantity
            
            # 2. Create order
            cursor.execute("INSERT INTO orders (customer_id, user_id, total_amount) VALUES (%s, %s, %s)",
                           (customer_id, session['user_id'], total_amount))
            order_id = cursor.lastrowid
            
            # 3. Create order item
            cursor.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_time) VALUES (%s, %s, %s, %s)",
                           (order_id, product_id, quantity, product['price']))
            
            # 4. Decrease stock
            cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
            
            conn.commit()
            flash('Order placed successfully!', 'success')
        else:
            flash('Not enough stock available!', 'danger')
            
        return redirect(url_for('orders'))
        
    # GET Request: Fetch orders, customers, and products
    cursor.execute("""
        SELECT o.id, c.name as customer, u.username as staff, o.total_amount, o.order_date 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN users u ON o.user_id = u.id
        ORDER BY o.order_date DESC
    """)
    orders_list = cursor.fetchall()
    
    cursor.execute("SELECT id, name FROM customers")
    customers_list = cursor.fetchall()
    
    cursor.execute("SELECT id, name, price, stock FROM products WHERE stock > 0")
    products_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('orders.html', orders=orders_list, customers=customers_list, products=products_list)

if __name__ == '__main__':
    app.run(debug=True)
