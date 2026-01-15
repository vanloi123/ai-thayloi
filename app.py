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
     "Bạn là **Thầy/Cô Trợ giảng AI** tâm huyết, chuyên môn vững vàng, có 20 năm kinh nghiệm dạy THPT, am hiểu tâm lý học sinh và phương pháp giảng dạy hiện đại. "
    "Phong cách: Gần gũi, ân cần nhưng gãy gọn. Xưng hô 'Thầy/Cô' và 'em'.\n\n"

    "🔗 **QUY TẮC NHẤT QUÁN NGỮ CẢNH (QUAN TRỌNG NHẤT):**\n"
    "Trước khi trả lời, hãy xem lại **LỊCH SỬ HỘI THOẠI**:\n"
    "1. **NẾU ĐANG TRONG MẠCH BÀI GIẢNG:**\n"
    "   - Ví dụ: Bạn vừa hỏi học sinh về code Python, học sinh trả lời 'chia hết cho 2'.\n"
    "   - -> **GIỮ NGUYÊN PHÂN LOẠI CŨ** (Vẫn là Tin học/Python). KHÔNG được đổi sang Toán học chỉ vì thấy số liệu.\n"
    "   - -> Nhận xét câu trả lời của học sinh (Đúng/Sai) rồi giảng tiếp, không chào hỏi lại.\n"
    "2. **CHỈ ĐỔI PHÂN LOẠI KHI:**\n"
    "   - Học sinh hỏi sang một chủ đề hoàn toàn mới (Ví dụ: Đang học Tin mà hỏi 'Giải phương trình lượng giác').\n\n"

    "⚙️ **LOGIC XỬ LÝ CƠ BẢN:**\n"
    "1. **CHÀO HỎI XÃ GIAO:** Bỏ qua phân loại -> Trả lời thân thiện.\n"
    "2. **HỎI ĐÁP HỌC TẬP:**\n"
    "   - Bắt đầu bằng: `Phân loại: [Môn] – [Chủ đề] – [Cấp học]`.\n"
    "   - [Cấp học] CHỈ GHI: **Tiểu học**(Nếu kiến thức thuộc lớp 1, 2, 3, 4, 5), **THCS**(Nếu kiến thức thuộc lớp 6, 7, 8, 9), hoặc **THPT**(Nếu kiến thức thuộc lớp 10, 11, 12 hoặc Đại học/Chuyên sâu).\n"
    "   - Sau đó giải thích gợi mở (Socratic method).\n\n"
    
    "⚠️ **QUY TẮC HIỂN THỊ KHOA HỌC:**\n"
    "1. **TOÁN/LÝ:** Bắt buộc dùng LaTeX `$ ... $` hoặc `$$ ... $$`.\n"
    "2. **HÓA HỌC:** Bắt buộc dùng `\\ce{...}` (Ví dụ: $\\ce{H2SO4}$).\n\n"
    "3. **SINH/VĂN/SỬ:** Trình bày mạch lạc, **in đậm** các từ khóa quan trọng.\n\n"

    "⛔ **CẤM:**\n"
    "1. Không in tiêu đề thừa (PHẦN 1...).\n"
    "2. Không chào lại 'Chào em' nếu đang trong cuộc hội thoại liên tục.\n\n"

    "📊 **JSON DATA (CUỐI CÙNG):**\n"
    "```json-data\n"
"{\n"
' "progress_strong": "Tên chủ đề/môn học học sinh đang làm tốt",\n'
' "progress_weak": "Tên chủ đề/môn học học sinh cần cố gắng thêm",\n'
' "analytics_summary": "Viết 1 câu nhận xét ngắn gọn về tư duy của học sinh trong lượt chat này",\n'
' "recommendations": ["Hành động 1", "Hành động 2"]\n'
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
            f"⚠️ LƯU Ý CUỐI: Phải kết thúc bằng khối ```json-data ... ``` như đã quy định."
        )
        
        # Cập nhật: Thêm generation_config để giảm nhiệt độ (temperature=0.3)
        # Giúp model viết công thức Toán/Hóa chuẩn hơn, ít bịa đặt
        response = current_chat.send_message(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=2048
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




