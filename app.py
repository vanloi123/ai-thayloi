import google.generativeai as genai
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# 🔹 Thay API key của bạn vào đây
genai.configure(api_key="AIzaSyB_hZxCpbtmf5MBIBkdmLDrN_bT1X5pYKY")

# 🔹 Dùng model ổn định và tương thích cao nhất
model = genai.GenerativeModel("models/gemini-2.5-flash")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    user_message = request.json.get("message")
    system_prompt = (
        "Bạn là trợ lý AI hỗ trợ học sinh THPT học môn Tin học. "
        "Hãy trả lời dễ hiểu, ngắn gọn, có thể kèm ví dụ hoặc câu hỏi trắc nghiệm nếu cần."
    )

    try:
        response = model.generate_content(f"{system_prompt}\nNgười học: {user_message}")
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Lỗi khi xử lý yêu cầu: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
