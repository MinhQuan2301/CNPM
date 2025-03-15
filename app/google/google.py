import os.path
import pathlib
from os import abort
from google.auth.transport.requests import Request
import cachecontrol

from flask import flash, Blueprint, session, redirect, request, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow

from app.config import GOOGLE_CLIENT_ID  # Sử dụng config.GOOGLE_CLIENT_ID để đồng bộ

google = Blueprint("google", __name__)

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Đường dẫn đến file client_secret.json (không cần nếu chỉ dùng GIS)
base_path = pathlib.Path(r"C:\Users\MinhQuan\OneDrive\Desktop\Hotel\QuanLyKhachSan")
client_secrets_file = base_path / "app" / "static" / "json" / "client_secret.json"

# Tạo flow OAuth2 (bỏ nếu không dùng, vì bạn đang dùng GIS)
flow = Flow.from_client_secrets_file(
    client_secrets_file=str(client_secrets_file),
    scopes=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ],
    redirect_uri="http://127.0.0.1:5000/callback"  # Có thể xóa nếu chỉ dùng GIS
)

# Middleware yêu cầu đăng nhập
def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)  # Unauthorized
        return function(*args, **kwargs)
    return wrapper

# Route xử lý token từ Google Sign-In
@google.route('/google_signin', methods=['POST'])
def google_signin():
    token = request.json.get('token')
    try:
        # Xác minh token từ Google
        id_info = id_token.verify_oauth2_token(
            token,
            Request(),
            GOOGLE_CLIENT_ID  # Sử dụng GOOGLE_CLIENT_ID từ config
        )
        # Lưu thông tin người dùng vào session
        session['google_id'] = id_info['sub']
        session['name'] = id_info.get('name')
        session['email'] = id_info.get('email')
        session['picture'] = id_info.get('picture')
        return {'success': True}
    except ValueError as e:
        print(f"Token verification failed: {e}")
        return {'success': False}, 401

# Route xử lý đăng xuất
@google.route('/logout')
def logout():
    session.clear()
    return redirect("/")