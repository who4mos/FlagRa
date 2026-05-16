from datetime import timedelta
from database import db
from models import User
from dotenv import load_dotenv
import os
from flask import Flask
from flask_session import Session
import redis
from game import game
from auth import auth

def create_app():
    app = Flask(__name__)

    # this get the local secret key if a .env exists with SECRET_KEY
    load_dotenv()

    # if not on production and local secret don't exist as well load fallback str
    app.secret_key = os.environ.get("SECRET_KEY", "42069")

    # get production redis-url
    redis_url = os.environ.get('REDIS_URL')

    # set session to redis or filesystem if running local
    if redis_url:
        app.config["SESSION_TYPE"] = "redis"
        app.config['SESSION_REDIS'] = redis.from_url(redis_url)
        app.config['SESSION_KEY_PREFIX'] = "flagra:"
    else:
        app.config["SESSION_TYPE"] = "filesystem"

    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4, minutes=20)
    app.config["SESSION_USE_SIGNER"] = True

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///flagra.db"
    db.init_app(app)
    
    Session(app)

    app.register_blueprint(game)
    app.register_blueprint(auth)
    
    return app


if __name__ == "__main__":
    app = create_app()
    
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        
    app.run()
