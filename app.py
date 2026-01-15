import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
# Cấu hình Session cho Flask (GIỮ NGUYÊN)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Chưa thiết lập GOOGLE_API_KEY trong Environment Variables!")

genai.configure(api_key=api_key)

# --- DEBUG: KIỂM TRA MODEL CÓ SẴN (GIỮ NGUYÊN) ---
print("=========================================")
print("ĐANG KIỂM TRA KẾT NỐI VÀ DANH SÁCH MODEL...")
try:
    available_models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- Tìm thấy: {m.name}")
            available_models.append(m.name)
            
    if not available_models:
        print("❌ CẢNH BÁO: Không tìm thấy model nào hỗ trợ generateContent!")
    else:
        print("✅ Kết nối API thành công!")
except Exception as e:
    print(f"❌ LỖI KẾT NỐI NGHIÊM TRỌNG: {str(e)}")
print("=========================================")
# ---------------------------------------

# ==============================================================================
# 🧠 SYSTEM PROMPT: BẢN CẬP NHẬT (TOÁN - LÝ - HÓA - SINH & PHÂN LOẠI CẤP HỌC)
# ==============================================================================
system_prompt_global = (
    "Bạn là **Thầy/Cô Trợ giảng AI** tâm huyết, chuyên môn vững vàng, 20 năm kinh nghiệm. "
    "Phong cách: Gần gũi, ân cần nhưng gãy gọn. Xưng hô 'Thầy/Cô' và 'em'.\n\n"

    "⚙️ **LOGIC XỬ LÝ THÔNG MINH (BẮT BUỘC):**\n"
    "1. **NẾU LÀ CHÀO HỎI XÃ GIAO** (Ví dụ: 'Xin chào', 'Hello', 'Thầy ơi'):\n"
    "   - -> **BỎ QUA** dòng Phân loại.\n"
    "   - -> Trả lời thân thiện, ngắn gọn, mời học sinh đặt câu hỏi.\n"
    "2. **NẾU LÀ CÂU HỎI HỌC TẬP**:\n"
    "   - -> **BẮT BUỘC** mở đầu bằng dòng: `💡 Phân loại: [Môn] – [Chủ đề] – [Cấp học]`.\n"
    "   - -> Cấp học CHỈ ĐƯỢC GHI: **Tiểu học**, **THCS**, hoặc **THPT** (Tuyệt đối KHÔNG ghi 'Lớp 10', 'Grade 11').\n"
    "   - -> Sau đó giải thích gợi mở (Socratic method), không đưa đáp án ngay.\n\n"
    
    "⚠️ **QUY TẮC HIỂN THỊ KHOA HỌC (TUÂN THỦ NGHIÊM NGẶT):**\n"
    "1. **TOÁN & VẬT LÝ:**\n"
    "   - BẮT BUỘC dùng mã **LaTeX** cho mọi biểu thức/công thức.\n"
    "   - Kẹp trong `$ ... $` (nếu nằm cùng dòng) hoặc `$$ ... $$` (nếu nằm riêng dòng).\n"
    "   - Ví dụ chuẩn: 'Phương trình $x^2 - 4 = 0$ có nghiệm...'.\n"
    "   - Ví dụ Vật lý: $F = ma$, $\\lambda = \\frac{v}{f}$.\n"
    "2. **HÓA HỌC (RẤT QUAN TRỌNG):**\n"
    "   - BẮT BUỘC dùng lệnh `\\ce{...}` cho mọi công thức hóa học (Để hiển thị chữ đứng).\n"
    "   - Ví dụ: Thay vì viết $H_2SO_4$ (sai), phải viết $\\ce{H2SO4}$ (đúng).\n"
    "   - Phương trình phản ứng: $\\ce{2H2 + O2 ->[t^o] 2H2O}$.\n"
    "   - Ion: $\\ce{Cu^2+}$, $\\ce{SO4^2-}$.\n"
    "3. **SINH HỌC / CÁC MÔN KHÁC:**\n"
    "   - Trình bày mạch lạc, in đậm các từ khóa quan trọng.\n"
    "   - Sơ đồ lai (nếu có) trình bày rõ ràng từng dòng P, G, F1.\n\n"

    "⛔ **QUY TẮC CẤM:**\n"
    "1. Không in ra các tiêu đề thừa như 'PHẦN 1', 'LỜI GIẢI', 'TƯƠNG TÁC'.\n"
    "2. Không chào hỏi lặp lại kiểu robot ở mỗi câu trả lời.\n\n"

    "📊 **JSON DATA (BẮT BUỘC Ở CUỐI CÙNG):**\n"
    "Kết thúc câu trả lời, in ra block code json-data chứa dữ liệu thống kê:\n"
    "```json-data\n"
    "{\n"
    ' "progress_strong": "[Chủ đề học sinh nắm vững]",\n'
    ' "progress_weak": "[Chủ đề cần cải thiện]",\n'
    ' "analytics_summary": "[Nhận xét ngắn gọn về tư duy của học sinh]",\n'
    ' "recommendations": ["[Gợi ý 1]", "[Gợi ý 2]"]\n'
    "}\n"
    "```"
)

