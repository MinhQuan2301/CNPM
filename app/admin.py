from datetime import datetime
from app import admin
from app.models import *
from flask_admin.contrib.sqla import ModelView
from flask_admin import BaseView, expose
from flask_login import login_user, logout_user, current_user
from flask import redirect, session, request, jsonify, json


class AuthenticatedModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and 'Admin' in [role.position for role in current_user.roles]

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/admin/login')


class AuthenticatedBaselView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated and 'Admin' in [role.position for role in current_user.roles]

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/admin/login')


class UserView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True
    column_filters = ['citizen_id', 'address', 'email', 'username', 'phone_number', 'fullname']
    column_searchable_list = ['citizen_id', 'address', 'email', 'username', 'phone_number', 'fullname']
    column_list = ['fullname', 'email', 'username', 'phone_number', 'address', 'citizen_id', 'create_at']

class RoleView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True
    column_filters = ['id', 'position']
    column_searchable_list = ['position']
    column_list = ['id', 'position']
    form_columns = ['position']


class RoomView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True
    column_filters = ['price', 'style_room', 'room_number']
    column_searchable_list = ['price', 'style_room', 'room_number']



class PolicyView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True
    column_filters = ['key', 'value', 'updated_at']
    column_searchable_list = ['key']
    column_list = ['key', 'value', 'updated_at']
    form_columns = ['key', 'value']


class BookingView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True



class BookingDetailView(AuthenticatedModelView):
    can_view_details = True
    can_export = True
    edit_modal = True
    details_modal = True
    create_modal = True


class LogoutView(AuthenticatedBaselView):
    @expose('/')
    def index(self):
        if current_user.is_authenticated and 'Admin' in [role.position for role in current_user.roles]:
            logout_user()  # Đăng xuất người dùng hiện tại
            session.clear()  # Xóa toàn bộ dữ liệu trong session
            return redirect('/admin')  #


class InvoiceView(ModelView, AuthenticatedBaselView):
    column_list = ('id', 'fullname', 'check_in_date', 'check_out_date', 'room_id', 'total_amount')
    column_labels = {
        'id': 'ID',
        'fullname': 'Họ tên',
        'check_in_date': 'Ngày nhận phòng',
        'check_out_date': 'Ngày trả phòng',
        'room_id': 'Số phòng',
        'total_amount': 'Tổng tiền'
    }

    def get_query(self):
        return self.session.query(Booking, User, BookingDetail).\
            join(User, Booking.user_id == User.id).\
            join(BookingDetail, Booking.id == BookingDetail.booking_id).\
            with_entities(Booking.id, User.fullname, Booking.check_in_date, Booking.check_out_date, BookingDetail.room_id, BookingDetail.total_amount)



class ReportView(AuthenticatedBaselView):
    @expose('/', methods=['GET'])
    def index(self, cls=None):
        # Lấy thông tin năm và tháng từ request
        year = request.args.get('year', default=2024, type=int)
        month = request.args.get('month', default='1')  # Mặc định là chuỗi "1"
        month_list = ['all'] + [str(m) for m in range(1, 13)]  # Thêm tùy chọn "all"

        # Truy vấn để lấy thông tin doanh thu và số lượt thuê của từng loại phòng
        query = db.session.query(
            Room.style_room.label('room_name'),
            func.count(BookingDetail.booking_id).label('days_rented'),  # Đếm số lần thuê
            func.sum(BookingDetail.total_amount).label('revenue')  # Tổng tiền
        ).join(BookingDetail, Room.id == BookingDetail.room_id) \
            .join(Booking, BookingDetail.booking_id == Booking.id) \
            .join(Style, Booking.style_id == Style.id) \
            .filter(Style.ballot_type == "Phiếu thuê phòng") \
            .filter(func.extract('year', Booking.check_in_date) == year)

        # Nếu không phải "all", thêm điều kiện lọc theo tháng
        if month != 'all':
            query = query.filter(func.extract('month', Booking.check_in_date) == int(month))

        room_usage = query.group_by(Room.style_room).all()

        # Tính tổng doanh thu
        total_revenue = sum([data.revenue or 0 for data in room_usage]) or 0

        # Chuẩn bị dữ liệu cho bảng
        table_data = [{
            'room_name': data.room_name,
            'days_rented': data.days_rented or 0,
            'revenue': data.revenue or 0,
            'rental_rate': (data.revenue or 0) / total_revenue * 100 if total_revenue > 0 else 0
        } for data in room_usage]

        # Chuẩn bị dữ liệu cho biểu đồ
        labels = [data.room_name for data in room_usage]
        revenues = [data.revenue or 0 for data in room_usage]
        booking_counts = [data.days_rented or 0 for data in room_usage]

        # Render template
        return self.render(
            'admin/revenue.html',
            table_data=table_data,
            year=year,
            month=month,
            month_list=month_list,
            total_revenue=total_revenue,
            labels=labels,
            revenues=revenues,
            booking_counts=booking_counts,
            enumerate=enumerate
        )

