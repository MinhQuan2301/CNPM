import math
import time
import uuid
from os import abort

from flask import render_template, url_for, jsonify, flash
from flask_login import login_required
import json
import dao

from flask import request

from admin import *
from app import LoginManager, app
from app.config import redis_client
from app.vnpays.forms import PaymentForm


@app.route('/')
def home():
    kw = request.args.get('kw')
    room_id = request.args.get('room_id')
    page = request.args.get('page', 1)
    num = dao.count_room()
    page_size = app.config["PAGE_SIZE"]
    pro = dao.get_room(kw, room_id, page)
    cart_stats = session.get('cart_stats', {"total_quantity": 0})
    total_pages = math.ceil(num / page_size)
    return render_template(
        'layout.html', pages=total_pages, produces=pro, cart_stats=cart_stats, kw=kw, room_id=room_id, page=page)




@app.route('/staff')
def staff():
    return render_template('staff.html')

@app.route('/staff/home')
def staff_home():
    room_id = request.args.get('room_id')
    pro = dao.get_room_staff(room_id)
    print(f"Room ID: {room_id}, Data: {pro}")
    if pro is None:  # Xử lý khi không có dữ liệu
        pro = []
    return render_template('staff_home.html', room_id=room_id, produces=pro)



@app.route('/staff/booking')
def staff_booking():
    return render_template('staff_booking.html')


@app.route('/staff/rental')
def staff_rental():
    return render_template('staff_rental.html')



@app.route('/staff/search')
def search():
    return render_template('search.html')



@app.route('/rooms/<id>')
def info_room(id):
    room = dao.get_room_by_id(id)
    if room is None:
        abort(404)  # Trả về lỗi 404 nếu phòng không tồn tại

        # Lấy danh sách bình luận liên quan đến phòng
    comments = Comment.query.filter_by(room_id=id).order_by(Comment.create_at.desc()).all()

    # Render template với dữ liệu phòng và bình luận
    return render_template('info.html', room=room, comments=comments)


@app.route('/vnpay_info', methods=['GET', 'POST'])
@login_required
def vnpay_info():
    cart = session.get('cart', [])
    if not cart:
        flash("Giỏ hàng của bạn đang trống!", "warning")
        return redirect(url_for('cart.cart'))

    # Lấy thông tin phòng từ dao và tính tổng giá trị
    rooms = [dao.get_room_by_id(room_id) for room_id in cart if dao.get_room_cart(room_id)]
    total_amount = sum(room.price for room in rooms)

    # Tạo một order_id duy nhất từ thời gian hiện tại
    order_id = str(int(time.time()))

    # Lưu các thông tin quan trọng vào session
    session['payment_user_id'] = current_user.id
    session['total_amount'] = total_amount
    session['order_id'] = order_id
    session.modified = True
    session.permanent = True

    form = PaymentForm(request.form)
    return render_template('payment.html', form=form, total_amount=total_amount, order_id=order_id)

@app.route('/payment_success')
@login_required
def payment_success():
    return render_template('thanks.html')


@app.route('/booking', methods=['GET', 'POST'])
def booking_form():
    # Kiểm tra quyền User
    user_roles = [role.position for role in current_user.roles]
    if 'User' not in user_roles:
        flash("Bạn cần đăng nhập bằng tài khoản có quyền User để đặt phòng.", "warning")
        return redirect(url_for('login', next=request.url))

    # Kiểm tra giỏ hàng
    cart = session.get('cart', [])
    if not cart:
        flash("Giỏ hàng của bạn đang trống!", "warning")
        return redirect(url_for('cart.cart'))

    # Lấy thông tin phòng từ cart
    rooms = [dao.get_room_by_id(room_id) for room_id in cart if dao.get_room_cart(room_id)]
    if not rooms:
        flash("Không tìm thấy thông tin phòng trong giỏ hàng!", "warning")
        return redirect(url_for('cart.cart'))

    if request.method == 'POST':
        email_from_form = request.form.get('email')
        total_amount = sum(room.price for room in rooms)

        # Lấy thông tin từ form
        booking_data = {
            'user_id': current_user.id,
            'checkin': request.form.get('checkin'),
            'checkout': request.form.get('checkout'),
            'guestType': request.form.get('guestType'),
            'cccd': request.form.get('cccd'),
            'address': request.form.get('address'),
            'fullname': current_user.fullname,
            'email': email_from_form,
            'total_amount': total_amount,
            'rooms': [{
                'id': room.id,
                'room_number': room.room_number,
                'price': room.price
            } for room in rooms]
        }

        # Tạo order_id duy nhất
        order_id = str(int(time.time()))
        booking_data['order_id'] = order_id

        # Lưu vào Redis với thời gian hết hạn 24 giờ
        redis_client.set(
            f"booking_data:{current_user.id}",
            json.dumps(booking_data),
            ex=3600  # 24 giờ
        )

        # Lưu các thông tin quan trọng vào session
        session['payment_user_id'] = current_user.id
        session['order_id'] = order_id
        session['total_amount'] = total_amount
        session.permanent = True  # Kéo dài thời gian session

        return redirect(url_for('vnpay_info'))

    # GET request: hiển thị form
    return render_template('booking.html',
                           rooms=rooms,
                           fullname=current_user.fullname)

