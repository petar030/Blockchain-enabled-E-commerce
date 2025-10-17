import enum
from flask_sqlalchemy import SQLAlchemy



db = SQLAlchemy()  # instanca ORM-a

class UserRole(enum.Enum):
    owner = "owner"
    customer = "customer"
    courier = "courier"

class User(db.Model):
    __tablename__ = 'users'
    idUser = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    forename = db.Column(db.String(256), nullable=False)
    surname = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False)

    def check_password(self, plain_password):
        return self.password == plain_password
