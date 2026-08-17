# Hướng dẫn sử dụng

## Khởi động bản desktop

1. Chạy `setup.bat` ở lần đầu.
2. Chạy `build_app.bat` để tạo `dist\SignalLab\SignalLab.exe`.
3. Chạy `run.bat` hoặc mở trực tiếp file EXE.

Bản desktop chỉ mở một cửa sổ SignalLab, không cần Node.js/Vite khi sử dụng và không mở terminal. Khi sao chép sang máy khác, phải sao chép cả thư mục `dist\SignalLab`, bao gồm `_internal`; không chỉ sao chép riêng EXE. Máy Windows đích cần Microsoft Edge WebView2 Runtime, vốn có sẵn trên Windows 10/11 được cập nhật.

`run_dev.bat` chỉ dành cho lập trình viên. Nó chạy Vite tại port 5173, nên nếu đóng cửa sổ dev server thì trình duyệt sẽ báo WebSocket mất kết nối và `ERR_CONNECTION_REFUSED`. Đây không phải cơ chế chạy của bản EXE.

Yêu cầu để build: Windows 10/11, Python 3.11+ và Node.js 20+. Lần chạy `setup.bat`/`build_app.bat` đầu tiên cần Internet để tải thư viện. Máy chỉ chạy thư mục release không cần Python hoặc Node.js.

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
