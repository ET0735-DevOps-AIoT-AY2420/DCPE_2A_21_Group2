import sqlite3
from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

# Database file
DB_FILE = "vending_machine.db"

# Paths
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
IMAGES_DIR = "images"

# Load HTML Template
def load_template():
    with open(os.path.join(TEMPLATES_DIR, "menu.html"), "r") as file:
        return file.read()

def fetch_menu():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, availability, image FROM menu")
    menu = cursor.fetchall()
    conn.close()
    print(menu)  # Add this to debug
    return menu

# Generate HTML content for menu items
def generate_menu_html():
    menu = fetch_menu()
    menu_items = ""
    for item_id, name, price, availability, image in menu:  # Corrected to unpack 5 values
        status_class = "out-of-stock" if not availability else ""
        image_path = f"/images/{image}" if image else "/images/default.jpg"
        menu_items += f"""
        <div class="card {status_class}">
            <img src="{image_path}" alt="{name}">
            <div><b>#{item_id}</b> {name}</div> <!-- Include drink number -->
            <div class="price">${price:.2f}</div>
            {"<div>Out of Stock</div>" if not availability else ""}
        </div>
        """
    return menu_items

# Custom HTTP request handler
class MenuHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/menu":
            html_template = load_template()
            menu_html = generate_menu_html()
            html_content = html_template.replace("{menu_items}", menu_html)
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))
        elif self.path.startswith("/static/") or self.path.startswith("/images/"):
            self.path = self.path.lstrip("/")
            super().do_GET()
        else:
            self.send_error(404, "Page Not Found")

# Start the HTTP server
def run_server(port=8000):
    server_address = ("", port)
    httpd = HTTPServer(server_address, MenuHTTPRequestHandler)
    print(f"Local HTTP server running on http://localhost:{port}/menu")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
