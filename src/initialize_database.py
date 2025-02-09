import sqlite3

# Define database file
DB_FILE = "vending_machine.db"

# Drinks menu data with images
DRINKS_MENU = [
    # Hot Beverages
    {"name": "Classic Coffee", "category": "Hot Beverage", "price": 2.50, "availability": True, "image": "classic_coffee.jpg"},
    {"name": "Strawberry Latte", "category": "Hot Beverage", "price": 3.00, "availability": True, "image": "strawberry_latte.jpg"},
    {"name": "Lychee Milk Tea", "category": "Hot Beverage", "price": 3.50, "availability": True, "image": "lychee_milk_tea.jpg"},
    {"name": "Mocha Strawberry Twist", "category": "Hot Beverage", "price": 4.00, "availability": True, "image": "mocha_strawberry_twist.jpg"},
    {"name": "Lime Infused Coffee", "category": "Hot Beverage", "price": 2.75, "availability": True, "image": "lime_infused_coffee.jpg"},

    # Cold Beverages
    {"name": "Iced Coffee", "category": "Cold Beverage", "price": 3.00, "availability": True, "image": "iced_coffee.jpg"},
    {"name": "Strawberry Iced Latte", "category": "Cold Beverage", "price": 3.50, "availability": True, "image": "strawberry_iced_latte.jpg"},
    {"name": "Lychee Cooler", "category": "Cold Beverage", "price": 3.75, "availability": True, "image": "lychee_cooler.jpg"},
    {"name": "Lime Lychee Refresher", "category": "Cold Beverage", "price": 3.25, "availability": True, "image": "lime_lychee_refresher.jpg"},
    {"name": "Coffee Berry Chill", "category": "Cold Beverage", "price": 4.50, "availability": True, "image": "coffee_berry_chill.jpg"},

    # Soda Mixes
    {"name": "Strawberry Soda Fizz", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "strawberry_soda_fizz.jpg"},
    {"name": "Lime Sparkle", "category": "Soda Mix", "price": 3.00, "availability": True, "image": "lime_sparkle.jpg"},
    {"name": "Lychee Lime Spritz", "category": "Soda Mix", "price": 3.50, "availability": True, "image": "lychee_lime_spritz.jpg"},
    {"name": "Coffee Soda Kick", "category": "Soda Mix", "price": 4.00, "availability": True, "image": "coffee_soda_kick.jpg"},
    {"name": "Strawberry Lychee Sparkler", "category": "Soda Mix", "price": 4.25, "availability": True, "image": "strawberry_lychee_sparkler.jpg"},

    # Smoothies
    {"name": "Strawberry Milk Smoothie", "category": "Smoothie", "price": 3.50, "availability": True, "image": "strawberry_milk_smoothie.jpg"},
    {"name": "Lychee Delight Smoothie", "category": "Smoothie", "price": 3.75, "availability": True, "image": "lychee_delight_smoothie.jpg"},
    {"name": "Tropical Lime Smoothie", "category": "Smoothie", "price": 4.00, "availability": True, "image": "tropical_lime_smoothie.jpg"},
    {"name": "Strawberry Coffee Smoothie", "category": "Smoothie", "price": 4.50, "availability": True, "image": "strawberry_coffee_smoothie.jpg"},
    {"name": "Lychee Strawberry Frost", "category": "Smoothie", "price": 4.25, "availability": True, "image": "lychee_strawberry_frost.jpg"},
]

#Inventory list with amount
INVENTORY_LIST = [
    {"inventory_name": "water", "amount": 10},
    {"inventory_name": "ice", "amount": 10},
    {"inventory_name": "milk", "amount": 10},
    {"inventory_name": "coffee", "amount": 10},
    {"inventory_name": "tea", "amount": 10},
    {"inventory_name": "strawberry", "amount": 10},
    {"inventory_name": "lime", "amount": 10},
    {"inventory_name": "lychee", "amount": 10},
    {"inventory_name": "soda", "amount": 10},
]

