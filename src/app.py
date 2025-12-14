# app.py
from flask import Flask, jsonify, request
import pymysql
import os
import time
import traceback
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
SECRET_PATH = "/mnt/rds-secret"
DB_PORT = 3306

# Health check WITHOUT DB dependency
@app.route("/health")
def health():
    """Health check endpoint with detailed logging"""
    
    x_forwarded_for = request.headers.get('X-Forwarded-For', '')
    x_real_ip = request.headers.get('X-Real-IP', '')
    x_forwarded_proto = request.headers.get('X-Forwarded-Proto', '')
    x_forwarded_port = request.headers.get('X-Forwarded-Port', '')
    
    all_headers = dict(request.headers)
    
    # קח את ה-IP
    if x_forwarded_for:
        client_ip = x_forwarded_for.split(',')[0].strip()
    else:
        client_ip = request.remote_addr
    
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # DEBUG - הדפס את כל ה-headers פעם אחת
    logger.info(f"All headers: {all_headers}")
    logger.info(f"Health check - IP: {client_ip} | User-Agent: {user_agent}")
    
    return "OK", 200

# Only initialize DB if secrets exist
def init_with_db():
    """Initialize database connection only if secrets are available"""
    if not os.path.exists(SECRET_PATH):
        print("⚠️  Secret path not found - running without DB")
        return False
    
    try:
        wait_for_secrets()
        
        global DB_HOST, DB_USER, DB_PASS, DB_NAME
        DB_HOST = open(os.path.join(SECRET_PATH, "host")).read().strip()
        DB_USER = open(os.path.join(SECRET_PATH, "username")).read().strip()
        DB_PASS = open(os.path.join(SECRET_PATH, "password")).read().strip()
        DB_NAME = open(os.path.join(SECRET_PATH, "dbname")).read().strip()
        
        print(f"📡 Will connect to RDS: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        # Try to initialize database
        try:
            init_database()
        except Exception as init_error:
            print(f"⚠️  Database init failed (will retry on /init-db): {init_error}")
            traceback.print_exc()
            # Don't fail - just log it
        
        return True
    except Exception as e:
        print(f"⚠️  Failed to initialize DB: {e}")
        traceback.print_exc()
        return False

def wait_for_secrets(timeout=60):
    """Wait for CSI driver to mount secrets"""
    required_files = ["host", "username", "password", "dbname"]
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if all(os.path.exists(os.path.join(SECRET_PATH, f)) for f in required_files):
            print("✅ All secret files found!")
            return True
        print(f"⏳ Waiting for secrets to be mounted... ({int(time.time() - start_time)}s)")
        time.sleep(2)
    
    raise FileNotFoundError(f"Secrets not found in {SECRET_PATH} after {timeout}s")

def get_db_connection():
    """Create database connection"""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        port=DB_PORT,
        connect_timeout=10,
        read_timeout=10,
        write_timeout=10,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_database():
    """Initialize all database tables with sample data"""
    print("🔧 Initializing database schema...")
    conn = get_db_connection()
    
    try:
        with conn.cursor() as cursor:
            # 1. Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_email (email),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'users' created/verified")
            
            # 2. Products table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    stock INT DEFAULT 0,
                    category VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_category (category),
                    INDEX idx_price (price)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'products' created/verified")
            
            # 3. Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    total_amount DECIMAL(10, 2) NOT NULL,
                    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX idx_user (user_id),
                    INDEX idx_status (status),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'orders' created/verified")
            
            # 4. Order Items table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL,
                    price DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                    INDEX idx_order (order_id),
                    INDEX idx_product (product_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'order_items' created/verified")
            
            # 5. Categories table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    parent_id INT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL,
                    INDEX idx_parent (parent_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'categories' created/verified")
            
            # 6. Logs table (for tracking activities)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    action VARCHAR(100) NOT NULL,
                    description TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
                    INDEX idx_user (user_id),
                    INDEX idx_action (action),
                    INDEX idx_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✅ Table 'activity_logs' created/verified")
            
            conn.commit()
            
            # Insert sample data if tables are empty
            cursor.execute("SELECT COUNT(*) as count FROM users")
            user_count = cursor.fetchone()['count']
            
            if user_count == 0:
                print("📝 Inserting sample data...")
                insert_sample_data(conn)
    
    finally:
        conn.close()
    
    print("✅ Database initialized successfully")

def insert_sample_data(conn):
    """Insert sample data into all tables"""
    with conn.cursor() as cursor:
        # Users
        cursor.execute("""
            INSERT INTO users (name, email) VALUES 
            ('John Doe', 'john@example.com'),
            ('Jane Smith', 'jane@example.com'),
            ('Bob Wilson', 'bob@example.com'),
            ('Alice Johnson', 'alice@example.com'),
            ('Charlie Brown', 'charlie@example.com')
        """)
        
        # Categories
        cursor.execute("""
            INSERT INTO categories (name, description) VALUES 
            ('Electronics', 'Electronic devices and accessories'),
            ('Books', 'Physical and digital books'),
            ('Clothing', 'Apparel and fashion items'),
            ('Home & Garden', 'Home improvement and garden supplies'),
            ('Sports', 'Sports equipment and gear')
        """)
        
        # Products
        cursor.execute("""
            INSERT INTO products (name, description, price, stock, category) VALUES 
            ('Laptop Pro 15', 'High-performance laptop with 16GB RAM', 1299.99, 25, 'Electronics'),
            ('Wireless Mouse', 'Ergonomic wireless mouse with USB receiver', 29.99, 150, 'Electronics'),
            ('Python Programming Book', 'Complete guide to Python 3', 49.99, 80, 'Books'),
            ('Cotton T-Shirt', 'Comfortable 100% cotton t-shirt', 19.99, 200, 'Clothing'),
            ('Garden Tool Set', '10-piece garden tool set', 79.99, 45, 'Home & Garden'),
            ('Basketball', 'Official size basketball', 34.99, 60, 'Sports'),
            ('Smartphone X', 'Latest model with 5G capability', 899.99, 30, 'Electronics'),
            ('Cookbook Basics', 'Essential recipes for beginners', 24.99, 100, 'Books'),
            ('Running Shoes', 'Lightweight running shoes', 89.99, 75, 'Sports'),
            ('LED Desk Lamp', 'Adjustable LED desk lamp', 39.99, 120, 'Electronics')
        """)
        
        # Orders (sample orders for users)
        cursor.execute("""
            INSERT INTO orders (user_id, total_amount, status) VALUES 
            (1, 1329.98, 'delivered'),
            (2, 49.99, 'shipped'),
            (3, 159.97, 'processing'),
            (1, 899.99, 'pending'),
            (4, 124.98, 'delivered')
        """)
        
        # Order Items
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price) VALUES 
            (1, 1, 1, 1299.99),
            (1, 2, 1, 29.99),
            (2, 3, 1, 49.99),
            (3, 4, 5, 19.99),
            (3, 5, 1, 79.99),
            (4, 7, 1, 899.99),
            (5, 9, 1, 89.99),
            (5, 6, 1, 34.99)
        """)
        
        # Activity Logs
        cursor.execute("""
            INSERT INTO activity_logs (user_id, action, description, ip_address) VALUES 
            (1, 'login', 'User logged in successfully', '192.168.1.100'),
            (1, 'order_created', 'Created order #1', '192.168.1.100'),
            (2, 'login', 'User logged in successfully', '192.168.1.101'),
            (3, 'product_view', 'Viewed product: Cotton T-Shirt', '192.168.1.102'),
            (1, 'logout', 'User logged out', '192.168.1.100')
        """)
        
        conn.commit()
        print("✅ Sample data inserted into all tables")

# Try to initialize with DB
DB_AVAILABLE = init_with_db()

@app.route("/")
def index():
    """Show database connection status and current time"""
    if not DB_AVAILABLE:
        return jsonify({
            "status": "⚠️ Running without database",
            "message": "Secrets not mounted - DB connection not available",
            "endpoints": {
                "health": "/health",
                "info": "/info"
            }
        }), 200
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT NOW() as current_time, VERSION() as db_version")
            result = cursor.fetchone()
        conn.close()
        
        return jsonify({
            "status": "✅ Connected to RDS!",
            "db_time": str(result['current_time']),
            "db_version": result['db_version'],
            "db_host": DB_HOST,
            "db_name": DB_NAME,
            "endpoints": {
                "users": "/users",
                "products": "/products",
                "orders": "/orders",
                "categories": "/categories",
                "logs": "/logs",
                "db_info": "/db-info",
                "init_db": "/init-db"
            }
        }), 200
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return jsonify({
            "status": "❌ Database connection failed",
            "error": str(e),
            "db_host": DB_HOST if DB_AVAILABLE else "N/A"
        }), 500

@app.route("/init-db")
def init_db_endpoint():
    """Manually trigger complete database initialization"""
    if not DB_AVAILABLE:
        return jsonify({
            "status": "error",
            "error": "Database not available - secrets not mounted"
        }), 503
    
    try:
        init_database()
        
        # Get table counts
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
            
            counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                counts[table] = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": "Database initialized successfully",
            "tables_created": tables,
            "record_counts": counts
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }), 500

@app.route("/users")
def get_users():
    """Get all users"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, email, created_at FROM users ORDER BY created_at DESC")
            users = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "count": len(users),
            "users": users
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/products")
def get_products():
    """Get all products"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, description, price, stock, category, created_at 
                FROM products 
                ORDER BY created_at DESC
            """)
            products = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "count": len(products),
            "products": products
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/orders")
def get_orders():
    """Get all orders with user details"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT o.id, o.user_id, u.name as user_name, u.email as user_email,
                       o.total_amount, o.status, o.created_at
                FROM orders o
                JOIN users u ON o.user_id = u.id
                ORDER BY o.created_at DESC
            """)
            orders = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "count": len(orders),
            "orders": orders
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/categories")
def get_categories():
    """Get all categories"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, name, description, parent_id FROM categories")
            categories = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "count": len(categories),
            "categories": categories
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/logs")
def get_logs():
    """Get activity logs"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    limit = request.args.get('limit', 50, type=int)
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT l.id, l.user_id, u.name as user_name, l.action, 
                       l.description, l.ip_address, l.created_at
                FROM activity_logs l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.created_at DESC
                LIMIT {limit}
            """)
            logs = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "count": len(logs),
            "logs": logs
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/db-info")
def db_info():
    """Get detailed database information"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "error": "Database not available"}), 503
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT DATABASE() as db_name")
            db_name = cursor.fetchone()['db_name']
            
            cursor.execute("SHOW TABLES")
            tables = [list(table.values())[0] for table in cursor.fetchall()]
            
            table_info = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                table_info[table] = cursor.fetchone()['count']
        
        conn.close()
        
        return jsonify({
            "status": "success",
            "database": db_name,
            "tables": tables,
            "table_counts": table_info,
            "connection_info": {
                "host": DB_HOST,
                "port": DB_PORT,
                "user": DB_USER
            }
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Flask app...")
    if DB_AVAILABLE:
        print(f"✅ Database connection configured: {DB_USER}@{DB_HOST}/{DB_NAME}")
    else:
        print("⚠️  Running without database")
    app.run(host="0.0.0.0", port=5000, debug=True)