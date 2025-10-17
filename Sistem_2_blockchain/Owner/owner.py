import os
import csv
import io
from decimal import Decimal, InvalidOperation
from flask import Flask, request, jsonify, g
from sqlalchemy import func, case
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
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


@app.route("/update", methods=["POST"])
def update_products():
    ok, val = auth_check(required_role="owner")
    if not ok:
        return val

    # 1) Provera da li postoji fajl
    f = request.files.get("file")
    if f is None:
        return jsonify({"message": "Field file is missing."}), 400

    # Čitamo CSV
    try:
        content = f.read().decode("utf-8")
    except Exception:
        content = ""
    rows = list(csv.reader(io.StringIO(content), delimiter=","))

    # 2) Provera broja kolona
    for idx, row in enumerate(rows):
        if len(row) != 3:
            return jsonify({"message": f"Incorrect number of values on line {idx}."}), 400

    # 3) Provera cene
    parsed = []
    for idx, (cat_str, name, price_str) in enumerate(rows):
        try:
            price = Decimal(price_str)
        except Exception:
            return jsonify({"message": f"Incorrect price on line {idx}."}), 400
        if price <= 0:
            return jsonify({"message": f"Incorrect price on line {idx}."}), 400
        categories = [c.strip() for c in (cat_str.split("|") if cat_str else []) if c.strip()]
        parsed.append((categories, name.strip(), price))
    try:
        for categories, name, price in parsed:
            current_name = name
            prod = Product(name=name, price=price)
            db.session.add(prod)
            db.session.flush()

            for cname in categories:
                cat = db.session.query(Category).filter_by(name=cname).first()
                if not cat:
                    cat = Category(name=cname)
                    db.session.add(cat)
                    db.session.flush()

                db.session.add(ProductCategory(product_id=prod.id, category_id=cat.id))
                db.session.flush()

        db.session.commit()
        return "", 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({"message": f"Product {current_name} already exists."}), 400

    return "", 200


@app.route("/product_statistics", methods=["GET"])
def product_statistics():
    ok, val = auth_check(required_role="owner")
    if not ok:
        return val

    # query sumira prodato i čekajuće po proizvodu
    # Query za statistiku proizvoda
    q = (
        db.session.query(
            Product.name,
            func.sum(
                case((Order.status == "COMPLETE", OrderProduct.quantity), else_=0)
            ).label("sold"),
            func.sum(
                case((Order.status != "COMPLETE", OrderProduct.quantity), else_=0)
            ).label("waiting"),
        )
        .join(OrderProduct)
        .join(Order)
        .group_by(Product.id)
    )

    # Pravimo listu JSON objekata i izbacujemo proizvode sa 0 količine
    stats = [
        {"name": name, "sold": int(sold or 0), "waiting": int(waiting or 0)}
        for name, sold, waiting in q.all()
        if (sold or 0) + (waiting or 0) > 0
    ]

    return jsonify({"statistics": stats}), 200



@app.route("/category_statistics", methods=["GET"])
def category_statistics():
    ok, val = auth_check(required_role="owner")
    if not ok:
        return val
    delivered = func.coalesce(
        func.sum(case((Order.status == "COMPLETE", OrderProduct.quantity), else_=0)), 0
    ).label("delivered")

    q = (
        db.session.query(Category.name, delivered)
        .outerjoin(ProductCategory, ProductCategory.category_id == Category.id)
        .outerjoin(Product, Product.id == ProductCategory.product_id)
        .outerjoin(OrderProduct, OrderProduct.product_id == Product.id)
        .outerjoin(Order, Order.id == OrderProduct.order_id)
        .group_by(Category.id)
        .order_by(delivered.desc(), Category.name.asc())
    )

    names = [name for name, _ in q.all()]
    return jsonify({"statistics": names}), 200


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5001, debug=True)
