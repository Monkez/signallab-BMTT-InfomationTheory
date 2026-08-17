# Kiến trúc SignalLab

## Tổng quan

```text
React + React Flow
  ├─ block library / canvas / property editor
  ├─ Python code editor
  └─ experiment dashboard
             │ REST + polling
FastAPI job service
  ├─ schema validation + DAG compiler
  ├─ job registry + cancellation
  └─ Monte-Carlo scheduler
       ├─ local process workers (NumPy)
       └─ optional GPU worker (CuPy)
             │
       block runtime + metric reducer
```

## Bản desktop Windows

PyWebView tạo cửa sổ native dùng WebView2. Một tiến trình Uvicorn nội bộ phục vụ cả API và frontend production trên loopback với port trống được chọn tự động. PyInstaller gom Python runtime, backend và `frontend/dist` vào thư mục phát hành onedir chứa `SignalLab.exe`. Onedir được chọn để khởi động nhanh và tránh mỗi worker Monte-Carlo phải giải nén lại toàn bộ onefile. Người dùng cuối không chạy Vite, Node.js hoặc hai terminal; Vite chỉ còn dành cho phát triển giao diện qua `run_dev.bat`.

## Mô hình thực thi

Mỗi node nhận `inputs`, `params`, `context` và trả về dictionary các output. Graph được topological-sort một lần. Mỗi trial có seed sinh từ `SeedSequence`, vì vậy lịch worker thay đổi không làm mất khả năng tái lập. Metric của sink được giảm theo phép cộng; BER cuối cùng là tổng bit lỗi chia tổng bit đã so sánh, không phải trung bình BER từng trial.

## Song song CPU/GPU

- CPU: trial độc lập được chia thành chunk và chạy bằng `ProcessPoolExecutor`. `workers=0` nghĩa là tự chọn.
- GPU: runtime thử nạp CuPy và kiểm tra device. Các khối built-in dùng namespace mảng `context.xp`. Bản MVP dùng một GPU worker theo batch nhỏ để tránh nhiều process tranh cùng device.
- Auto: ưu tiên GPU khi khả dụng và graph tương thích, ngược lại dùng CPU; workload nhỏ chạy inline để tránh overhead.

## Python block API

```python
def process(inputs, params, context):
    xp = context.xp
    samples = xp.asarray(inputs["in"])
    gain = float(params.get("gain", 1.0))
    return {"out": samples * gain}
```

`context` cung cấp `xp`, `rng`, `trial_index`, `seed`, `device`. Code tùy biến hiện chạy với quyền của người dùng local. Khi chạy dưới dịch vụ dùng chung, bắt buộc thêm sandbox, giới hạn CPU/RAM/thời gian và allowlist import.

## Định dạng dự án

Project là JSON versioned chứa metadata, nodes, edges và cấu hình simulation. UI có thể xuất/nhập trực tiếp; backend dùng Pydantic để kiểm tra.

Mỗi node có `port_orientation` (`standard` hoặc `reversed`). Đây là thuộc tính trình bày của canvas: `standard` đặt input bên trái/output bên phải, còn `reversed` đặt input bên phải/output bên trái. Engine chỉ dùng id/handle nên kết quả mô phỏng không thay đổi.

## Experiment sweep và Sink

Experiment tạo dải SNR từ `snr_db_start/stop/step`; mỗi trial nhận `context.snr_db`, vì vậy AWGN ở chế độ `experiment` không cần hard-code một giá trị. Mỗi điểm dừng khi đạt `min_frames` và (`min_errors` hoặc `max_frames`). Kết quả giữ `snr_points` để Sink vẽ BER theo SNR. Block được chọn ngay tại sự kiện bắt đầu kéo; hai sidebar có thể ẩn/hiện và kéo đổi chiều rộng. BER Meter hiển thị đồ thị SVG log-scale trong inspector sau khi có kết quả.
