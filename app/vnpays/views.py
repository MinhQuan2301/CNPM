import hashlib
import hmac
import json
import random

from flask_mail import Mail, Message
import requests
from datetime import datetime
from django.http import JsonResponse
from flask import Blueprint, request, redirect, render_template, session, flash, url_for
from flask_login import login_required, current_user
from app import config, db, app, mail
from app.config import redis_client
from app.models import Booking, BookingDetail, User, Room

from app.vnpays.forms import PaymentForm
from app.vnpays.vnpay import vnpay_order

vnpay = Blueprint("vnpay", __name__)



def hmacsha512(key, data):
    byteKey = key.encode('utf-8')
    byteData = data.encode('utf-8')
    return hmac.new(byteKey, byteData, hashlib.sha512).hexdigest()


@vnpay.route('/vnpay', methods=['GET', 'POST'])
def payment():
    # Kiểm tra đăng nhập từ hệ thống hoặc Google
    is_authenticated_system = current_user.is_authenticated
    is_authenticated_google = session.get("google_id") is not None

    if not (is_authenticated_system or is_authenticated_google):
        flash("Bạn cần đăng nhập để thanh toán.", "warning")
        return redirect(url_for('login_user'))

    # Debug session để kiểm tra
    print("Session data in payment:", session)

    if request.method == 'POST':
        form = PaymentForm(request.form)
        if form.validate_on_submit():
            # Lấy dữ liệu từ session
            user_id = session.get('payment_user_id')
            order_id = session.get('order_id')
            total_amount = session.get('total_amount')

            if not all([user_id, order_id, total_amount]):
                flash("Thông tin thanh toán không hợp lệ!", "error")
                return redirect(url_for('login_user'))

            # Lấy dữ liệu từ form
            order_type = form.order_type.data.strip()
            amount = int(total_amount)  # Sử dụng total_amount từ session
            order_desc = form.order_desc.data.strip()
            bank_code = form.bank_code.data.strip() if form.bank_code.data else ''
            language = form.language.data.strip() if form.language.data else 'vn'
            ipaddr = request.remote_addr

            # Log thông tin
            print("Form Data:")
            print(f"order_type: {order_type}")
            print(f"order_id: {order_id}")
            print(f"amount: {amount}")
            print(f"order_desc: {order_desc}")
            print(f"bank_code: {bank_code}")
            print(f"language: {language}")
            print(f"ipaddr: {ipaddr}")
            print(f"user_id: {user_id}")  # Debug user_id

            # Khởi tạo thanh toán VNPay
            vnp = vnpay_order()

            # Set các tham số bắt buộc
            vnp.requestData = {
                'vnp_Version': '2.1.0',
                'vnp_Command': 'pay',
                'vnp_TmnCode': config.VNPAY_TMN_CODE.strip(),
                'vnp_Amount': str(amount * 100),
                'vnp_CreateDate': datetime.now().strftime('%Y%m%d%H%M%S'),
                'vnp_CurrCode': 'VND',
                'vnp_IpAddr': ipaddr,
                'vnp_Locale': language,
                'vnp_OrderInfo': order_desc,
                'vnp_OrderType': order_type,
                'vnp_ReturnUrl': config.VNPAY_RETURN_URL.strip(),
                'vnp_TxnRef': order_id
            }

            # Thêm bank_code nếu có
            if bank_code:
                vnp.requestData['vnp_BankCode'] = bank_code

            # Tạo URL thanh toán
            payment_url = vnp.get_payment_url(
                config.VNPAY_PAYMENT_URL.strip(),
                config.VNPAY_HASH_SECRET_KEY.strip()
            )

            print("Payment URL:", payment_url)
            return redirect(payment_url)

        else:
            print("Form input not validate")
    return render_template("payment.html", title="Thanh toán")


