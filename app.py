# app.py - Flask Backend for FashionHub
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import uuid
from datetime import datetime
import jwt
from functools import wraps

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Supabase configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET", "fashionhub-secret-key-2023")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Admin emails (in production, you would store this in your database)
ADMIN_EMAILS = ["admin@fashionhub.com"]

# Decorator to require admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Authorization token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify the token
            decoded = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            # Check if user is admin
            if decoded.get('email') not in ADMIN_EMAILS:
                return jsonify({'error': 'Admin access required'}), 403
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

# API Routes

# Admin login
@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        # In a real app, you would verify credentials against your database
        # For simplicity, we're checking against a hardcoded list of admin emails
        if email in ADMIN_EMAILS and password == "admin123":  # Simple password for demo
            # Generate JWT token
            token = jwt.encode({
                'email': email,
                'exp': datetime.utcnow().timestamp() + 3600  # 1 hour expiration
            }, JWT_SECRET, algorithm='HS256')
            
            return jsonify({
                'message': 'Login successful',
                'token': token,
                'user': {'email': email, 'isAdmin': True}
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials or not an admin'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all products or filtered by category
@app.route('/api/products', methods=['GET'])
def get_products():
    try:
        category = request.args.get('category')
        
        if category and category != 'all':
            # Filter by category
            response = supabase.table('products').select('*').eq('category', category).execute()
        else:
            # Get all products
            response = supabase.table('products').select('*').execute()
        
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get a single product by ID
@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    try:
        response = supabase.table('products').select('*').eq('id', product_id).execute()
        
        if response.data:
            return jsonify(response.data[0]), 200
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Create a new product (Admin only)
@app.route('/api/products', methods=['POST'])
@admin_required
def create_product():
    try:
        data = request.get_json()
        
        # Generate a unique ID for the product
        product_id = str(uuid.uuid4())
        
        # Insert product into database
        response = supabase.table('products').insert({
            'id': product_id,
            'name': data['name'],
            'price': data['price'],
            'category': data['category'],
            'image_url': data['image_url'],
            'description': data['description'],
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return jsonify(response.data[0]), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Update a product (Admin only)
@app.route('/api/products/<product_id>', methods=['PUT'])
@admin_required
def update_product(product_id):
    try:
        data = request.get_json()
        
        # Update product in database
        response = supabase.table('products').update({
            'name': data['name'],
            'price': data['price'],
            'category': data['category'],
            'image_url': data['image_url'],
            'description': data['description'],
            'updated_at': datetime.now().isoformat()
        }).eq('id', product_id).execute()
        
        if response.data:
            return jsonify(response.data[0]), 200
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Delete a product (Admin only)
@app.route('/api/products/<product_id>', methods=['DELETE'])
@admin_required
def delete_product(product_id):
    try:
        response = supabase.table('products').delete().eq('id', product_id).execute()
        
        if response.data:
            return jsonify({'message': 'Product deleted successfully'}), 200
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Place an order
@app.route('/api/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        
        # Generate a unique ID for the order
        order_id = str(uuid.uuid4())
        
        # Insert order into database
        response = supabase.table('orders').insert({
            'id': order_id,
            'customer_name': data['customer_name'],
            'customer_email': data['customer_email'],
            'customer_address': data['customer_address'],
            'items': data['items'],
            'total_amount': data['total_amount'],
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }).execute()
        
        return jsonify(response.data[0]), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get all orders (Admin only)
@app.route('/api/orders', methods=['GET'])
@admin_required
def get_orders():
    try:
        response = supabase.table('orders').select('*').execute()
        return jsonify(response.data), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'message': 'FashionHub API is running'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
