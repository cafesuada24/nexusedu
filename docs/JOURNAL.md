# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

---

## Tuần 1 — 05/04/2026

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Project Setup**: Khởi tạo cấu trúc project với `uv`, thiết lập logging hooks cho AI và cấu hình môi trường.
- **Initial UI/API**: Xây dựng khung giao diện cơ bản và các endpoint API đầu tiên cho việc query dữ liệu.
- **Agent Prototype**: Triển khai agent loop cơ bản sử dụng LangChain và GPT-4o để thực hiện các câu truy vấn SQL đơn giản.
- **ETL Scripts**: Viết script ban đầu để import dữ liệu mẫu từ SIS và LMS.

### Khó nhất tuần này
- **Cấu trúc Folder**: Phải cân nhắc nhiều lần giữa việc gộp chung hay tách riêng frontend/backend để tối ưu cho việc phát triển song song.
- **SQL Generation**: Model đôi khi tạo ra các câu lệnh SQL không tương thích với DuckDB (local engine đang dùng).

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Gemini CLI | Setup boilerplate và quản lý dependencies | Tiết kiệm 50% thời gian cấu hình |
| Claude Code | Debug logic SQL generation | Phát hiện sớm các lỗi cú pháp DuckDB |

### Học được
- Cách quản lý dependency hiệu quả hơn với `uv`.
- Tầm quan trọng của việc định nghĩa rõ schema DB ngay từ đầu cho AI Agent.

### Nếu làm lại, sẽ làm khác
- Thiết kế hệ thống prompt linh hoạt hơn thay vì hard-code trong code.

### Kế hoạch tuần tới
- Cải thiện độ chính xác của SQL Agent.
- Xây dựng dashboard hiển thị các chỉ số cơ bản.

---

## Tuần 2 — 12/04/2026

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Refactor Agent with BAML**: Chuyển từ LangChain sang BAML để kiểm soát schema output tốt hơn và giảm thiểu lỗi format của LLM.
- **Data Router & Alerts**: Triển khai các router xử lý dữ liệu thực tế và hệ thống cảnh báo (Alerts) dựa trên điểm số sinh viên.
- **PII Masking**: Thêm module nhận diện và che giấu thông tin cá nhân (PII) nhạy cảm trước khi gửi dữ liệu lên LLM.
- **Authentication**: Tích hợp FastAPI Users để quản lý đăng nhập và bảo mật API.

### Khó nhất tuần này
- **Migration sang BAML**: Việc thay đổi toàn bộ logic gọi LLM sang framework mới tốn nhiều thời gian kiểm thử lại.
- **PII Performance**: Module che thông tin chạy khá chậm trên tập dữ liệu lớn, cần tối ưu hóa bằng regex kết hợp NLP.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| BAML | Định nghĩa interface cho LLM | Code sạch hơn, type-safety tốt hơn |
| Claude Code | Refactor logic che PII | Tăng độ chính xác của việc nhận diện tên và email |

### Học được
- BAML giúp giảm thiểu "prompt leakage" và đảm bảo output luôn đúng format JSON mong muốn.
- Không nên gửi toàn bộ DB schema cho LLM mà chỉ gửi những table liên quan (schema-on-demand).

### Nếu làm lại, sẽ làm khác
- Sử dụng connection pooling cho DB ngay từ đầu để tránh overhead.

### Kế hoạch tuần tới
- Xây dựng Kanban board cho việc quản lý các trường hợp cần hỗ trợ.
- Tích hợp email generation tự động.

---

## Tuần 3 — 19/04/2026

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Kanban Board V1**: Triển khai giao diện Kanban để theo dõi trạng thái hỗ trợ sinh viên (Accepted, Contacted, Resolved).
- **Email Generation Node**: Thêm node AI tự động soạn thảo email dựa trên bối cảnh cảnh báo của sinh viên (điểm thấp, nghỉ học nhiều).
- **LangGraph Integration**: Chuyển đổi Agent sang mô hình Graph để xử lý các workflow phức tạp như: Planner -> Executor -> Reviewer.
- **Mock Data Generator**: Viết script tạo dữ liệu giả lập phong phú để test các edge cases trên giao diện.

### Khó nhất tuần này
- **LangGraph State Management**: Việc quản lý state giữa các node trong graph rất phức tạp, dễ dẫn đến loop vô hạn nếu stop condition không tốt.
- **UI Sync**: Đồng bộ trạng thái Kanban với database SQL thực tế thông qua API.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| LangGraph | Xây dựng logic workflow | Cho phép agent thực hiện nhiều bước suy nghĩ |
| Cursor | Code UI Kanban với Tailwind | Giao diện kéo thả mượt mà |

### Học được
- State trong LangGraph cần được thiết kế tối giản, tránh lưu quá nhiều dữ liệu thừa làm chậm quá trình inference.
- Sử dụng `exponential backoff` khi gọi API của LLM để tránh rate limit.

### Nếu làm lại, sẽ làm khác
- Đơn giản hóa workflow thay vì cố gắng dùng quá nhiều node trung gian không cần thiết.

### Kế hoạch tuần tới
- Implement hệ thống Gamification (tích lũy điểm cho cố vấn).
- Hoàn thiện trang thông tin chi tiết sinh viên (Student Detail Modal).

---

## Tuần 4 — 26/04/2026

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Gamification Engine**: Triển khai hệ thống Point Ledger để ghi nhận điểm thưởng cho advisor mỗi khi xử lý case.
- **Student Profile Modal**: Thay thế side drawer cũ bằng modal chi tiết sinh viên, tích hợp lịch sử học tập và biểu đồ xu hướng.
- **Localization (V1)**: Bắt đầu Việt hóa các label chính trên dashboard và trang quản lý case.
- **Auto-save Drafts**: Thêm tính năng tự động lưu bản thảo email (debounced save) để tránh mất dữ liệu khi đang soạn thảo.