def payment_ipn():
    inputData = request.GET
    if inputData:
        vnp = vnpay_order()
        vnp.responseData = inputData.dict()
        order_id = inputData['vnp_TxnRef']
        amount = inputData['vnp_Amount']
        order_desc = inputData['vnp_OrderInfo']
        vnp_TransactionNo = inputData['vnp_TransactionNo']
        vnp_ResponseCode = inputData['vnp_ResponseCode']
        vnp_TmnCode = inputData['vnp_TmnCode']
        vnp_PayDate = inputData['vnp_PayDate']
        vnp_BankCode = inputData['vnp_BankCode']
        vnp_CardType = inputData['vnp_CardType']
        if vnp.validate_response(config.VNPAY_HASH_SECRET_KEY):
            # Check & Update Order Status in your Database
            # Your code here
            firstTimeUpdate = True
            totalamount = True
            if totalamount:
                if firstTimeUpdate:
                    if vnp_ResponseCode == '00':
                        print('Payment Success. Your code implement here')
                    else:
                        print('Payment Error. Your code implement here')

                    # Return VNPAY: Merchant update success
                    result = JsonResponse({'RspCode': '00', 'Message': 'Confirm Success'})
                else:
                    # Already Update
                    result = JsonResponse({'RspCode': '02', 'Message': 'Order Already Update'})
            else:
                # invalid amount
                result = JsonResponse({'RspCode': '04', 'Message': 'invalid amount'})
        else:
            # Invalid Signature
            result = JsonResponse({'RspCode': '97', 'Message': 'Invalid Signature'})
    else:
        result = JsonResponse({'RspCode': '99', 'Message': 'Invalid request'})

    return result


