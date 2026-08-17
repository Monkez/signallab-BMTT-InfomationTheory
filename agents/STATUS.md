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
- Quyết định: code tùy biến được xem là trusted-local code trong MVP.
