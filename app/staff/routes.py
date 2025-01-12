from datetime import datetime

from flask import session, render_template, jsonify, Blueprint, request, redirect, url_for, flash

from app import app, dao, db
from app.models import Booking, PaymentMethod, Style, Room, BookingDetail, Policy, User

staff = Blueprint("staff", __name__)


@app.route('/staff/booking_room', methods=['GET', 'POST'])
def staff_booking_room():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        customer_name = request.form.get('customerName')
        phone_number = request.form.get('phone_number')
        cccd = request.form.get('cccd')
        customer_stype = request.form.get('customerType')
        address = request.form.get('address')
        room_numbers = request.form.get('roomNumber', "").split(",")
        checkin_date = request.form.get('bookingDate')
        checkout_date = request.form.get('checkoutDate')

        # Chuyển đổi kiểu ngày
        create_at = datetime.now().date()
        checkin_date = datetime.strptime(checkin_date, '%Y-%m-%d').date()

        # Lấy giá trị "Thời điểm nhận phòng" từ bảng Policy
        policy = Policy.query.filter_by(key="Thời điểm nhận phòng").first()
        if policy:
            max_days = policy.value  # Lấy giá trị value
            # Kiểm tra quy định ngày nhận phòng
            days_difference = (checkin_date - create_at).days
            if days_difference > max_days:
                flash(f"Ngày nhận phòng không được quá {max_days} ngày kể từ ngày tạo phiếu.", "error")
                return render_template('staff_booking.html')

        # Xử lý loại khách hàng
        if customer_stype == 'domestic':
            customer_stype = 'Nội địa'
        elif customer_stype == 'international':
            customer_stype = 'Nước ngoài'

        # Kiểm tra khách hàng, thêm mới nếu không tồn tại
        user = dao.get_user(cccd)
        if not user:
            user = User(
                fullname=customer_name,
                phone_number=phone_number,
                citizen_id=cccd,
                address=address
            )
            db.session.add(user)
            db.session.commit()

        # Thêm phiếu đặt phòng
        booking = Booking(
            check_in_date=checkin_date,
            check_out_date=datetime.strptime(checkout_date, '%Y-%m-%d').date(),
            customer_stype=customer_stype,
            user_id=user.id,
            payment_method_id=1,
            style_id=1
        )
        db.session.add(booking)
        db.session.commit()

        # Thêm chi tiết đặt phòng
        for room_number in room_numbers:
            room_number = room_number.strip()
            room = dao.get_room_id(room_number)
            if room:
                booking_detail = BookingDetail(
                    booking_id=booking.id,
                    room_id=room.id,
                    quantity_customer=1,
                    total_amount=0
                )
                db.session.add(booking_detail)
                room.status = True
            else:
                print(f"Không tìm thấy phòng với số {room_number}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Lỗi khi lưu thông tin đặt phòng:", str(e))
        return redirect(url_for('staff_booking'))

    return render_template('staff_booking.html')


@app.route('/staff/rental', methods=['GET', 'POST'])
def staff_rental_room():
    if request.method == 'POST':
        # Lấy dữ liệu từ form
        customer_name = request.form.get('customer_name')
        phone_number = request.form['phone_number']
        cccd = request.form.get('cccd')
        customer_stype = request.form.get('customer_type')
        address = request.form.get('address')
        room_numbers = request.form.get('room_number', "").split(",")
        checkin_time = request.form.get('checkin_time')
        checkin_date = request.form.get('booking_date')
        checkout_date = request.form.get('checkout_date')
        number_of_people = request.form.get('number_of_people')
        payment_method_name = request.form.get('payment_method')
        price = float(request.form.get('price'))

        if payment_method_name == 'cash':
            payment_method_name = 'Tiền mặt'
        elif payment_method_name == 'card':
            payment_method_name = 'Tiền thẻ'

        # Chuyển đổi kiểu khách hàng
        if customer_stype == 'domestic':
            customer_stype = 'Nội địa'
        elif customer_stype == 'international':
            customer_stype = 'Nước ngoài'

        # Kiểm tra và lấy user từ database
        user = dao.get_user(cccd)
        if not user:
            user = User(
                fullname=customer_name,
                phone_number=phone_number,
                citizen_id=cccd,
                address=address
            )
            db.session.add(user)
            db.session.commit()
        print(payment_method_name)
        # Tìm phương thức thanh toán từ database
        payment_method = dao.get_payment_method(payment_method_name)
        if not payment_method:
            print(f"Không tìm thấy phương thức thanh toán: {payment_method_name}")
            # Gán phương thức thanh toán mặc định nếu không tìm thấy
            payment_method = dao.get_payment_method("Tiền mặt")

        # Kiểm tra các trường ngày nhận phòng và ngày trả phòng
        if checkin_date:
            try:
                checkin_date = datetime.strptime(checkin_date, '%Y-%m-%d').date()
            except ValueError:
                print("Lỗi: Ngày nhận phòng không hợp lệ.")
                checkin_date = None
        else:
            print("Lỗi: Ngày nhận phòng không được để trống.")
            checkin_date = None

        if checkout_date:
            try:
                checkout_date = datetime.strptime(checkout_date, '%Y-%m-%d').date()
            except ValueError:
                print("Lỗi: Ngày trả phòng không hợp lệ.")
                checkout_date = None
        else:
            print("Lỗi: Ngày trả phòng không được để trống.")
            checkout_date = None

        # Kiểm tra giờ nhận phòng
        if checkin_time:
            try:
                checkin_time = datetime.strptime(checkin_time, '%H:%M').time()
            except ValueError:
                print("Lỗi: Giờ nhận phòng không hợp lệ.")
                checkin_time = None
        else:
            print("Lỗi: Giờ nhận phòng không được để trống.")
            checkin_time = None

        # Tạo phiếu thuê phòng
        booking = Booking(
            check_in_date=checkin_date,
            check_out_date=checkout_date,
            check_in_time=checkin_time,
            customer_stype=customer_stype,
            user_id=user.id,
            payment_method_id=payment_method.id,
            style_id=2  # Hoặc style_id khác tùy vào yêu cầu
        )
        db.session.add(booking)
        db.session.commit()

        # Thêm chi tiết phòng vào BookingDetail
        for room_number in room_numbers:
            room_number = room_number.strip()
            room = dao.get_room_id(room_number)
            if room:
                booking_detail = BookingDetail(
                    booking_id=booking.id,
                    room_id=room.id,
                    quantity_customer=number_of_people,
                    total_amount=price,
                    status= True
                )
                db.session.add(booking_detail)
            else:
                print(f"Không tìm thấy phòng với số {room_number}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Lỗi khi lưu thông tin đặt phòng:", str(e))

        return redirect(url_for('staff_rental'))  # Redirect lại trang đặt phòng

    return render_template('staff_rental.html')


@app.route('/search_customer', methods=['GET', 'POST'])
def search_customer():
    customer = None
    if request.method == 'GET':
        kw = request.args.get('kw')  # Lấy từ khóa tìm kiếm từ form
        if kw:
            # Gọi hàm từ dao.py để thực hiện truy vấn
            customer = dao.search_customer_by_keyword(kw)
    return render_template('search.html', customer=customer)
