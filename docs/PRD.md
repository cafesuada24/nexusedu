# PRD: The Activation Engine

## 1. Định nghĩa Vấn đề: The Activation Gap

Vấn đề cốt lõi của các trường đại học không phải là thiếu dữ liệu track sinh viên, mà là **thiếu hành động**. Hiện tại, vòng lặp can thiệp đang bị đứt gãy:

*   **Cố vấn học tập (AA):** Nhận danh sách sinh viên rủi ro quá dài, không có thời gian "cold-call" từng người, dẫn đến tâm lý chờ đợi sinh viên tự tìm đến.
*   **Sinh viên:** Không nhận thức được mình đang trượt dốc (vì điểm chưa quá tệ) hoặc cảm thấy xấu hổ, sợ hãi khi phải chủ động xin giúp đỡ.
*   **Hệ thống cũ:** Gửi các email cảnh báo hàng loạt (Spray-and-pray) khô khan, khiến sinh viên lo lắng và né tránh thay vì hành động.

**Giả thuyết:** Nếu chúng ta biến sinh viên thành **người chủ động khởi đầu** cuộc hội thoại bằng cách gửi cho họ những thông tin thấu cảm, cá nhân hóa về chính xu hướng của họ (Pattern-based), chúng ta sẽ chuyển đổi "danh sách rủi ro bị động" thành "nhu cầu hỗ trợ chủ động". Cố vấn chỉ cần làm việc với những người thực sự muốn được giúp đỡ.

---

## 2. Core Value Proposition

1.  **Student-Activated Intervention:** Sinh viên nhận được phân tích về chính mình ("Điểm Quiz tuần này của bạn thấp hơn 30% so với thông lệ - đây là điều bất thường"), thúc đẩy sự tự nhận thức và tự nguyện tìm đến cố vấn.
2.  **Zero-Friction cho Cố vấn:** Loại bỏ hoàn toàn công việc phân tích dữ liệu thủ công. Cố vấn không còn phải tìm sinh viên mà chỉ tiếp nhận những lịch hẹn đã được chốt sẵn kèm **bản tóm tắt bối cảnh rủi ro** do AI soạn.
3.  **Cá nhân hóa theo Baseline cá nhân:** AI không so sánh sinh viên với trung bình lớp, mà so sánh sinh viên với **chính lịch sử của họ** để phát hiện những sự "trượt dốc thầm lặng".

---

## 3. Workflow

Hệ thống hoạt động theo vòng lặp 4 bước tự động:

1.  **AI Ingest:** Nhận file CSV từ LMS (Canvas/Moodle) và SIS (Hệ thống điểm).
2.  **Pattern Detection:** AI xác định "Baseline" (ngưỡng bình thường) của từng sinh viên và gắn cờ khi có sự lệch chuẩn (vd: Bình thường nộp bài 100%, 2 tuần nay chỉ nộp 40%).
3.  **The Nudge (Lời nhắc thấu cảm):** AI soạn và gửi email cá nhân hóa (AA duyệt 1-click). Email không trừng phạt mà mang tính tò mò/hỗ trợ kèm link đặt lịch (Calendly).
4.  **AA Action (Can thiệp tập trung):** AA nhận lịch hẹn kèm một **Student Brief** (3 câu tóm tắt vấn đề cốt lõi) để sẵn sàng giải quyết ca khó trong 30 giây chuẩn bị.

---

## 4. Functional Requirements

### 4.1. Động cơ Nhận diện Xu hướng (Pattern Recognition Engine)
*   **Baseline Detection:** AI tự động thiết lập ngưỡng hoạt động bình thường cho từng cá nhân sinh viên.
*   **Deviation Flagging:** Gắn cờ khi dữ liệu mới lệch khỏi ngưỡng (điểm quiz giảm, tần suất login LMS tụt sâu, bỏ lỡ bài tập).
*   **Insight Generation:** Viết 2-3 câu giải thích rõ: "Bạn đang thay đổi như thế nào so với chính bạn tuần trước/tháng trước".

### 4.2. Hệ thống Nudge & Phê duyệt (Admin Dashboard)
*   **Review Mode:** AA có một màn hình "Hàng đợi" để xem nhanh 50 email AI đã soạn và bấm "Duyệt tất cả" hoặc chỉnh sửa nhanh.
*   **Tone Control:** Đảm bảo giọng văn luôn là "Hỗ trợ/Tò mò" (Curiosity-based), tuyệt đối không dùng từ ngữ "Cảnh báo/Học vụ/Rủi ro" để tránh gây áp lực tâm lý.

### 4.3. Action Inbox cho Cố vấn (Advisor Interface)
*   Thay thế Dashboard phức tạp bằng một **Action Queue** tối giản.
*   Chỉ hiển thị các sinh viên đã phản hồi hoặc đã đặt lịch.
*   **AI Student Brief:** Tóm tắt 3 câu về bối cảnh (vd: "Mai thường học giỏi nhưng 2 tuần nay bỏ 3 bài quiz môn Lý, có dấu hiệu burnout").

---

## 5. Success Metrics

*   **Tỉ lệ Sinh viên Tự kết nối (Self-Referral Rate):** % sinh viên rủi ro tự đặt lịch hẹn sau khi nhận Nudge (Target: >25%).
*   **Hiệu suất Họp Cố vấn (Meeting Efficiency):** % các cuộc hẹn dẫn đến hành động thực tế, thay vì các cuộc hẹn "báo động giả" (Target: >70%).
*   **Tỉ lệ Can thiệp Sớm:** % sinh viên được can thiệp trước tuần thứ 10 của học kỳ.
*   **Nudge Open/Click Rate:** Tỉ lệ mở và click vào link hỗ trợ trong email.

---

## 6. Ràng buộc Kỹ thuật & Bảo mật

*   **Quyền riêng tư (FERPA):** Dữ liệu sinh viên chỉ xử lý phía server, không lộ thông tin nhạy cảm qua URL hoặc Client-side JS.
*   **Kiểm soát Tần suất:** Tối đa 1 Nudge/sinh viên/tuần để tránh gây "mệt mỏi vì thông báo" (Alert fatigue).
*   **Khả năng mở rộng:** Hệ thống xử lý CSV linh hoạt để không phụ thuộc vào việc tích hợp API trực tiếp với hệ thống cũ của trường trong giai đoạn MVP.