@vnpay.route("/payment_return", methods=["GET"])
def payment_return():
    # Kiểm tra đăng nhập từ hệ thống hoặc Google
    is_authenticated_system = current_user.is_authenticated
    is_authenticated_google = session.get("google_id") is not None

    if not (is_authenticated_system or is_authenticated_google):
        flash("Bạn cần đăng nhập để xem kết quả thanh toán.", "warning")
        return redirect(url_for('login_user'))

    # Debug session để kiểm tra
    print("Session data in payment_return:", session)

    try:
        inputData = request.args
        if not inputData:
            return render_template("payment_return.html",
                                   title="Kết quả thanh toán",
                                   result="Lỗi",
                                   msg="Không nhận được dữ liệu thanh toán")

        # Lấy thông tin từ inputData
        vnp = vnpay_order()
        vnp.responseData = inputData.to_dict()
        order_id = inputData.get('vnp_TxnRef')
        amount = int(inputData.get('vnp_Amount', 0)) / 100
        order_desc = inputData.get('vnp_OrderInfo')
        vnp_TransactionNo = inputData.get('vnp_TransactionNo')
        vnp_ResponseCode = inputData.get('vnp_ResponseCode')
        vnp_TmnCode = inputData.get('vnp_TmnCode')
        vnp_PayDate = inputData.get('vnp_PayDate')
        vnp_BankCode = inputData.get('vnp_BankCode')
        vnp_CardType = inputData.get('vnp_CardType')

        # Tìm kiếm trong Redis với order_id
        all_keys = redis_client.keys("booking_data:*")
        booking_data_json = None
        user_id = None

        for key in all_keys:
            data = redis_client.get(key)
            if data:
                data_dict = json.loads(data)
                if str(data_dict.get('order_id')) == str(order_id):
                    booking_data_json = data
                    user_id = key.split(':')[1]
                    break

        if not booking_data_json:
            return render_template("payment_return.html",
                                   title="Kết quả thanh toán",
                                   result="Lỗi",
                                   msg="Không tìm thấy thông tin đặt phòng hoặc phiên đặt phòng đã hết hạn")

        booking_data = json.loads(booking_data_json)
        print(f"Booking data found for user_id: {user_id}, order_id: {order_id}")

        if vnp.validate_response(config.VNPAY_HASH_SECRET_KEY):
            if vnp_ResponseCode == "00":
                try:
                    # Kiểm tra user_id từ booking_data để xử lý cho cả hệ thống và Google
                    if user_id.startswith('google_'):
                        # Xử lý tài khoản Google
                        google_id = user_id.replace('google_', '')
                        # Kiểm tra session để đảm bảo tài khoản Google còn hợp lệ
                        if not session.get("google_id") or session.get("google_id") != google_id:
                            flash("Phiên đăng nhập Google không hợp lệ hoặc đã hết hạn.", "error")
                            return redirect(url_for('login_user'))
                        # Giả sử bạn không cần tìm User trong DB cho Google, chỉ cần sử dụng thông tin từ session
                        user_email = booking_data.get('email') or booking_data.get('fullname')
                    else:
                        # Xử lý tài khoản hệ thống
                        user = User.query.get(int(user_id))
                        if user:
                            user_email = user.email or booking_data.get('email') or booking_data.get('fullname')
                        else:
                            user_email = booking_data.get('email') or booking_data.get('fullname')

                    # Tạo booking mới
                    new_booking = Booking(
                        check_in_date=datetime.strptime(booking_data['checkin'], '%Y-%m-%d').date(),
                        check_out_date=datetime.strptime(booking_data['checkout'], '%Y-%m-%d').date(),
                        check_in_time=datetime.now().time(),
                        customer_stype=booking_data['guestType'],
                        user_id=int(user_id) if not user_id.startswith('google_') else None,
                        # Chỉ lưu user_id cho hệ thống
                        payment_method_id=1,  # ID của VNPAY
                        style_id=1  # ID của Phiếu đặt phòng
                    )

                    db.session.add(new_booking)
                    db.session.flush()  # Để lấy new_booking.id

                    if not user_id.startswith('google_'):
                        try:
                            user = User.query.get(int(user_id))
                            if user:
                                # Lấy dữ liệu từ booking_data
                                citizen_id = booking_data.get('cccd')
                                address_value = booking_data.get('address')

                                # Cập nhật CCCD nếu tồn tại
                                if citizen_id:
                                    user.citizen_id = citizen_id

                                # Cập nhật địa chỉ nếu tồn tại
                                if address_value:
                                    user.address = address_value

                                # Lưu thay đổi vào cơ sở dữ liệu
                                db.session.commit()
                                print("Cập nhật thông tin người dùng thành công.")
                            else:
                                print(f"Không tìm thấy user với ID: {user_id}")
                        except Exception as e:
                            db.session.rollback()  # Rollback nếu có lỗi
                            print(f"Lỗi khi cập nhật thông tin người dùng: {str(e)}")

                    # Tạo booking detail cho từng phòng
                    for room in booking_data['rooms']:
                        booking_detail = BookingDetail(
                            quantity_customer=1,
                            total_amount=room['price'],
                            booking_id=new_booking.id,
                            room_id=room['id'],
                            status=True
                        )
                        db.session.add(booking_detail)
                        room_to_update = Room.query.get(room['id'])
                        if room_to_update:
                            room_to_update.status = True
                            db.session.add(room_to_update)
                    db.session.commit()

                    if user_email:
                        try:
                            msg = Message(
                                subject="Xác nhận đặt phòng thành công",
                                sender=app.config['MAIL_USERNAME'],
                                recipients=[user_email]
                            )
                            msg.html = f'''
                                            <div style="text-align: center;">
                                                <h3>Bạn đã đặt phòng thành công!</h3>
                                                <p>Mã đặt phòng của bạn là: #{new_booking.id}</p>
                                            </div>
                                            '''
                            mail.send(msg)
                            print("Email xác nhận đã được gửi thành công.")
                        except Exception as e:
                            print("Gửi email thất bại:", e)

                    # Xóa dữ liệu Redis và session
                    redis_client.delete(f"booking_data:{user_id}")
                    session.pop('payment_user_id', None)
                    session.pop('order_id', None)
                    session.pop('total_amount', None)
                    session.pop('cart', None)

                    return render_template("payment_return.html",
                                           title="Kết quả thanh toán",
                                           result="Thành công",
                                           order_id=order_id,
                                           amount=amount,
                                           order_desc=order_desc,
                                           vnp_TransactionNo=vnp_TransactionNo,
                                           vnp_ResponseCode=vnp_ResponseCode)

                except Exception as e:
                    db.session.rollback()
                    print("Lỗi khi lưu thông tin đặt phòng:", str(e))
                    return render_template("payment_return.html",
                                           title="Kết quả thanh toán",
                                           result="Lỗi",
                                           order_id=order_id,
                                           amount=amount,
                                           order_desc=order_desc,
                                           vnp_TransactionNo=vnp_TransactionNo,
                                           vnp_ResponseCode=vnp_ResponseCode,
                                           msg=f"Lỗi khi lưu thông tin đặt phòng: {str(e)}")
            else:
                print("Giao dịch không thành công. Response Code:", vnp_ResponseCode)
                return render_template("payment_return.html",
                                       title="Kết quả thanh toán",
                                       result="Lỗi",
                                       order_id=order_id,
                                       amount=amount,
                                       order_desc=order_desc,
                                       vnp_TransactionNo=vnp_TransactionNo,
                                       vnp_ResponseCode=vnp_ResponseCode,
                                       msg="Giao dịch không thành công")
        else:
            return render_template("payment_return.html",
                                   title="Kết quả thanh toán",
                                   result="Lỗi",
                                   msg="Chữ ký không hợp lệ")

    except Exception as e:
        print("Lỗi không xác định:", str(e))
        return render_template("payment_return.html",
                               title="Kết quả thanh toán",
                               result="Lỗi",
                               msg="Đã xảy ra lỗi trong quá trình xử lý")



