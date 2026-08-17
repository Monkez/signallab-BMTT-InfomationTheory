# Quy trình phát triển cho AI

1. Kiểm tra `git status` và đọc docs/status.
2. Chốt phạm vi, cập nhật `agents/STATUS.md` khi bắt đầu/kết thúc mốc lớn.
3. Backend: giữ engine độc lập HTTP; thêm test thuật toán và tính tái lập.
4. Frontend: giữ schema khối đồng bộ API; build TypeScript sau thay đổi.
5. Không đưa secret, virtualenv, node_modules hay output build vào git.
6. Dùng `git` cho status/diff/commit/push; không dùng `gh`.
7. Trước bàn giao chạy `test.bat` hoặc pytest + npm build.

