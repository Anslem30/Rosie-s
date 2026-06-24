from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import os

from sqlalchemy.dialects.oracle.dictionary import all_users
from werkzeug.security import generate_password_hash, check_password_hash

import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'your-secret-key-change-this-in-production'

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("POSTGRES_URL_NON_POOLING")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

# ==================== AUTHENTICATION DECORATORS ====================

from functools import wraps


def login_required(f):
    """Decorator to require user login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged_in'):
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('user_login', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin login"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)

    return decorated_function


# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    payment_methods = db.relationship('PaymentMethod', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class MenuItem(db.Model):
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(200))
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MenuItem {self.name}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_address = db.Column(db.Text, nullable=False)
    total = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_delivery = db.Column(db.DateTime)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)

    # Relationship
    menu_item = db.relationship('MenuItem', backref='order_items')

    def __repr__(self):
        return f'<OrderItem {self.name}>'


class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<OrderStatusHistory {self.status}>'


class PaymentMethod(db.Model):
    __tablename__ = 'payment_methods'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_type = db.Column(db.String(50), nullable=False)
    card_number = db.Column(db.String(20), nullable=False)
    card_name = db.Column(db.String(100), nullable=False)
    expiry_date = db.Column(db.String(10), nullable=False)
    added_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PaymentMethod {self.card_type}>'


# ==================== CONTEXT PROCESSOR ====================

@app.context_processor
def inject_datetime():
    return dict(datetime=datetime, timedelta=timedelta)

@app.context_processor
def inject_user():
    user = None
    if session.get('user_logged_in'):
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
    return dict(user=user)

# ==================== USER ROUTES ====================

@app.route('/')
def home():
    featured_items = MenuItem.query.filter_by(available=True).limit(4).all()
    return render_template('home.html', featured_items=featured_items)


@app.route('/menu')
def menu():
    categories = db.session.query(MenuItem.category).distinct().all()
    categories = [cat[0] for cat in categories]

    selected_category = request.args.get('category', 'all')

    if selected_category == 'all':
        filtered_items = MenuItem.query.filter_by(available=True).all()
    else:
        filtered_items = MenuItem.query.filter_by(category=selected_category, available=True).all()

    return render_template('menu.html', menu_items=filtered_items, categories=categories,
                           selected_category=selected_category)


@app.route('/cart')
def cart():
    if not session.get('user_logged_in'):
        flash('Please log in to view your cart.', 'error')
        return redirect(url_for('user_login'))

    cart_items = session.get('cart', [])
    total = sum(item['total'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))

    if 'cart' not in session:
        session['cart'] = []

    try:
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
    except (ValueError, KeyError):
        return redirect(url_for('menu'))

    item = MenuItem.query.get(item_id)
    if not item:
        return redirect(url_for('menu'))

    cart_item = {
        'id': item.id,
        'name': item.name,
        'price': item.price,
        'quantity': quantity,
        'total': item.price * quantity
    }

    existing_item = next((ci for ci in session['cart'] if ci['id'] == item_id), None)
    if existing_item:
        existing_item['quantity'] += quantity
        existing_item['total'] = existing_item['price'] * existing_item['quantity']
    else:
        session['cart'].append(cart_item)

    session.modified = True

    # ⭐ Redirect instead of returning JSON
    flash("Item added to cart!", "success")
    return redirect(url_for('menu'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    if 'cart' in session:
        quantity = int(request.form.get('quantity', 1))
        for item in session['cart']:
            if item['id'] == item_id:
                item['quantity'] = quantity
                item['total'] = item['price'] * quantity
                break
        session.modified = True
        flash('Cart updated!', 'success')
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:item_id>')
@login_required
def remove_from_cart(item_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != item_id]
        session.modified = True
        flash("Item removed from cart.", "info")
        return redirect(url_for('cart'))


@app.route('/checkout')
@login_required
def checkout():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('menu'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)
    cart_items = session.get('cart', [])
    total = sum(item['total'] for item in cart_items)

    return render_template('checkout.html', user=user, cart_items=cart_items, total=total)

@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    cart_items = session.get('cart', [])
    if not cart_items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))

    # Build Stripe line items
    line_items = []
    for item in cart_items:
        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': int(item['price'] * 100),
            },
            'quantity': item['quantity'],
        })

    # Load connected Stripe account (will be None until your sister connects)
    connected_account_id = None
    if os.path.exists("stripe_account.txt"):
        with open("stripe_account.txt", "r") as f:
            connected_account_id = f.read().strip()

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card', 'cashapp'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('payment_cancel', _external=True),
            stripe_account=connected_account_id
        )

        return redirect(checkout_session.url, code=303)

    except Exception as e:
        print("Stripe error:", e)
        flash('Payment error. Please try again.', 'error')
        return redirect(url_for('checkout'))


@app.route('/order/place', methods=['POST'])
@login_required
def place_order():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('menu'))

    customer_name = request.form.get('customer_name', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()
    customer_address = request.form.get('customer_address', '').strip()
    payment_method = request.form.get('payment_method', 'cash')

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if user:
        customer_name = customer_name or user.full_name
        customer_phone = customer_phone or user.phone
        customer_address = customer_address or user.address

    if not all([customer_name, customer_phone, customer_address]):
        flash('Please fill in all required fields!', 'error')
        return redirect(url_for('checkout'))

    # Create order
    order = Order(
        user_id=user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        total=sum(item['total'] for item in session['cart']),
        payment_method=payment_method,
        status='Pending',
        estimated_delivery=datetime.now() + timedelta(minutes=45)
    )

    db.session.add(order)
    db.session.flush()  # Get the order ID

    # Add order items
    for item in session['cart']:
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item['id'],
            name=item['name'],
            price=item['price'],
            quantity=item['quantity'],
            total=item['total']
        )
        db.session.add(order_item)

    # Add status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        status='Pending'
    )
    db.session.add(status_history)

    db.session.commit()

    # Clear cart
    session['cart'] = []
    session.modified = True

    flash(f'Order #{order.id} placed successfully!', 'success')
    return redirect(url_for('order_confirmation', order_id=order.id))


@app.route('/order/confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order_confirmation.html', order=order)


@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_logged_in'] = True
            session['username'] = username
            session['user_id'] = user.id
            flash('Login successful!', 'success')

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials!', 'error')

    return render_template('user_login.html')


@app.route('/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        if not all([username, email, password, full_name, phone, address]):
            flash('Please fill in all required fields!', 'error')
            return render_template('user_register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return render_template('user_register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already exists!', 'error')
            return render_template('user_register.html')

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            full_name=full_name,
            phone=phone,
            address=address
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('user_login'))

    return render_template('user_register.html')


@app.route('/logout')
def user_logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
def user_dashboard():
    # First check: user must be logged in
    if not session.get('user_logged_in'):
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('user_login'))

    # Second check: user_id must exist
    user_id = session.get('user_id')
    if not user_id:
        session.clear()
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('user_login'))

    # Third check: user must exist in DB
    user = User.query.get(user_id)
    if not user:
        session.clear()
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('user_login'))

    # If all good → load dashboard
    user_orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()

    total_orders = len(user_orders)
    total_spent = sum(order.total for order in user_orders)
    pending_orders = sum(1 for order in user_orders if order.status in ['Pending', 'Preparing'])

    menu_items = MenuItem.query.filter_by(available=True).all()

    return render_template(
        'user_dashboard.html',
        user=user,
        recent_orders=user_orders[:5],
        total_orders=total_orders,
        total_spent=total_spent,
        pending_orders=pending_orders,
        menu_items=menu_items
    )



@app.route('/profile', methods=['GET', 'POST'])
def user_profile():
    if not session.get('user_logged_in'):
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('user_login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        user.full_name = request.form.get('full_name', '').strip()
        user.email = request.form.get('email', '').strip()
        user.phone = request.form.get('phone', '').strip()
        user.address = request.form.get('address', '').strip()

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('user_profile'))

    return render_template('user_profile.html', user=user)


@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # 1) Find user by email
        user = User.query.filter_by(email=email).first()
        if not user:
            flash('User not found with that email!', 'error')
            return render_template('change_password.html')

        # 2) Check current password
        if not check_password_hash(user.password, current_password):
            flash('Current password is incorrect!', 'error')
            return render_template('change_password.html')

        # 3) Check new password match
        if new_password != confirm_password:
            flash('New passwords do not match!', 'error')
            return render_template('change_password.html')

        # 4) Check length
        if len(new_password) < 6:
            flash('New password must be at least 6 characters long!', 'error')
            return render_template('change_password.html')

        # 5) Ensure different from current
        if check_password_hash(user.password, new_password):
            flash('New password must be different from the current password!', 'error')
            return render_template('change_password.html')

        # 6) Update password
        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash('Password changed successfully! You can now log in.', 'success')
        return redirect(url_for('user_login'))

    return render_template('change_password.html')


@app.route('/payment-methods', methods=['GET', 'POST'])
def payment_methods():
    if not session.get('user_logged_in'):
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('user_login'))

    user_id = session.get('user_id')
    user = User.query.get(user_id)

    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('user_login'))

    if request.method == 'POST':
        card_type = request.form.get('card_type', '')
        card_number = request.form.get('card_number', '')
        card_name = request.form.get('card_name', '')
        expiry_date = request.form.get('expiry_date', '')

        if all([card_type, card_number, card_name, expiry_date]):
            payment_method = PaymentMethod(
                user_id=user_id,
                card_type=card_type,
                card_number='**** **** **** ' + card_number[-4:],
                card_name=card_name,
                expiry_date=expiry_date
            )
            db.session.add(payment_method)
            db.session.commit()
            flash('Payment method added successfully!', 'success')
        else:
            flash('Please fill in all fields!', 'error')

        return redirect(url_for('payment_methods'))

    payment_methods_list = PaymentMethod.query.filter_by(user_id=user_id).all()
    return render_template('payment_methods.html', user=user, payment_methods=payment_methods_list)


@app.route('/payment-methods/delete/<int:method_id>')
def delete_payment_method(method_id):
    if not session.get('user_logged_in'):
        return redirect(url_for('user_login'))

    user_id = session.get('user_id')
    payment_method = PaymentMethod.query.filter_by(id=method_id, user_id=user_id).first()

    if payment_method:
        db.session.delete(payment_method)
        db.session.commit()
        flash('Payment method removed!', 'info')

    return redirect(url_for('payment_methods'))


@app.route('/track-order/<int:order_id>')
def track_order(order_id):
    order = Order.query.get_or_404(order_id)

    if session.get('user_logged_in'):
        user_id = session.get('user_id')
        if order.user_id != user_id:
            flash('You can only track your own orders.', 'error')
            return redirect(url_for('user_dashboard'))

    return render_template('track_order.html', order=order)


@app.route('/my-orders')
def my_orders():
    if not session.get('user_logged_in'):
        flash('Please log in to view your orders.', 'error')
        return redirect(url_for('user_login'))

    user_id = session.get('user_id')
    user_orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()

    return render_template('my_orders.html', orders=user_orders)

@app.route('/payment/success')
@login_required
def payment_success():
    session['cart'] = []
    session.modified = True
    flash('Payment successful! Your order has been placed.', 'success')
    return redirect(url_for('user_dashboard'))


@app.route('/payment/cancel')
@login_required
def payment_cancel():
    flash('Payment cancelled.', 'info')
    return redirect(url_for('checkout'))

@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime("%b %d, %Y %I:%M %p")



# ==================== ADMIN ROUTES ====================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'error')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Admin logged out successfully!', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Load orders and users
    all_orders = Order.query.order_by(Order.created_at.desc()).all()
    all_users = User.query.order_by(User.created_at.desc()).all()

    total_orders = len(all_orders)
    total_revenue = sum(order.total for order in all_orders)
    pending_orders = sum(1 for order in all_orders if order.status == 'Pending')
    completed_orders = sum(1 for order in all_orders if order.status == 'Delivered')

    recent_orders = all_orders[:10]

    # ⭐ Load Stripe connection status
    stripe_connected = None
    try:
        if os.path.exists("stripe_account.txt"):
            with open("stripe_account.txt", "r") as f:
                stripe_connected = f.read().strip()
    except:
        pass

    return render_template(
        'admin_dashboard.html',
        orders=recent_orders,
        users=all_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        stripe_connected=stripe_connected  # ⭐ Pass to template
    )


@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    status_filter = request.args.get('status', 'all')

    if status_filter == 'all':
        filtered_orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        filtered_orders = Order.query.filter_by(status=status_filter).order_by(Order.created_at.desc()).all()

    return render_template('admin_orders.html', orders=filtered_orders, status_filter=status_filter)


@app.route('/admin/update_order_status/<int:order_id>/<status>')
def update_order_status(order_id, status):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    order = Order.query.get(order_id)
    if order:
        order.status = status

        # Add to status history
        status_history = OrderStatusHistory(
            order_id=order_id,
            status=status
        )
        db.session.add(status_history)
        db.session.commit()

        flash(f'Order #{order_id} status updated to {status}!', 'success')

    return redirect(request.referrer or url_for('admin_dashboard'))


@app.route('/admin/menu', methods=['GET', 'POST'])
def admin_menu():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = float(request.form.get('price', 0))
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()

        if name and price and category:
            new_item = MenuItem(
                name=name,
                price=price,
                category=category,
                description=description,
                image='default.jpg'
            )
            db.session.add(new_item)
            db.session.commit()
            flash('Menu item added successfully!', 'success')
        else:
            flash('Please fill in all required fields!', 'error')

        return redirect(url_for('admin_menu'))

    all_menu_items = MenuItem.query.all()
    return render_template('admin_menu.html', menu_items=all_menu_items)


@app.route('/admin/menu/delete/<int:item_id>')
def admin_delete_menu_item(item_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    item = MenuItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        flash('Menu item deleted!', 'info')

    return redirect(url_for('admin_menu'))


@app.route('/admin/users')
def admin_users():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    all_users = User.query.all()
    return render_template('admin_users.html', users=all_users)

@app.route('/admin/stripe/connect')
def stripe_connect():
    client_id = os.environ.get("STRIPE_CLIENT_ID")
    return redirect(
        f"https://connect.stripe.com/oauth/authorize?response_type=code&client_id={client_id}&scope=read_write"
    )

@app.route('/admin/stripe/callback')
def stripe_callback():
    code = request.args.get('code')

    try:
        response = stripe.OAuth.token(
            grant_type='authorization_code',
            code=code
        )

        connected_account_id = response['stripe_user_id']

        # Save to file
        with open("stripe_account.txt", "w") as f:
            f.write(connected_account_id)

        flash("Stripe account connected successfully!", "success")
    except Exception as e:
        print("Stripe error:", e)
        flash("Stripe connection failed.", "error")

    return redirect(url_for('admin_dashboard'))


# ==================== RUN APPLICATION ====================

if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')

    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=5000, debug=True)
