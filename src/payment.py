import stripe
from flask import Flask, request, render_template

app = Flask(__name__)

# Your Stripe secret key
stripe.api_key = "sk_test_51Qh9kW06aB8tsnc6hM4v2C48GHGTHJEhDr6iqSw471hz1UmloXMf3wq88Qw2vC1HzIgOEHTOlxfFPnromgpf964R00vHQZySAx"

@app.route("/")
def index():
    # This should render your main page (index.html),
    # which might have a button calling /create-checkout-session
    return render_template("index.html")

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "Vending Machine Item",
                    },
                    "unit_amount": 100,  # $1.00 in cents
                },
                "quantity": 1,
            }],
            mode="payment",
            # Redirect to /success on success, /cancel on cancel
            success_url="http://localhost:5000/success",
            cancel_url="http://localhost:5000/cancel",
        )
        return {"url": session.url}
    except Exception as e:
        # Return a string error message if something goes wrong
        return str(e)

@app.route("/success")
def success():
    # Instead of returning plain text, render the success template
    return render_template("success.html")

@app.route("/cancel")
def cancel():
    # You can return a simple message or render a cancel.html
    return "Payment canceled"

if __name__ == "__main__":
    app.run(debug=True)
