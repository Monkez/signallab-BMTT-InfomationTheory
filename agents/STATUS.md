# Trạng thái dự án

- Ngày cập nhật: 2026-08-17
- Giai đoạn: bản desktop Windows hoàn tất và đã kiểm thử
- Kiến trúc: React/TypeScript + React Flow, FastAPI/Python, NumPy/CuPy tùy chọn.
- Đã hoàn thành: đặc tả, engine DAG, Monte-Carlo CPU/GPU tùy chọn, REST jobs, canvas React Flow, editor Python, dashboard và script Windows.
- Kiểm thử: backend 3/3 pass; frontend production build pass; browser E2E 100 trials pass, không có console error.
- Đã hoàn thành: giao diện sáng trung tính; favicon; PyWebView/WebView2 launcher; PyInstaller onedir; `SignalLab.exe`; tách `run.bat` desktop và `run_dev.bat` Vite.
- Kiểm thử desktop: EXE mở thành công, 100 trial hoàn tất, BER 1.453e-3, multiprocessing CPU hoạt động trong bản frozen.
- Hoàn tất cập nhật: typography dễ đọc hơn, logo/icon SVG đồng bộ, phím `Delete` xóa block đã chọn; EXE đã build lại tại `dist\\SignalLab\\SignalLab.exe`.
- Hoàn tất: port orientation theo block (`standard`/`reversed`), lưu trong project JSON, UI test xác nhận input chuyển sang phải.
- Hoàn tất sửa lỗi: React Flow đo lại node internals sau khi đảo port, 2/7 edge path liên quan đã thay đổi đúng trong UI test; PyInstaller nhúng `assets/app.ico` thay icon Python mặc định.
- Quyết định: code tùy biến được xem là trusted-local code trong MVP.
- Cập nhật hiện tại: hoàn tất SNR sweep Monte-Carlo với stopping criteria theo từng điểm; AWGN tham chiếu `context.snr_db`; thêm biểu đồ BER SVG cho Sink và Experiment; chọn block ngay khi drag; sidebar hai bên có ẩn/hiện và resize.
- Kiểm thử mới nhất: backend 3/3 pass, frontend `npm run build` pass, browser E2E xác nhận drag-select, sidebar toggle, SNR sweep, Sink chart và port reversal. `build_app.bat` đã chạy thành công; EXE phát hành đã cập nhật.
- Hoàn tất mốc hiện tại: Console dock dưới canvas có resize/clear; header/library đã tinh gọn; graph mẫu được bố trí hai hàng; bổ sung block nguồn/mã nguồn/mã kênh/điều chế/kênh/receiver/sink; engine trả `sink_metrics` cho các Sink trực quan. Build desktop mới đã thành công.
- Hoàn tất mốc tiếp theo: đã bỏ Run Simulation khỏi topbar; Console giữ nguyên trạng thái ẩn khi chạy; Python Block có API tự nhiên `process(signal, params) -> array`, vẫn tương thích API cũ và scheduler tự xử lý song song hóa. Test hiện tại 5/5 pass; EXE đã build lại.
- Hoàn tất mốc realtime/export: dashboard nhận `snr_points` theo từng batch để vẽ BER trực tiếp; biểu đồ có Copy/PNG, bảng có Copy/CSV/PNG. Engine biên dịch graph plan một lần, sinh seed theo batch, tái sử dụng process pool và tự tránh process overhead với workload nhỏ. Đã xác nhận backend 5/5 pass, frontend production build pass và `dist\\SignalLab\\SignalLab.exe` đã build lại.
