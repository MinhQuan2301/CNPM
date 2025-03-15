import google.generativeai as genai
import os
from flask import Blueprint, jsonify, request, current_app
from flask_cors import CORS

from app import app, config
from app.models import Evaluation, Style, PaymentMethod, Room, Floor

openAI = Blueprint("openAI", __name__)

CORS(app)
genai.configure(api_key=config.GEMINI_API_KEY)


# Định nghĩa Blueprint



generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
)
def get_training_data():
    """Lấy dữ liệu từ database và trả về dưới dạng JSON."""
    try:
        data = {
            "evaluations": [
                {"id": e.id, "point": e.point, "room_id": e.room_id}
                for e in Evaluation.query.all()
            ],
            "styles": [
                {"id": s.id, "ballot_type": s.ballot_type}
                for s in Style.query.all()
            ],
            "payment_methods": [
                {"id": p.id, "name": p.name}
                for p in PaymentMethod.query.all()
            ],
            "rooms": [
                {
                    "id": r.id, "room_number": r.room_number, "style_room": r.style_room,
                    "price": r.price, "image": r.image, "status": r.status,
                    "address": r.address, "description": r.description, "floor_id": r.floor_id
                }
                for r in Room.query.all()
            ],
            "floors": [
                {"id": f.id, "number_floor": f.number_floor}
                for f in Floor.query.all()
            ]
        }
        return data
    except Exception as e:
        print(f"Error fetching training data: {e}")
        return None

@openAI.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message", "")

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    # Lấy dữ liệu từ database
    db_data = get_training_data()

    # Xây dựng ngữ cảnh từ dữ liệu database
    if db_data:
        context = f"""
        Đây là thông tin khách sạn:
        - Phòng: {[room['room_number'] + ' (' + str(room['price']) + ' VND/ngày)' for room in db_data['rooms']]}
        - Phương thức thanh toán: {[pm['name'] for pm in db_data['payment_methods']]}
        - Các tầng: {[floor['number_floor'] for floor in db_data['floors']]}
        """
    else:
        context = "Không thể lấy dữ liệu từ database."

    # Gửi yêu cầu đến AI với ngữ cảnh mở rộng
    try:
        response = model.generate_content(f"{context}\nUser: {user_input}")
        return jsonify({"response": response.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