#Menu and Inventory
MENU_INVENTORY_MAPPING = {
    "Classic Coffee": ["water", "coffee"],
    "Strawberry Latte": ["milk", "coffee", "strawberry"],
    "Lychee Milk Tea": ["milk", "lychee", "tea"],
    "Mocha Strawberry Twist": ["water", "milk", "coffee", "strawberry"],
    "Lime Infused Coffee": ["coffee", "lime"],
    "Iced Coffee": ["water", "coffee", "ice"],
    "Strawberry Iced Latte": ["coffee", "milk", "strawberry", "ice"],
    "Lychee Cooler": ["water", "lychee", "ice"],
    "Lime Lychee Refresher": ["water", "lime", "lychee", "ice"],
    "Coffee Berry Chill": ["coffee", "strawberry", "ice"],
    "Strawberry Soda Fizz": ["soda", "strawberry"],
    "Lime Sparkle": ["soda", "lime"],
    "Lychee Lime Spritz": ["soda", "lychee", "lime"],
    "Coffee Soda Kick": ["soda", "coffee"],
    "Strawberry Lychee Sparkler": ["soda", "strawberry", "lychee"],
    "Strawberry Milk Smoothie": ["milk", "strawberry"],
    "Lychee Delight Smoothie": ["milk", "lychee"],
    "Tropical Lime Smoothie": ["milk", "lime"],
    "Strawberry Coffee Smoothie": ["milk", "strawberry", "coffee"],
    "Lychee Strawberry Frost": ["milk", "lychee", "strawberry"]
}


# Initialize the database
def initialize_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            availability BOOLEAN NOT NULL,
            image TEXT
        )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        timestamp TEXT NOT NULL,  -- Store time as Singapore Time
        FOREIGN KEY (item_id) REFERENCES menu (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,  -- Store time as Singapore Time
        price REAL NOT NULL,
        source TEXT NOT NULL,
        FOREIGN KEY (item_id) REFERENCES menu (id),
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
    )
    """)



    # Create inventory_list table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_list (
            inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_name TEXT NOT NULL,
            amount INTEGER NOT NULL
        )
    """)

    # Create menu_inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu_inventory (
            id INTEGER,
            name TEXT,
            inventory_id INTEGER,
            inventory_name TEXT,
            FOREIGN KEY(id) REFERENCES menu(id),
            FOREIGN KEY(inventory_id) REFERENCES inventory_list(inventory_id) 
        )
    """)

    # Create the admin_users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Insert admin users with password '123456'
    admins = [
        ('admin1', '123456'),
        ('admin2', '123456'),
        ('admin3', '123456'),
        ('admin4', '123456')
    ]

    cursor.executemany("""
        INSERT INTO admin_users (username, password)
        VALUES (?, ?)
    """, admins)

    # Create the admin_logs table to log admin logins
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            ip_address TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admin_users(id)
        )
    """)

    # Populate the menu table
    cursor.executemany("""
        INSERT INTO menu (name, category, price, availability, image)
        VALUES (:name, :category, :price, :availability, :image)
    """, DRINKS_MENU)

    # Populate the inventory_list table
    cursor.executemany(""" 
        INSERT INTO inventory_list(inventory_name, amount)
        VALUES (:inventory_name, :amount)
    """, INVENTORY_LIST)

    
    # Populate menu_inventory table
    for drink_name, ingredients in MENU_INVENTORY_MAPPING.items():
        cursor.execute("SELECT id FROM menu WHERE name = ?", (drink_name,))
        menu_id = cursor.fetchone()
        
        if menu_id:
            menu_id = menu_id[0]
            for ingredient in ingredients:
                cursor.execute("SELECT inventory_id FROM inventory_list WHERE inventory_name = ?", (ingredient,))
                inventory_id = cursor.fetchone()
                
                if inventory_id:
                    inventory_id = inventory_id[0]
                    cursor.execute("""
                        INSERT INTO menu_inventory (id, name, inventory_id, inventory_name)
                        VALUES (?, ?, ?, ?)
                    """, (menu_id, drink_name, inventory_id, ingredient))
    conn.commit()
    conn.close()
    print(f"Database initialized and populated with {len(DRINKS_MENU)} drinks!")
    print(f"Database initialized and populated with {len(INVENTORY_LIST)} inventories!")

# Run the script
if __name__ == "__main__":
    initialize_database()
