import redis
from flask_mail import Mail

from app import app

VNPAY_RETURN_URL = 'http://localhost:5000/payment_return'
VNPAY_PAYMENT_URL = 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html'
VNPAY_API_URL = 'https://sandbox.vnpayment.vn/merchant_webapi/api/transaction'
VNPAY_TMN_CODE = 'BNWQLPVT'
VNPAY_HASH_SECRET_KEY = '6ESWLVXRTFVWAJZC0PEP54R3SLHUL9B0'

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)
MAIL_DEFAULT_SENDER = "quantran.23012003@gmail.com"
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_DEBUG = False
MAIL_USERNAME = "quantran.23012003@gmail.com"
MAIL_PASSWORD = "pvvn zrsq uabb iefp"

GEMINI_API_KEY="AIzaSyAFcnjvOHw6tuH4WTuvwgNL2lgAhD1K6ls"
GOOGLE_CLIENT_ID="1082030793432-avmt55u1uepplcjvarn8veap8a8a13ed.apps.googleusercontent.com"


