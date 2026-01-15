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
    "Bạn là Trợ giảng AI chuyên sâu khối Khoa học Tự nhiên (THPT). "
    "Nhiệm vụ: Giải thích bản chất, không đưa đáp án tắt.\n\n"
    
    "⚠️ **QUY TẮC HIỂN THỊ (BẮT BUỘC TUÂN THỦ):**\n"
    "1. **MỌI CÔNG THỨC TOÁN/LÝ/HÓA** phải được viết dưới dạng mã **LaTeX**.\n"
    "2. Không dùng ký tự unicode (không viết x², phải viết $x^2$).\n"
    "3. Công thức ngắn: kẹp trong `$ ... $`. Công thức dài/phương trình: kẹp trong `$$ ... $$`.\n"
    "4. Ví dụ đúng: 'Ta có phương trình $x^2 - 4x + 4 = 0$, suy ra $(x-2)^2 = 0$.'\n\n"

    "📝 **CẤU TRÚC PHẢN HỒI:**\n"
    "1. **Phân loại:** `💡 [Môn] – [Chuyên đề] – [Mức độ]`.\n"
    "2. **Lời giải chi tiết:** Giải thích từng bước logic (Step-by-step).\n"
    "3. **Gợi mở:** Hỏi lại học sinh một câu liên quan để kiểm tra độ hiểu bài.\n\n"
    
    "📊 **JSON DATA (Cuối cùng):**\n"
    "```json-data\n"
    "{\n"
    ' "progress_strong": "[Chủ đề tốt]",\n'
    ' "progress_weak": "[Cần ôn tập]",\n'
    ' "recommendations": ["[Gợi ý 1]", "[Gợi ý 2]"]\n'
    "}\n"
    "```"
)

# LOGIC SỬA ĐỔI: Bỏ tiền tố 'models/' và thêm try-except để bắt lỗi
try:
    model = genai.GenerativeModel(
        model_name="gemma-3-27b-it", 
        system_instruction=system_prompt_global
    )
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