def get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)

n = random.randint(10**11, 10**12 - 1)
n_str = str(n)
while len(n_str) < 12:
    n_str = '0' + n_str


def query():
    if request.method == 'GET':
        return render_template(request, "query.html", title="Kiểm tra kết quả giao dịch")

    url = config.VNPAY_API_URL
    secret_key = config.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = config.VNPAY_TMN_CODE
    vnp_Version = '2.1.0'

    vnp_RequestId = n_str
    vnp_Command = 'querydr'
    vnp_TxnRef = request.POST['order_id']
    vnp_OrderInfo = 'kiem tra gd'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_IpAddr = request.remote_addr

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode,
        vnp_TxnRef, vnp_TransactionDate, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render_template(request, "query.html", title="Kiểm tra kết quả giao dịch", response_json= response_json)

def refund():
    if request.method == 'GET':
        return render_template(request, "refund.html", title="Hoàn tiền giao dịch")

    url = config.VNPAY_API_URL
    secret_key = config.VNPAY_HASH_SECRET_KEY
    vnp_TmnCode = config.VNPAY_TMN_CODE
    vnp_RequestId = n_str
    vnp_Version = '2.1.0'
    vnp_Command = 'refund'
    vnp_TransactionType = request.POST['TransactionType']
    vnp_TxnRef = request.POST['order_id']
    vnp_Amount = request.POST['amount']
    vnp_OrderInfo = request.POST['order_desc']
    vnp_TransactionNo = '0'
    vnp_TransactionDate = request.POST['trans_date']
    vnp_CreateDate = datetime.now().strftime('%Y%m%d%H%M%S')
    vnp_CreateBy = 'user01'
    vnp_IpAddr = request.remote_addr

    hash_data = "|".join([
        vnp_RequestId, vnp_Version, vnp_Command, vnp_TmnCode, vnp_TransactionType, vnp_TxnRef,
        vnp_Amount, vnp_TransactionNo, vnp_TransactionDate, vnp_CreateBy, vnp_CreateDate,
        vnp_IpAddr, vnp_OrderInfo
    ])

    secure_hash = hmac.new(secret_key.encode(), hash_data.encode(), hashlib.sha512).hexdigest()

    data = {
        "vnp_RequestId": vnp_RequestId,
        "vnp_TmnCode": vnp_TmnCode,
        "vnp_Command": vnp_Command,
        "vnp_TxnRef": vnp_TxnRef,
        "vnp_Amount": vnp_Amount,
        "vnp_OrderInfo": vnp_OrderInfo,
        "vnp_TransactionDate": vnp_TransactionDate,
        "vnp_CreateDate": vnp_CreateDate,
        "vnp_IpAddr": vnp_IpAddr,
        "vnp_TransactionType": vnp_TransactionType,
        "vnp_TransactionNo": vnp_TransactionNo,
        "vnp_CreateBy": vnp_CreateBy,
        "vnp_Version": vnp_Version,
        "vnp_SecureHash": secure_hash
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        response_json = json.loads(response.text)
    else:
        response_json = {"error": f"Request failed with status code: {response.status_code}"}

    return render_template(request, "refund.html", title="Kết quả hoàn tiền giao dịch", response_json=response_json)