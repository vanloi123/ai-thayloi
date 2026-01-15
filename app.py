import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, session
import os
import json
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
# Cấu hình Session cho Flask
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Chưa thiết lập GOOGLE_API_KEY trong Environment Variables!")

# --- LOGIC SỬA ĐỔI: Bỏ dòng ép buộc version cũ để tránh lỗi ---
# os.environ["GOOGLE_GENERATIVE_AI_API_VERSION"] = "v1beta" 

genai.configure(api_key=api_key)

# --- DEBUG: KIỂM TRA MODEL CÓ SẴN (Logic mới thêm vào) ---
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

# System Prompt 
system_prompt_global = (
   "Bạn là **Thầy/Cô Trợ giảng AI** tâm huyết, có 20 năm kinh nghiệm dạy THPT, luôn xưng hô Thầy/Cô, am hiểu tâm lý học sinh và phương pháp giảng dạy hiện đại. "
    "Phong cách: Gần gũi, ân cần nhưng gãy gọn. Xưng hô 'Thầy' hoặc 'Cô' và 'em'.\n\n"

    "⛔ **QUY TẮC CẤM (ĐỂ GIỐNG NGƯỜI THẬT - QUAN TRỌNG):**\n"
    "1. **TUYỆT ĐỐI KHÔNG** in ra các tiêu đề phân đoạn như: 'PHẦN 1', 'PHẦN 2', 'TƯƠNG TÁC SƯ PHẠM', 'LỜI GIẢI'.\n"
    "2. Không chào hỏi sáo rỗng kiểu robot (như 'Rất vui được hỗ trợ...'). Hãy đi thẳng vào vấn đề một cách tự nhiên.\n"
    "3. Không đưa đáp án ngay. Hãy hỏi gợi mở (Socratic method).\n\n"
    "2. Không bịa đặt phân loại môn học khi người dùng chỉ chào hỏi.\n\n"
    
    "⚠️ **QUY TẮC HIỂN THỊ (BẮT BUỘC):**\n"
    "1. **TOÁN/LÝ/HÓA:** Dùng mã **LaTeX** cho mọi công thức ($...$ hoặc $$...$$).\n"
    "2. **VĂN/SỬ/ĐỊA:** Trình bày thoáng, in đậm từ khóa.\n\n"

    "📝 **CẤU TRÚC TRẢ LỜI MONG MUỐN:**\n"
    "1. Dòng 1: `💡 Phân loại: Môn [Môn] – [Chủ đề] – [Cấp độ]` (Luôn bắt đầu bằng dòng này).\n"
    "2. Xuống dòng và nói chuyện trực tiếp với học sinh. Giải thích vấn đề, đặt câu hỏi gợi ý.\n"
    "3. Cuối cùng (ẩn): Block JSON dữ liệu.\n\n"

    "📊 **JSON DATA (BẮT BUỘC Ở CUỐI CÙNG):**\n"
    "```json-data\n"
    "{\n"
    ' "progress_strong": "[Chủ đề tốt]",\n'
    ' "progress_weak": "[Cần cải thiện]",\n'
    ' "analytics_summary": "[Nhận xét ngắn về tư duy]",\n'
    ' "recommendations": ["[Gợi ý 1]", "[Gợi ý 2]"]\n'
    "}\n"
    "```"
)
# LOGIC SỬA ĐỔI: Bỏ tiền tố 'models/' và thêm try-except để bắt lỗi
try:
    model = genai.GenerativeModel(
        model_name="gemma-3-27b-it" 
    )
except Exception:
    try:
        model = genai.GenerativeModel("gemma-3-27b")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")

# Biến toàn cục lưu phiên chat
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
    """Xử lý Reset khi người dùng chọn môn mới"""
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
        
        # Tóm tắt lịch sử
        history_data = session.get('learning_history', [])
        recent_history = history_data[-3:] 
        
        history_str = "\n".join([f"Học sinh: {h['user']} | AI: {h['ai_summary']}" for h in recent_history])
        
        # --- KỸ THUẬT NHÚNG SYSTEM PROMPT VÀO TIN NHẮN ---
        # Để đảm bảo hoạt động trên các phiên bản thư viện cũ chưa hỗ trợ system_instruction
        full_prompt = (
            f"{system_prompt_global}\n\n"
            f"=== LỊCH SỬ HỘI THOẠI ===\n{history_str}\n\n"
            f"=== CÂU HỎI MỚI ===\n: {user_message}"
        )
        
        response = current_chat.send_message(full_prompt) 
        
        if not response.text:
             return jsonify({"reply": "Lỗi: AI không phản hồi."})       
        
        # Lưu vào lịch sử (Lọc bỏ phần JSON)
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




