# KHỞI TẠO MODEL (Ưu tiên bản -it, fallback về bản thường)
try:
    model = genai.GenerativeModel("gemma-3-27b-it")
except Exception:
    try:
        model = genai.GenerativeModel("gemma-3-27b")
        print("⚠️ Đang dùng bản gemma-3-27b thường (Do bản -it không tìm thấy)")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo model: {e}")

# Biến toàn cục lưu phiên chat (GIỮ NGUYÊN)
chat_session = None

def get_chat_session():
    """Khởi tạo hoặc trả về phiên chat hiện tại."""
    global chat_session
    if 'chat_session_id' not in session or chat_session is None:
        chat_session = model.start_chat(history=[]) 
        session['chat_session_id'] = id(chat_session)   
    
    if 'learning_history' not in session:
        session['learning_history'] = []      
    return chat_session

@app.route("/")
def index():
    get_chat_session()
    return render_template("index.html")

@app.route("/new_chat", methods=["POST"])
def new_chat():
    """Xử lý Reset khi người dùng chọn môn mới (GIỮ NGUYÊN)"""
    global chat_session
    chat_session = None 
    session.clear() 
    get_chat_session() 
    return jsonify({"status": "success", "message": "Đã reset hội thoại"})

@app.route("/ask", methods=["POST"])
def ask():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"reply": "Vui lòng nhập câu hỏi."})

    try:
        current_chat = get_chat_session()   
        
        # Tóm tắt lịch sử (GIỮ NGUYÊN LOGIC CŨ)
        history_data = session.get('learning_history', [])
        recent_history = history_data[-3:] 
        
        history_str = "\n".join([f"Học sinh: {h['user']} | AI: {h['ai_summary']}" for h in recent_history])
        
        # --- KỸ THUẬT NHÚNG SYSTEM PROMPT VÀO TIN NHẮN (PROMPT INJECTION) ---
        # Ghép System Prompt mới vào trước câu hỏi để ép model tuân thủ quy tắc
        full_prompt = (
            f"{system_prompt_global}\n\n"
            f"=== LỊCH SỬ HỘI THOẠI ===\n{history_str}\n\n"
            f"=== CÂU HỎI MỚI ===\nHỌC SINH HỎI: {user_message}"
        )
        
        # Cập nhật: Thêm generation_config để giảm nhiệt độ (temperature=0.3)
        # Giúp model viết công thức Toán/Hóa chuẩn hơn, ít bịa đặt
        response = current_chat.send_message(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000
            )
        ) 
        
        if not response.text:
             return jsonify({"reply": "Lỗi: AI không phản hồi."})       
        
        # Lưu vào lịch sử (Lọc bỏ phần JSON) - GIỮ NGUYÊN
        ai_reply_full = response.text
        clean_text_for_history = ai_reply_full.split("```json-data")[0].strip()
        
        if 'learning_history' not in session: session['learning_history'] = []
        session['learning_history'].append({
            'user': user_message,
            'ai_summary': clean_text_for_history[:150] + "..." 
        })
        session.modified = True 
        
        return jsonify({"reply": ai_reply_full})
        
    except Exception as e:
        print(f"Server Error: {e}")
        global chat_session
        chat_session = None 
        # Trả về thông báo lỗi thân thiện hơn
        return jsonify({"reply": f"⚠️ Hệ thống đang bận hoặc gặp lỗi kết nối API. Mã lỗi: {str(e)}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
