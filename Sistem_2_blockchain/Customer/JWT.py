import os
from datetime import datetime, timezone, timedelta
import jwt
from dotenv import load_dotenv
load_dotenv()

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
    def verify_token(token):
        try:
            payload = jwt.decode(token, JWT.SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            #print("Expired")
            return None
        except jwt.InvalidTokenError as e:
            #print("Invalid", str(e))
            return None


        return payload.get("sub")
