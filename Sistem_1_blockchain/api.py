import os
from flask import Flask, request, jsonify
from ORM import User, UserRole, db
import re
from JWT import JWT
# from dotenv import load_dotenv

# load_dotenv()



app = Flask(__name__)
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_addr = os.getenv('DB_ADDR')
db_port = os.getenv('DB_PORT')
app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_user}:{db_pass}@{db_addr}/korisnici"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def valid_email(email):
    return re.match(r"^[^@]+@[^@]+\.[a-zA-Z]{2,}$" , email)

# Registracija korisnika
def validate_register(data):
    required_fields = ['forename', 'surname', 'email', 'password']
    for field in required_fields:
        if field not in data or not isinstance(data[field], str) or len(data[field]) == 0:
            return f"Field {field} is missing."
    if not valid_email(data['email']):
        return "Invalid email."
    if len(data['password']) < 8:
        return "Invalid password."
    if User.query.filter_by(email=data['email']).first():
        return "Email already exists."
    return None
def register_user(data, role):
    error = validate_register(data)
    if error:
        return jsonify({"message": error}), 400

    user = User(
        email=data['email'],
        password=data['password'],
        forename=data['forename'],
        surname=data['surname'],
        role=role
    )
    db.session.add(user)
    db.session.commit()
    return '', 200






#Login korisnika
def validate_login(data):
    required_fields = ['email', 'password']
    for field in required_fields:
        if field not in data or not isinstance(data[field], str) or len(data[field]) == 0:
            return f"Field {field} is missing."
    if not valid_email(data['email']):
        return "Invalid email."
    if not User.query.filter_by(email=data['email']).first():
        return "Invalid credentials."
    return None
def login_user(data):
    error = validate_login(data)
    if error:
        return jsonify({"message": error}), 400
    user = User.query.filter_by(email=data['email']).first()
    if not user.check_password(data['password']):
        return "Invalid credentials."
    return jsonify({"accessToken": JWT.generate_token(user)}), 200


#API's
@app.route('/register_customer', methods=['POST'])
def register_customer():
    data = request.get_json()
    return register_user(data, UserRole.customer)

@app.route('/register_courier', methods=['POST'])
def register_courier():
    data = request.get_json()
    return register_user(data, UserRole.courier)

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    return login_user(data)


@app.route('/delete', methods=['POST'])
def delete():
    # 1. Provera zaglavlja
    auth_header = request.headers.get("Authorization", "").strip()

    if not auth_header:
        return {"msg": "Missing Authorization Header"}, 401

    if not auth_header.startswith("Bearer "):
        return {"msg": "Missing Authorization Header"}, 401  # jer format nije validan

    # 2. Ekstrakcija tokena
    token = auth_header[len("Bearer "):].strip()
    try:
        email = JWT.verify_token(token)
        if not email:
            return {"message": "Unknown user."}, 400
    except Exception:
        return {"message": "Unknown user."}, 400

    # 3. Provera da li korisnik postoji
    user = User.query.filter_by(email=email).first()
    if not user:
        return {"message": "Unknown user."}, 400

    # 4. Brisanje korisnika
    db.session.delete(user)
    db.session.commit()

    # 5. Uspešan odgovor bez sadržaja
    return '', 200


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)