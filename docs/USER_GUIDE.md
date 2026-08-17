# Hướng dẫn sử dụng

## Khởi động

Chạy `setup.bat` ở lần đầu, sau đó chạy `run.bat`. Hai dịch vụ backend/frontend được mở trong cùng một cửa sổ PowerShell quản lý; đóng cửa sổ để dừng.

Yêu cầu tối thiểu: Windows 10/11, Python 3.11+ và Node.js 20+. Lần chạy `setup.bat` đầu tiên cần Internet để tải thư viện.

## Tạo mô phỏng

1. Chọn khối trong thanh bên hoặc dùng sơ đồ mẫu.
2. Kéo từ cổng bên phải của một khối sang cổng bên trái khối kế tiếp.
3. Chọn khối để sửa tên và tham số. Với Python Block, sửa hàm `process` theo mẫu.
4. Chọn số trial, số worker, seed và thiết bị.
5. Nhấn **Run simulation**. Kết quả cập nhật trong panel bên phải.

## Cấu hình Monte-Carlo

- `Trials`: số lần lặp độc lập.
- `Workers = 0`: hệ thống tự chọn; đặt `1` để debug dễ hơn.
- `Seed`: cho kết quả tái lập.
- `Auto`: chọn GPU nếu có và phù hợp, nếu không dùng CPU.

## Lưu dự án

Nút Export tải file `.json`; Import đọc lại file đó. Không lưu code tùy biến từ nguồn không tin cậy rồi chạy.
