# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

> Cập nhật **bất cứ khi nào** nhóm ra quyết định kỹ thuật quan trọng hoặc thay đổi hướng đi.

---

## Các Quyết Định Kỹ Thuật (ADRs)

### [ADR-1] Chuyển đổi từ LangChain sang BAML — 12/04/2026

**Bối cảnh:** LLM thường trả về sai format JSON hoặc bị "prompt leakage". LangChain khó kiểm soát schema output chặt chẽ.

**Các lựa chọn đã xem xét:**
- Tiếp tục dùng LangChain và viết thêm các parser regex.
- Sử dụng BAML để định nghĩa data models và type-safety trực tiếp.

**Quyết định:** Chọn BAML vì nó ép kiểu dữ liệu (type-safety) tốt hơn, code sạch và dễ bảo trì.

**Hệ quả:** Tốn thời gian migrate toàn bộ logic gọi LLM cũ sang BAML nhưng giảm hẳn lỗi parsing format JSON.

---

### [ADR-2] Áp dụng Optimistic Concurrency Control (OCC) — 26/04/2026

**Bối cảnh:** Khi hệ thống có nhiều cố vấn (advisor) cùng thao tác trên 1 case trên Kanban board, có nguy cơ ghi đè dữ liệu (Race Condition).

**Các lựa chọn đã xem xét:**
- Pessimistic Locking: Lock dòng trong database -> Chạy chậm, dễ bị deadlock.
- Optimistic Concurrency Control (OCC): Dùng trường `version` để check conflict.

**Quyết định:** Sử dụng OCC vì phù hợp với tính chất hệ thống phân tán, ít block người dùng.

**Hệ quả:** Cập nhật database schema thêm cột `version` ở các bảng quan trọng và xử lý logic lỗi xung đột (retry/reload) ở UI.

---

### [ADR-3] Sử dụng Outbox Pattern cho Async Tasks — 03/05/2026

**Bối cảnh:** Cần đảm bảo sau khi đặt lịch hẹn thành công (lưu vào database), thông báo/email chắc chắn phải được gửi đi, ngay cả khi dịch vụ gửi email bị sập tạm thời.

**Các lựa chọn đã xem xét:**
- Gửi trực tiếp API trong request: Rủi ro timeout, mất data nếu API bên thứ 3 lỗi.
- Outbox Pattern: Lưu event cần thực hiện vào bảng `outbox` cùng transaction với database, sau đó background worker đọc và thực thi.

**Quyết định:** Chọn Outbox Pattern.

**Hệ quả:** Đảm bảo data integrity tuyệt đối nhưng hệ thống phức tạp hơn do phải chạy thêm background worker để xử lý.

---

### [ADR-4] Gỡ bỏ LangGraph, thay bằng Prompt Chain — 12/05/2026

**Bối cảnh:** Kiến trúc LangGraph hiện tại quá phức tạp, việc quản lý state giữa các node tốn nhiều tài nguyên. Dẫn đến chi phí token cao và độ trễ (latency) chậm do chạy qua nhiều node trung gian không cần thiết.

**Các lựa chọn đã xem xét:**
- Tối ưu state và giảm số vòng lặp trong LangGraph.
- Gỡ bỏ hoàn toàn LangGraph, thay bằng deterministic Prompt Chain.

**Quyết định:** Chuyển sang Prompt Chain theo tiêu chí "Less is More". Đơn giản hóa workflow.

**Hệ quả:** Giảm 40% chi phí token, tốc độ phản hồi tăng x2. Đánh đổi lại là mất đi khả năng loop/agentic phức tạp nhưng hoàn toàn phù hợp với use-case hiện tại.

---

### [ADR-5] Sử dụng UUIDv7 làm Khóa Chính — 12/05/2026

**Bối cảnh:** Cần scale database, chuẩn bị cho hệ thống lớn. UUIDv4 bị phân mảnh index, gây chậm khi truy vấn và sắp xếp dữ liệu theo thời gian.

**Các lựa chọn đã xem xét:**
- Auto-increment ID (Int)
- UUIDv4
- UUIDv7

**Quyết định:** Nâng cấp toàn bộ khóa chính (ID) sang UUIDv7 vì nó giữ được tính chất phân tán (phòng chống đoán ID) nhưng có khả năng tự động sắp xếp theo thời gian (time-ordered).

**Hệ quả:** Chạy script migration để chuyển đổi toàn bộ data cũ sang chuẩn ID mới. 

---

## Phân công Công việc (Sprints)

