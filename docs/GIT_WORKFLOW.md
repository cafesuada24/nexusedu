# Quy trình Git & Branching

Tài liệu này định nghĩa **quy trình làm việc với Git** bắt buộc cho toàn đội. Tuân thủ nghiêm giúp tránh conflict, mất code, và giúp việc review dễ hơn.

## Mô hình Branching

Chúng ta sử dụng mô hình **Feature Branch Workflow**:

```
main                    ← Branch chính, luôn ở trạng thái có thể deploy
 └── dev                ← Branch tích hợp, nơi merge các feature trước khi lên main
      ├── feature/...   ← Branch phát triển tính năng mới
      ├── fix/...       ← Branch sửa lỗi
      └── chore/...     ← Branch dọn dẹp code, cập nhật tài liệu
```

## Đặt tên Branch

Cú pháp: `<loại>/<tên-ngắn-gọn>`

| Loại | Dùng khi | Ví dụ |
| :--- | :--- | :--- |
| `feature/` | Thêm tính năng mới | `feature/nudge-email-engine` |
| `fix/` | Sửa lỗi | `fix/csv-parser-encoding` |
| `chore/` | Cập nhật docs, cấu hình | `chore/update-prd` |
| `refactor/` | Tái cấu trúc code | `refactor/agent-nodes` |

## Quy trình làm việc hàng ngày

### 1. Bắt đầu một task mới

```bash
# Đảm bảo branch dev của bạn cập nhật mới nhất
git checkout dev
git pull origin dev

# Tạo branch mới từ dev
git checkout -b feature/ten-tinh-nang-cua-ban
```

### 2. Trong quá trình làm việc

```bash
# Commit thường xuyên, mỗi commit là một đơn vị thay đổi có nghĩa
git add .
git commit -m "feat: thêm baseline detection logic cho sinh viên"

# Push lên remote để backup và team có thể thấy tiến độ
git push origin feature/ten-tinh-nang-cua-ban
```

### 3. Cú pháp Commit Message

Tuân thủ **Conventional Commits**: `<loại>: <mô tả ngắn bằng tiếng Anh>`

| Loại | Ý nghĩa | Ví dụ |
| :--- | :--- | :--- |
| `feat:` | Tính năng mới | `feat: add student risk flagging` |
| `fix:` | Sửa lỗi | `fix: handle empty CSV file` |
| `docs:` | Cập nhật tài liệu | `docs: update REPO_STRUCTURE` |
| `refactor:` | Cải thiện code, không đổi behavior | `refactor: extract baseline logic` |
| `test:` | Thêm/sửa test | `test: add unit test for risk engine` |
| `chore:` | Cấu hình, dependencies | `chore: add sendgrid to requirements` |

### 4. Tạo Pull Request (PR) vào `dev`

Khi hoàn thành task, tạo PR lên GitHub với tiêu đề và mô tả theo chuẩn trong `AGENTS.md`:

```
## Summary
Mô tả ngắn gọn những gì đã thay đổi và tại sao.

## Changes
- src/etl/csv_parser.py: Thêm parser cho file CSV từ Canvas
- tests/test_csv_parser.py: Thêm unit test tương ứng
```

### 5. Merge vào `main`

Merge từ `dev` vào `main` sau khi đã test trên `dev`.

## Setup ban đầu (chạy một lần)

```bash
# Clone repo
git clone https://github.com/a20-ai-thuc-chien/A20-App-007.git
cd A20-App-007

# Cài git hooks (BẮT BUỘC, xem AGENTS.md)
bash scripts/setup_hooks.sh

# Cấu hình môi trường
cp .env.example .env
# Điền API keys của bạn vào file .env
```