### Khó nhất tuần này
- **Race Condition**: Khi nhiều advisor cùng xử lý một case, phát sinh lỗi ghi đè dữ liệu. Phải áp dụng Optimistic Concurrency Control (OCC).
- **Gamification Logic**: Tính toán điểm thưởng sao cho công bằng (ví dụ: case khó điểm cao hơn).

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Thiết kế thuật toán tính điểm | Logic ổn định, dễ mở rộng |
| Gemini CLI | Debug lỗi concurrency | Phát hiện lỗi thiếu version field trong DB |

### Học được
- OCC là giải pháp đơn giản nhưng hiệu quả để xử lý xung đột dữ liệu trong hệ thống phân tán.
- Giao diện người dùng cần phản hồi trạng thái "Saved" rõ ràng để tạo cảm giác an tâm.

### Nếu làm lại, sẽ làm khác
- Thiết kế hệ thống Gamification dưới dạng Microservice/Event-driven từ đầu để không làm chậm logic chính.

### Kế hoạch tuần tới
- Hoàn thiện hệ thống quản lý lịch làm việc của Advisor.
- Tích hợp lịch hẹn (Appointments).

---

## Tuần 5 — 03/05/2026

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Advisor Scheduling**: Triển khai CRUD cho Working Hours và Date-off. Tự động tính toán các slot trống.
- **Appointment System**: Xây dựng logic đặt lịch hẹn giữa sinh viên và cố vấn, bao gồm kiểm tra xung đột thời gian (conflict detection).
- **Outbox Pattern**: Áp dụng Outbox pattern để đảm bảo tính nhất quán giữa Database và các dịch vụ bên thứ ba (như gửi email thực).
- **Admin Dashboard**: Thêm trang quản lý tổng thể dành cho Admin để theo dõi hiệu suất của toàn bộ đội ngũ cố vấn.

### Khó nhất tuần này
- **Algorithm Optimization**: Thuật toán tìm slot trống chạy chậm khi số lượng advisor lớn. Phải tối ưu bằng cách index thời gian và xử lý ở tầng DB.
- **Outbox Processor**: Việc polling liên tục vào database để xử lý event cần được cấu hình tần suất hợp lý để không gây quá tải.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Tối ưu hóa thuật toán tìm slot | Giảm thời gian query từ 500ms xuống còn 50ms |
| Gemini CLI | Viết migrations và testcases cho hệ thống lịch | Đảm bảo độ phủ test 80% |

### Học được
- Việc tách biệt Command (Đặt lịch) và Query (Xem lịch trống) giúp hệ thống dễ mở rộng hơn (CQRS).
- Outbox pattern là "cứu cánh" cho việc xử lý các task bất đồng bộ mà vẫn đảm bảo data integrity.

### Nếu làm lại, sẽ làm khác
- Sử dụng Redis để cache các slot trống thay vì query trực tiếp SQL mỗi lần.

### Kế hoạch tuần tới
- Mobile Optimization cho toàn bộ dashboard.
- Real-time notifications qua Websocket.

---

## Tuần 6 — 12/05/2026 (Hiện tại - Thứ 3)

**Thành viên:** Hồ Sỹ Minh Hà, Đặng Hồ Hải, Trịnh Đức An

### Đã làm
- **Mobile-First Refactor**: Tối ưu hóa Kanban, biểu đồ và các bảng dữ liệu cho màn hình nhỏ (hỗ trợ snap scrolling, responsive typography).
- **Websocket Real-time**: Tích hợp Websocket thông báo ngay lập tức cho Advisor khi có case mới hoặc thay đổi trạng thái.
- **LangGraph Removal**: Quyết định gỡ bỏ LangGraph để thay bằng deterministic prompt chain, giúp giảm 40% chi phí token và tăng tốc độ phản hồi 2x.
- **Infrastructure Upgrade**: Nâng cấp toàn bộ ID sang UUIDv7 để tối ưu hiệu suất sắp xếp và chuẩn bị cho việc mở rộng DB sau này.

### Khó nhất tuần này
- **UI Consistency on Mobile**: Việc làm cho một Dashboard phức tạp với nhiều biểu đồ hiển thị tốt trên điện thoại là một thử thách lớn về thiết kế CSS.
- **Websocket Stability**: Xử lý reconnection logic và heartbeat để duy trì kết nối ổn định trên môi trường mạng không dây.

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Gemini CLI | Refactor code từ LangGraph sang Prompt Chain | Chuyển đổi an toàn, không làm hỏng logic hiện có |
| Claude Code | Viết CSS Tailwind cho responsive layout | Giao diện mobile chuyên nghiệp, hiện đại |

### Học được
- Đôi khi "Less is More": Việc gỡ bỏ một framework phức tạp (LangGraph) lại giúp sản phẩm ổn định và nhanh hơn cho use-case hiện tại.
- UUIDv7 thực sự hữu ích khi cần cả tính duy nhất toàn cầu và khả năng sắp xếp theo thời gian tự nhiên.

### Nếu làm lại, sẽ làm khác
- Tập trung vào Mobile-first ngay từ tuần 1 thay vì đến tuần cuối mới tối ưu.

### Kế hoạch tiếp theo (Cuối tuần)
- Hoàn thiện báo cáo cuối kỳ và video demo sản phẩm.
- Stress test hệ thống với 1000 users ảo.
- Đóng gói sản phẩm để chuẩn bị bàn giao.
