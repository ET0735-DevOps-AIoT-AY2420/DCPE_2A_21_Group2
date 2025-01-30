import stripe
import sqlite3
from flask import Flask, request, render_template

app = Flask(__name__)

DB_FILE = "vending_machine.db"

# Your Stripe secret key
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

# Define your DRINKS_MENU here (or fetch from DB if preferred)
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

def get_db_connection():
    return sqlite3.connect(DB_FILE)

@app.route("/")
def index():
    # Render index.html with DRINKS_MENU if you want to iterate or pass data
    return render_template("index.html", drinks=DRINKS_MENU)

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        # Parse JSON from the POST body (not request.form)
        data = request.get_json()
        item_index = int(data["item_index"])
        selected_item = DRINKS_MENU[item_index]

        # Convert item price from dollars to cents
        price_in_cents = int(selected_item["price"] * 100)

        # Create a Stripe Checkout Session for the selected item
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": selected_item["name"],
                    },
                    "unit_amount": price_in_cents,
                },
                "quantity": 1,
            }],
            mode="payment",
            # Include the item_index in the success URL so you know which item to record
            success_url=f"http://localhost:5000/success?item_index={item_index}",
            cancel_url="http://localhost:5000/cancel",
        )

        # Return JSON with the session URL
        return {"url": session.url}
    except Exception as e:
        # Return an error string if something goes wrong
        return str(e), 400

@app.route("/success")
def success():
    # Get the item_index from the query string
    item_index = request.args.get("item_index", default=0, type=int)
    selected_item = DRINKS_MENU[item_index]

    # Record the purchase in the 'sales' table
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO sales (item_id, price, source)
        VALUES (?, ?, ?)
    """, (
        item_index + 1,         # or a real DB ID if you have one
        selected_item["price"], # store the actual price
        "Stripe"
    ))

    conn.commit()
    conn.close()

    # Render a success template
    return render_template("success.html", item=selected_item)

@app.route("/cancel")
def cancel():
    return "Payment canceled"

if __name__ == "__main__":
    app.run(debug=True)
