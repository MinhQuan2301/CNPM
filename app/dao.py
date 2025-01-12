from flask import session
from flask_login import current_user
from sqlalchemy import or_
from flask_login import logout_user

from app.models import *


def authenticated_login(username, password):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    return User.query.filter(User.username.__eq__(username),
                                User.password.__eq__(password)).first()


def get_room(kw, room_id, page):
    room = Room.query
    if kw:
        room = room.filter(or_(func.lower(Room.style_room).contains(func.lower(kw)),
                               func.lower(Room.price).contains(func.lower(kw)),
                               func.lower(Room.status == False)))
        if 'còn phòng' in kw.lower():
            room = room.filter(Room.status == False)
        elif 'hết phòng' in kw.lower():
            room = room.filter(Room.status == True)

    if room_id:
        room = room.filter(Room.id.__eq__(room_id))

    if page:
        page = int(page)
        page_size = app.config["PAGE_SIZE"]
        start = (page - 1) * page_size

        return room.slice(start, start + page_size).all()

    return room.all()


def get_room_staff(room_id):
    room = Room.query
    if room_id:
        room = room.filter(Room.id.__eq__(room_id))
    result = room.all()
    return result



def get_room_cart(room_id):
    return Room.query.get(room_id)


def count_room():
    return Room.query.count()

def get_room_by_id(id):
    return Room.query.get(id)


def count_cart(cart):
    def count_cart(cart):
        total_amount, total_quantity = 0, 0

        if cart:
            for room_id in cart:
                room = get_room_cart(room_id)
                if room:
                    total_quantity += 1
                    total_amount += room.price

        return {
            "total_amount": total_amount,
            "total_quantity": total_quantity
        }

def get_user_by_id(user_id):
    user = User.query.get(user_id)
    if user:
        if 'Admin' in [role.position for role in user.roles]:
            session['user_role'] = 'Admin'
        else:
            session['user_role'] = 'User'
    return user

def admin_login(username, password):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    user = User.query.filter(User.username == username, User.password ==password).first()

    if user:
        admin_role = [role.position for role in user.roles.all()]
        if "Admin" in admin_role:
            return user
    return None



def login(username, password):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    return User.query.filter(User.username.__eq__(username),
                                User.password.__eq__(password)).first()



def add_comment(room_id, content):
    c = Comment(room_id=room_id, content=content, user=current_user)
    db.session.add(c)
    db.session.commit()

    return c

def logout_user_handler():
    logout_user()


def get_user(fullname=None, username=None, email=None, citizen_id=None):
    query = User.query
    if fullname:
        query = query.filter_by(fullname=fullname)
    if username:
        query = query.filter_by(username=username)
    if email:
        query = query.filter_by(email=email)
    if citizen_id:
        query = query.filter_by(citizen_id=citizen_id)
    return query.first()


def get_room_id(room_number=None):
    query = Room.query
    if room_number:
        query = query.filter_by(room_number=room_number)
    return query.first()


def get_role (position):
    role = Role.query.filter_by(position=position).first()
    return role

def get_payment_method(name=None):
    query = PaymentMethod.query
    if name:
        query = query.filter_by(name=name)
    return query.first()


def search_customer_by_keyword(kw):
    # Tìm kiếm khách hàng có Style là "Phiếu đặt phòng" và tên khớp với từ khóa
    customer = db.session.query(User).join(Booking).join(Style).filter(
        User.fullname.like(f'%{kw}%'),
        Style.ballot_type == "Phiếu đặt phòng"
    ).first()  # Dùng .first() nếu chỉ cần lấy một khách hàng đầu tiên tìm thấy

    if customer:
        # Tải các liên kết bổ sung (Booking, BookingDetail) cho khách hàng
        bookings = Booking.query.filter_by(user_id=customer.id).all()
        for booking in bookings:
            booking_details = BookingDetail.query.filter_by(booking_id=booking.id).all()
            booking.booking_detail = booking_details  # Thêm thông tin BookingDetail vào Booking

        customer.bookings = bookings  # Gán danh sách Booking vào customer

    return customer