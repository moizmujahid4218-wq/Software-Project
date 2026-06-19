from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from config import Config
from database import get_db_connection, init_db

app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database automatically when the app starts
init_db()

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
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
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
    
    total_products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    low_stock_items = conn.execute("SELECT * FROM products WHERE stock < 10").fetchall()
    
    recent_orders = conn.execute("""
        SELECT orders.id, customers.name, orders.total_amount, orders.order_date
        FROM orders 
        LEFT JOIN customers ON orders.customer_id = customers.id
        ORDER BY orders.order_date DESC LIMIT 5
    """).fetchall()
    
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
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        category_id = request.form.get('category_id')
        if not category_id: category_id = None
        
        conn.execute("INSERT INTO products (name, price, stock, category_id) VALUES (?, ?, ?, ?)",
                     (name, price, stock, category_id))
        conn.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
        
    search_query = request.args.get('search', '')
    if search_query:
        products_list = conn.execute("""
            SELECT p.*, c.name as category_name 
            FROM products p LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.name LIKE ?
        """, ('%' + search_query + '%',)).fetchall()
    else:
        products_list = conn.execute("""
            SELECT p.*, c.name as category_name 
            FROM products p LEFT JOIN categories c ON p.category_id = c.id
        """).fetchall()
    
    categories = conn.execute("SELECT * FROM categories").fetchall()
    conn.close()
    
    return render_template('products.html', products=products_list, categories=categories, search_query=search_query)

@app.route('/products/delete/<int:id>', methods=['POST'])
def delete_product(id):
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('Product deleted!', 'info')
    return redirect(url_for('products'))

@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        conn.execute("INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)", (name, email, phone))
        conn.commit()
        flash('Customer added!', 'success')
        return redirect(url_for('customers'))
        
    customers_list = conn.execute("SELECT * FROM customers").fetchall()
    conn.close()
    
    return render_template('customers.html', customers=customers_list)

@app.route('/orders', methods=['GET', 'POST'])
def orders():
    if not is_logged_in(): return redirect(url_for('login'))
    conn = get_db_connection()
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        if not customer_id: customer_id = None
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        
        product = conn.execute("SELECT price, stock FROM products WHERE id = ?", (product_id,)).fetchone()
        
        if product and product['stock'] >= quantity:
            total_amount = product['price'] * quantity
            
            # Create order
            cursor = conn.cursor()
            cursor.execute("INSERT INTO orders (customer_id, user_id, total_amount) VALUES (?, ?, ?)",
                           (customer_id, session['user_id'], total_amount))
            order_id = cursor.lastrowid
            
            # Create order item
            conn.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_time) VALUES (?, ?, ?, ?)",
                         (order_id, product_id, quantity, product['price']))
            
            # Decrease stock
            conn.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity, product_id))
            
            conn.commit()
            flash('Order placed successfully!', 'success')
        else:
            flash('Not enough stock available!', 'danger')
            
        return redirect(url_for('orders'))
        
    orders_list = conn.execute("""
        SELECT o.id, c.name as customer, u.username as staff, o.total_amount, o.order_date 
        FROM orders o 
        LEFT JOIN customers c ON o.customer_id = c.id
        LEFT JOIN users u ON o.user_id = u.id
        ORDER BY o.order_date DESC
    """).fetchall()
    
    customers_list = conn.execute("SELECT id, name FROM customers").fetchall()
    products_list = conn.execute("SELECT id, name, price, stock FROM products WHERE stock > 0").fetchall()
    
    conn.close()
    
    return render_template('orders.html', orders=orders_list, customers=customers_list, products=products_list)

if __name__ == '__main__':
    app.run(debug=True)
