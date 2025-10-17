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

from blockchain import OrderContract

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


@app.route("/orders_to_deliver", methods=["GET"])
def orders_to_deliver():
    ok, val = auth_check(required_role="courier")
    if not ok:
        return val

    q = (
        db.session.query(
            Order.id, Order.email
        ).filter(Order.status == "CREATED").order_by(Order.id)
    )

    orders = []
    for id, email in q.all():
        orders.append({"id": id, "email": email})

    return jsonify({"orders": orders}), 200





    return "", 200


@app.route("/pick_up_order", methods=["POST"])
def pick_up_order():
    ok, val = auth_check(required_role="courier")
    if not ok:
        return val
    data = request.get_json(silent=True) or {}

    #Ukoliko zaglavlje ne postoji
    if "id" not in data:
        return jsonify({"message": "Missing order id."}), 400

    #Ukoliko nije pozitivan ceo broj
    order_id = data["id"]
    if not is_positive_int(order_id):
        return jsonify({"message": "Invalid order id."}), 400

    #Ukoliko u bazi ne postoji porudzbina sa ovim id-jem koja je statusa "CREATED"
    order = db.session.get(Order, order_id)
    if not order or order.status != "CREATED":
        return jsonify({"message": "Invalid order id."}), 400

    #Ukoliko nedostaje polje address
    if "address" not in data or data["address"] == "":
        return jsonify({"message": "Missing address."}), 400

    #Dodeljujemo kurira pametnom ugovoru
    assigned = OrderContract.assign_courier(order.contract_address, data["address"])
    if not assigned["success"]:
        return jsonify({"message": assigned["message"]}), 400

    #Radimo update statusa u bazi na "PENDING"
    order.status = "PENDING"
    db.session.commit()

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5003, debug=True)
