import cart
from flask import session, render_template, jsonify, Blueprint

from app import app, dao


cart = Blueprint("cart", __name__)

@cart.route('/cart')
def carts():
    cart = session.get('cart', [])
    rooms_in_cart = []
    total_price = 0
    for room_id in cart:
        room = dao.get_room_cart(room_id)
        if room:
            rooms_in_cart.append(room)
            total_price += room.price
    cart_stats = session.get('cart_stats', {"total_quantity": len(cart)})

    return render_template('cart.html', rooms=rooms_in_cart, total=total_price, cart_stats=cart_stats)


@cart.route('/add_to_cart/<int:room_id>', methods=['POST'])
def add_to_cart(room_id):
    cart = session.get('cart', [])
    if room_id not in cart:
        cart.append(room_id)
    session['cart'] = cart
    session['cart_stats'] = {"total_quantity": len(cart)}  # Cập nhật số lượng

    return jsonify({"success": True, "cart_size": session['cart_stats']['total_quantity']})


@cart.route('/remove_from_cart/<int:room_id>', methods=['POST'])
def remove_from_cart(room_id):
    cart = session.get('cart', [])
    if room_id in cart:
        cart.remove(room_id)
    session['cart'] = cart

    rooms_in_cart = [dao.get_room_cart(room_id) for room_id in cart]
    total_price = sum(room.price for room in rooms_in_cart if room)

    cart_stats = {"total_quantity": len(cart)}
    session['cart_stats'] = cart_stats

    return jsonify({
        "success": True,
        "cart_size": cart_stats['total_quantity'],
        "total": total_price
    })
