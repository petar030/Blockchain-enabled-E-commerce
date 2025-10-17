import os
from datetime import datetime, timezone, timedelta
from ORM import User, UserRole
import jwt
# from dotenv import load_dotenv
# load_dotenv()

class JWT:
    SECRET_KEY = os.getenv('SECRET_KEY')

    @staticmethod
    def generate_token(user):
        payload = {
            "sub": user.email,
            "forename": user.forename,
            "surname": user.surname,
            "roles": user.role.name,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "nbf": datetime.now(timezone.utc),
            "type": "access",


        }
        token = jwt.encode(payload, JWT.SECRET_KEY, algorithm="HS256")
        return token


    @staticmethod
    def verify_token(token, user=None):
        try:
            payload = jwt.decode(token, JWT.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            #print("Expired")
            return None
        except jwt.InvalidTokenError as e:
            #print("Invalid", str(e))
            return None

        # Ako je prosleđen user, proveri da li se email poklapa
        if user is not None and payload.get("sub") != user.email:
            return None

        return payload.get("sub")
