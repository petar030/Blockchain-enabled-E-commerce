import os
from decimal import Decimal
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, g
from sqlalchemy import func
from dotenv import load_dotenv
from blockchain import OrderContract
from ORM import db, Product, Category, ProductCategory, Order, OrderProduct
from JWT import JWT
import jwt

load_dotenv()

app = Flask(__name__)

db_user = os.getenv("DB_USER", "")
db_pass = os.getenv("DB_PASS", "")
db_addr = os.getenv("DB_ADDR", "")
db_name = "prodavnica"
DB_URI  = f"mysql+pymysql://{db_user}:{db_pass}@{db_addr}/{db_name}"

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def is_positive_int(val):
    try:
        iv = int(val)
        return iv > 0
    except Exception:
        return False
def isoformat_z(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def auth_check(required_role: str | None = None):
    """
    Vrati (True, {"email":..., "role":...}) ako je sve OK,
    inače (False, (jsonify({...}), status_code)) spremno za return iz rute.
    """
    auth_header = request.headers.get("Authorization", "").strip()
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, (jsonify({"msg": "Missing Authorization Header"}), 401)

    token = auth_header[len("Bearer "):].strip()

    email = JWT.verify_token(token)
    if not email:
        return False, (jsonify({"msg": "Missing Authorization Header"}), 401)

    try:
        payload = jwt.decode(token, JWT.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return False, (jsonify({"msg": "Missing Authorization Header"}), 401)

    role = payload.get("roles")

    if required_role and role != required_role:
        return False, (jsonify({"msg": "Missing Authorization Header"}), 401)

    return True, {"email": email, "role": role}

@app.route("/search", methods=["GET"])
def search():
    ok, val = auth_check(required_role="customer")
    if not ok:
        return val

    name_q = request.args.get("name", "", type=str)
    cat_q  = request.args.get("category", "", type=str)

    name_like = f"%{name_q}%"
    cat_like  = f"%{cat_q}%"

    # Kategorije: ime sadrži category + imaju bar jedan proizvod čije ime sadrži name
    categories_q = (
        db.session.query(Category.name)
        .join(ProductCategory, ProductCategory.category_id == Category.id)
        .join(Product, Product.id == ProductCategory.product_id)
        .filter(Category.name.ilike(cat_like))
        .filter(Product.name.ilike(name_like))
        .distinct()
        .order_by(Category.name.asc())
    )
    categories = [n for (n,) in categories_q.all()]

    # Proizvodi: ime sadrži name + pripadaju bar jednoj kategoriji čije ime sadrži category
    products_q = (
        db.session.query(Product)
        .join(ProductCategory, ProductCategory.product_id == Product.id)
        .join(Category, Category.id == ProductCategory.category_id)
        .filter(Product.name.ilike(name_like))
        .filter(Category.name.ilike(cat_like))
        .distinct()
        .order_by(Product.id.asc())
    )
    products = products_q.all()

    out_products = []
    for p in products:
        cat_names = [c.name for c in p.categories]
        cat_names.sort()
        out_products.append({
            "categories": cat_names,
            "id": p.id,
            "name": p.name,
            "price": float(p.price) if p.price is not None else 0.0
        })

    return jsonify({"categories": categories, "products": out_products}), 200


@app.route("/order", methods=["POST"])
def create_order():
    ok, val = auth_check(required_role="customer")
    if not ok:
        return val
    else:
        email = val.get("email")

    data = request.get_json(silent=True) or {}

    # 1) Field requests is missing.
    if "requests" not in data:
        return jsonify({"message": "Field requests is missing."}), 400

    requests_list = data["requests"]
    if not isinstance(requests_list, list):
        return jsonify({"message": "Field requests is missing."}), 400

    # 2) Product id is missing for request number N.
    for idx, item in enumerate(requests_list):
        if not isinstance(item, dict) or "id" not in item:
            return jsonify({"message": f"Product id is missing for request number {idx}."}), 400

    # 3) Product quantity is missing for request number N.
    for idx, item in enumerate(requests_list):
        if "quantity" not in item:
            return jsonify({"message": f"Product quantity is missing for request number {idx}."}), 400

    # 4) Invalid product id for request number N.
    for idx, item in enumerate(requests_list):
        if not is_positive_int(item.get("id")):
            return jsonify({"message": f"Invalid product id for request number {idx}."}), 400

    # 5) Invalid product quantity for request number N.
    for idx, item in enumerate(requests_list):
        if not is_positive_int(item.get("quantity")):
            return jsonify({"message": f"Invalid product quantity for request number {idx}."}), 400

    # 6) Invalid product for request number N. (ne postoji)
    product_ids = [int(x["id"]) for x in requests_list]
    existing_ids = set(pid for (pid,) in db.session.query(Product.id).filter(Product.id.in_(product_ids)).all())
    for idx, pid in enumerate(product_ids):
        if pid not in existing_ids:
            return jsonify({"message": f"Invalid product for request number {idx}."}), 400

    # 7) Field address is missing
    if "address" not in data or data["address"] == "":
        return jsonify({"message": "Field address is missing."}), 400


    # Total price
    total_price = 0
    for item in requests_list:
        product = Product.query.get(int(item["id"]))
        quantity = int(item["quantity"])
        total_price += quantity * product.price


    # 8) Trying to create contract
    contract = OrderContract.deploy(data["address"], total_price)

    if not contract["success"]:
        return jsonify({"message": contract["message"]}), 400

    # Kreiraj narudžbinu
    now = datetime.now(timezone.utc)
    order = Order(email=email, status="CREATED", timestamp=now, contract_address=contract["message"])
    db.session.add(order)
    db.session.flush()

    for item in requests_list:
        db.session.add(
            OrderProduct(
                order_id=order.id,
                product_id=int(item["id"]),
                quantity=int(item["quantity"])

            )
        )

    db.session.commit()
    return jsonify({"id": order.id}), 200


@app.route("/status", methods=["GET"])
def status():
    ok, val = auth_check(required_role="customer")
    if not ok:
        return val
    else:
        email = val.get("email")



    orders = Order.query.filter_by(email=email).order_by(Order.timestamp.asc()).all()

    out = []
    for o in orders:
        rows = (
            db.session.query(OrderProduct, Product)
            .join(Product, Product.id == OrderProduct.product_id)
            .filter(OrderProduct.order_id == o.id)
            .all()
        )

        products_json = []
        total_price = Decimal("0.00")

        for op, p in rows:
            cat_names = [c.name for c in p.categories]
            cat_names.sort()
            price = Decimal(p.price or 0)
            qty = int(op.quantity)
            total_price += price * qty

            products_json.append({
                "categories": cat_names,
                "name": p.name,
                "price": float(price),
                "quantity": qty
            })

        out.append({
            "products": products_json,
            "price": float(total_price),
            "status": o.status,
            "timestamp": isoformat_z(o.timestamp)
        })

    return jsonify({"orders": out}), 200


@app.route("/delivered", methods=["POST"])
def delivered():
    ok, val = auth_check(required_role="customer")
    if not ok:
        return val
    else:
        email = val.get("email")

    data = request.get_json(silent=True) or {}

    # 1) Missing order id.
    if "id" not in data:
        return jsonify({"message": "Missing order id."}), 400

    # 2) Invalid order id. (nije ceo broj > 0, ne postoji, ili nije PENDING)
    try:
        oid = int(data["id"])
    except Exception:
        return jsonify({"message": "Invalid order id."}), 400
    if oid <= 0:
        return jsonify({"message": "Invalid order id."}), 400

    order = Order.query.filter_by(id=oid, email=email).first()
    if not order:
        return jsonify({"message": "Invalid order id."}), 400
    if order.status != "PENDING":
        return jsonify({"message": "Delivery not complete."}), 400

    delivery = OrderContract.confirm_delivery(order.contract_address)

    if not delivery["success"]:
        return jsonify({"message": delivery["message"]}), 400


    order.status = "COMPLETE"
    db.session.commit()
    return "", 200

@app.route("/generate_invoice", methods=["POST"])
def generate_invoice():
    ok, val = auth_check(required_role="customer")
    if not ok:
        return val

    data = request.get_json(silent=True) or {}
    # 1) Missing order id.
    if "id" not in data:
        return jsonify({"message": "Missing order id."}), 400

    # 2) Invalid order id. (nije ceo broj > 0, ne postoji, ili nije PENDING)
    try:
        oid = int(data["id"])
    except Exception:
        return jsonify({"message": "Invalid order id."}), 400
    if oid <= 0:
        return jsonify({"message": "Invalid order id."}), 400
    order = Order.query.filter_by(id=oid).first()
    if not order:
        return jsonify({"message": "Invalid order id."}), 400

    # 3) Missing address
    if "address" not in data:
        return jsonify({"message": "Missing address."}), 400

    customer_address = data["address"]
    contract_address = order.contract_address

    generated = OrderContract.generate_invoice(contract_address, customer_address)
    if not generated["success"]:
        return jsonify({"message": generated["message"]}), 400

    return jsonify({"invoice": generated["message"]}), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002, debug=True)