class OccupancyView(AuthenticatedBaselView):
    @expose('/', methods=['GET'])
    def index(self):
        # Lấy thông tin năm và tháng từ request
        year = request.args.get('year', default=2024, type=int)
        month = request.args.get('month', default='1')  # Mặc định là chuỗi "1"
        month_list = ['all'] + [str(m) for m in range(1, 13)]  # Thêm tùy chọn "all"

        # Truy vấn để lấy số ngày thuê của từng phòng
        query = db.session.query(
            Room.room_number.label('room_name'),
            func.sum(func.datediff(Booking.check_out_date, Booking.check_in_date)).label('days_rented')
        ).join(BookingDetail, Room.id == BookingDetail.room_id) \
            .join(Booking, BookingDetail.booking_id == Booking.id) \
            .join(Style, Booking.style_id == Style.id) \
            .filter(Style.ballot_type == "Phiếu thuê phòng") \
            .filter(func.extract('year', Booking.check_in_date) == year)

        # Nếu không phải "all", thêm điều kiện lọc theo tháng
        if month != 'all':
            query = query.filter(func.extract('month', Booking.check_in_date) == int(month))

        room_usage = query.group_by(Room.room_number).all()

        # Tính tổng số ngày thuê để tính tỷ lệ
        total_days_rented = sum([data.days_rented or 0 for data in room_usage]) or 1  # Tránh chia 0

        # Chuẩn bị dữ liệu cho bảng
        table_data = [{
            'room_name': data.room_name,
            'days_rented': data.days_rented or 0,
            'rental_rate': (data.days_rented or 0) / total_days_rented * 100
        } for data in room_usage]

        # Chuẩn bị dữ liệu cho biểu đồ
        labels = [data['room_name'] for data in table_data]
        days_rented = [data['days_rented'] for data in table_data]
        rental_rates = [data['rental_rate'] for data in table_data]

        return self.render(
            'admin/occupancy.html',
            table_data=table_data,
            year=year,
            month=month,
            month_list=month_list,
            total_days_rented=total_days_rented,
            labels=labels,
            days_rented=days_rented,
            rental_rates=rental_rates
        )

admin.add_view(UserView(User, db.session))
admin.add_view(RoleView(Role, db.session))
admin.add_view(RoomView(Room, db.session))
admin.add_view(PolicyView(Policy, db.session))
admin.add_view(BookingView(Booking, db.session))
admin.add_view(BookingDetailView(BookingDetail, db.session))
admin.add_view(LogoutView(name="Đăng xuất"))
admin.add_view(InvoiceView(Invoice, db.session, name="Hóa đơn thanh toán"))
admin.add_view(ReportView(name="Báo Cáo Doanh Thu",  endpoint='report'))
admin.add_view(OccupancyView(name="Báo Cáo Mật Độ", endpoint="occupancy"))
