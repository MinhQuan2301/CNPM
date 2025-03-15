from datetime import timedelta
from urllib.parse import quote

from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_admin import Admin


app = Flask(__name__)
app.config.from_object('config')

app.secret_key = "1234567890!@#$%^&*()qwertyuioplkjhgfdsazxcvbnm,./ASDFGHJKLZMXNCBVQWERTYUIOP"
app.config["SQLALCHEMY_DATABASE_URI"] = ("mysql+pymysql://root:%s@localhost/dbhotel?charset=utf8mb4"
                                         % quote("d@Ikaquan2301"))
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Hoặc thời gian phù hợp
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config["PAGE_SIZE"] = 6

db = SQLAlchemy(app)


mail = Mail(app)


admin = Admin(app, name='Quản lý Khách Sạn', template_mode='bootstrap4')

LoginManager = LoginManager(app=app)

from app.google.google import google
from app.openAI.openAI import openAI
from app.cart.routes import cart
from app.vnpays.views import vnpay
from app.user.routes import user_register
from app.staff.routes import staff


app.register_blueprint(cart)
app.register_blueprint(vnpay)
app.register_blueprint(user_register)
app.register_blueprint(staff)
app.register_blueprint(openAI)
app.register_blueprint(google)


