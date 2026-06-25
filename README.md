# AgentGuard - Trình Chặn và Phê Duyệt Lệnh Terminal (Nhị Phân Native)

Hệ thống quản lý và chặn các câu lệnh thực thi từ Terminal hoặc các AI Agent (như Antigravity hoặc Claude Code) trên Windows, yêu cầu phê duyệt thủ công qua giao diện Web di động (mobile-first) trước khi thực thi thực tế.

Dự án đã được cấu hình nâng cấp toàn diện, chuyển đổi cơ chế chặn từ các tệp script kịch bản (`.cmd`/`.bat`) sang các tệp nhị phân thực thi thực sự (`.exe`). Sự thay đổi này giúp sửa hoàn toàn lỗi `%1 is not a valid Win32 application` khi các AI Agent gọi tiến trình chạy lệnh thông qua hàm hệ thống.

---

## Cấu trúc và Thành phần chính

### 1. Trình chặn nhị phân (`wrapper.cs` -> `bin/`)
Chương trình C# siêu nhẹ làm trình bọc (wrapper) chặn lệnh:
* Tự động nhận diện xem nó đang được gọi dưới dạng `powershell.exe` hay `cmd.exe` (qua tên file chạy).
* Chuyển tiếp các đối số dòng lệnh một cách an toàn sang tập lệnh Python `shell_interceptor.py`.
* Trả về mã thoát (exit code) chính xác của câu lệnh sau khi được duyệt và chạy.
* Được biên dịch thành `bin/powershell.exe` và `bin/cmd.exe`.

### 2. Thiết lập Môi trường bảo vệ (`start-secured-env.bat`)
Cấu hình trỏ trực tiếp biến shell hệ thống `%COMSPEC%` và `%CLAUDE_CODE_SHELL%` sang trình chặn nhị phân mới:
* `set COMSPEC=bin\cmd.exe`
* `set CLAUDE_CODE_SHELL=bin\cmd.exe`
* Đưa thư mục `bin` lên đầu biến môi trường `PATH`.

---

## Hướng dẫn vận hành dự án

Để chạy hệ thống bảo vệ toàn diện máy tính của bạn:

1. **Khởi động server quản lý**: Nhấp đúp chạy file `run.bat` để bật server Flask của AgentGuard lên (nó sẽ hiển thị mã QR để bạn quét truy cập bằng điện thoại).
2. **Mở môi trường bảo vệ**: Nhấp đúp file `start-secured-env.bat` để mở cửa sổ dòng lệnh màu đen (được bảo vệ).
3. **Khởi chạy AI Agent từ cửa sổ đó**:
   * Nếu dùng **Antigravity**: Bạn gõ lệnh `antigravity` rồi nhấn Enter để khởi chạy.
   * Nếu dùng **Claude Code**: Bạn gõ lệnh `claude` rồi nhấn Enter để khởi chạy.
   * Nếu dùng **Cursor / VS Code**: Gõ `cursor .` hoặc `code .` để mở trình soạn thảo lên.

---

## Cơ chế kiểm thử & Hoạt động thực tế

* **Khi gọi một lệnh chưa có trong Whitelist (ví dụ: `git commit`, `csc`...)**: Lệnh sẽ tự động bị chặn lại, trạng thái terminal chuyển thành "Đang chờ duyệt..." và gửi yêu cầu lên Web/Mobile. Sau khi bạn ấn **Phê Duyệt**, lệnh sẽ tiếp tục thực thi.
* **Cơ chế tự động duyệt (Auto-approve)**: Khi chạy lệnh nằm trong danh sách Whitelist (như `git status`, `echo`, `dir`...), trình bọc bóc tách được lệnh con và tự động cho phép chạy (auto-approved), không cần người dùng thao tác.