### Sprint 1 & 2 — 05/04 → 18/04/2026
*Mục tiêu: Setup kiến trúc, UI cơ bản và Data Router.*

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Cấu hình `uv` và thiết lập logging hooks AI | Trịnh Đức An | 07/04 | ✅ Xong |
| Triển khai ETL import dữ liệu từ SIS/LMS | Hồ Sỹ Minh Hà | 10/04 | ✅ Xong |
| Xây dựng UI/API cơ bản | Đặng Hồ Hải | 10/04 | ✅ Xong |
| Refactor từ LangChain sang BAML framework | Trịnh Đức An | 15/04 | ✅ Xong |
| Tích hợp PII Masking Module | Hồ Sỹ Minh Hà | 17/04 | ✅ Xong |
| Tích hợp FastAPI Users Authentication | Đặng Hồ Hải | 18/04 | ✅ Xong |

---

### Sprint 3 & 4 — 19/04 → 02/05/2026
*Mục tiêu: Kanban, Email Node, Gamification và Student Modal.*

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Xây dựng giao diện Kanban Board V1 | Đặng Hồ Hải | 22/04 | ✅ Xong |
| Tạo script Mock Data Generator | Trịnh Đức An | 24/04 | ✅ Xong |
| Node AI tự động soạn thảo Email | Hồ Sỹ Minh Hà | 25/04 | ✅ Xong |
| Hệ thống Gamification & Point Ledger | Trịnh Đức An | 29/04 | ✅ Xong |
| Xử lý OCC Race Condition cho Kanban | Hồ Sỹ Minh Hà | 01/05 | ✅ Xong |
| Student Profile Modal & Auto-save debounce | Đặng Hồ Hải | 02/05 | ✅ Xong |

---

### Sprint 5 & 6 — 03/05 → 12/05/2026
*Mục tiêu: Scheduling, Mobile-first & Tối ưu Hiệu năng.*

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Thuật toán tính toán và đặt Slot Lịch hẹn | Hồ Sỹ Minh Hà | 06/05 | ✅ Xong |
| Tích hợp Outbox Pattern cho DB | Trịnh Đức An | 08/05 | ✅ Xong |
| Responsive UI (Mobile-First) cho màn hình nhỏ | Đặng Hồ Hải | 10/05 | ✅ Xong |
| Nâng cấp UUIDv7 toàn hệ thống | Trịnh Đức An | 12/05 | ✅ Xong |
| Thay thế LangGraph bằng Prompt Chain | Hồ Sỹ Minh Hà | 12/05 | ✅ Xong |
| Real-time Notification qua Websocket | Đặng Hồ Hải | 12/05 | ✅ Xong |

---

## Brainstorming

### Brainstorm: Tối ưu hiển thị Kanban trên Mobile — 08/05/2026

**Câu hỏi:** Làm sao để hiển thị một Kanban board nhiều cột trên màn hình điện thoại (mobile) mà không làm vỡ layout hay gây khó chịu cho trải nghiệm người dùng?

**Các ý tưởng:**
- **Ý tưởng 1 (Đặng Hồ Hải):** Chuyển từ dạng bảng sang dạng danh sách accordion. Khi người dùng bấm vào một trạng thái (New, Accepted...), nó sẽ xổ xuống danh sách sinh viên tương ứng.
- **Ý tưởng 2 (Trịnh Đức An):** Dùng tính năng CSS Snap Scrolling (cuộn theo khấc). Mỗi lần vuốt ngang sẽ tự động "snap" hiển thị trọn vẹn 1 cột duy nhất chiếm toàn màn hình.
- **Ý tưởng 3 (Hồ Sỹ Minh Hà):** Thêm một thanh filter dropdown trên cùng để chọn cột muốn xem, ẩn các cột còn lại đi.

**Phân tích (Pros/Cons):**
| Ý tưởng | Ưu điểm | Nhược điểm |
|---|---|---|
| Accordion List | Tiết kiệm không gian | Không còn cảm giác "Kanban" kéo thả |
| CSS Snap Scrolling | Giữ được form Kanban, vuốt rất mượt | Khó implement thao tác kéo thả card qua lại giữa các cột trên màn hình cảm ứng |
| Dropdown Filter | Dễ code, chắc chắn không vỡ layout | Phải bấm nhiều thao tác để xem tổng quan |

**Kết luận:** Chọn **Ý tưởng 2 (Snap Scrolling)** để làm layout chính vì cảm giác hiện đại và mượt mà. Kết hợp thêm **Ý tưởng 1** cho thao tác chuyển trạng thái (trên mobile thay vì kéo thả thì sẽ bấm nút menu ở card để chọn cột cần chuyển). Sử dụng Tailwind class `snap-x` và `snap-mandatory` để implement.