@app.route('/user/login', methods=['POST'])
def user_login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = dao.authenticated_login(username=username, password=password)
    if user:
        login_user(user, remember=True)
        session['user_id'] = user.id
        if 'User' in [role.position for role in user.roles]:
            return redirect(url_for('home'))
        elif 'Staff' in [role.position for role in user.roles]:
            return redirect(url_for('staff_home'))
    else:
        return render_template('login.html', error="Sai tên đăng nhập hoặc mật khẩu")


@app.route('/user_info')
def user_info():
    if current_user.is_authenticated:
        user_roles = [role.position for role in current_user.roles]
        is_user_role = 'User' in user_roles  # Kiểm tra xem có role 'User' không
        return render_template('user_info.html', is_user_role=is_user_role)
    else:
        return render_template('user_info.html', is_user_role=False)


@app.route('/add_comment', methods=['POST'])
@login_required
def add_comment():
    comment_text = request.json.get('comment')
    room_id = request.json.get('room_id')

    if not comment_text or not room_id:
        return jsonify({"error": "Thiếu dữ liệu"}), 400

    new_comment = Comment(
        comments=comment_text,
        user_id=current_user.id,
        room_id=room_id
    )
    db.session.add(new_comment)
    db.session.commit()

    return jsonify({
        "message": "Thêm bình luận thành công",
        "username": current_user.username,
        "avatar": "static/images/avatar.png",  # Đường dẫn đến ảnh mặc định
        "comment": comment_text,
        "created_at": new_comment.create_at.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/add_rating', methods=['POST'])
@login_required
def add_rating():
    rating = request.json.get('rating')
    room_id = request.json.get('room_id')

    if not rating or not room_id:
        return jsonify({"error": "Thiếu dữ liệu"}), 400

    new_evaluation = Evaluation(
        point=rating,
        user_id=current_user.id,
        room_id=room_id
    )
    db.session.add(new_evaluation)
    db.session.commit()

    return jsonify({"message": "Thêm đánh giá thành công"})


# @app.route('/room/<int:room_id>')
# def room_detail(room_id):
#     # Lấy thông tin phòng dựa vào room_id
#     room = Room.query.get_or_404(room_id)
#
#     # Lấy danh sách tất cả bình luận liên quan đến phòng này
#     comments = Comment.query.filter_by(room_id=room_id).order_by(Comment.create_at.desc()).all()
#
#     # Render template với dữ liệu phòng và bình luận
#     return render_template('room_detail.html', room=room, comments=comments)


@app.route('/login_user')
def login():
    return render_template('login.html')


@app.route('/register')
def register():
    return render_template('register.html')


@app.context_processor
def common_responses():
    cart = session.get('cart', [])
    cart_stats = dao.count_cart(cart)
    return {
        'cart_stats': cart_stats
    }
@app.route('/update-room-status', methods=['POST'])
def update_room_status():
    room_id = request.json.get('room_id')
    new_status = request.json.get('status')

    if room_id is None or new_status is None:
        return jsonify({"error": "Invalid data"}), 400

    room = Room.query.get(room_id)
    if room is None:
        return jsonify({"error": "Room not found"}), 404

    room.status = new_status  # Cập nhật trạng thái
    db.session.commit()

    return jsonify({"message": "Room status updated successfully"}), 200

@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = dao.admin_login(username=username, password=password)
    if user:
        login_user(user)
        session['user_role'] = 'Admin'
        return redirect('/admin')
    else:
        flash("Tài khoản hoặc mật khẩu không đúng, hoặc bạn không có quyền truy cập!", "danger")
        return redirect('/admin')


@app.route('/logout_staff')
def logout_staff():
    if current_user.is_authenticated and 'Staff' in [role.position for role in current_user.roles]:
        dao.logout_user_handler()
        return redirect(url_for('login'))

@app.route('/logout_user')
def logout_user():
    if current_user.is_authenticated and 'User' in [role.position for role in current_user.roles]:
        dao.logout_user_handler()
        return redirect(url_for('login'))


@LoginManager.user_loader
def user_load(user_id):
    return dao.get_user_by_id(user_id)



if __name__ == "__main__":
    app.run(debug=True)
