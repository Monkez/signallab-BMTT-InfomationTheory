# Kiến trúc SignalLab

## Tổng quan

```text
React + React Flow
  ├─ block library / canvas / property editor
  ├─ Python code editor
  ├─ experiment dashboard
  └─ console dock (job/runtime events)
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

## Ranh giới module

Frontend được tổ chức theo feature thay vì dồn dữ liệu và thuật toán vào component màn hình:

```text
frontend/src/
  App.tsx                         điều phối workspace và job
  components/FlowMiniMapNode.tsx renderer MiniMap
  features/blocks/catalog.ts      catalog offline + icon/màu nhóm block
  features/experiment/config.ts   mặc định và phép tính SNR sweep
  features/ber/
    BerPlot.tsx                   SVG plot dùng chung preview/report
    BerLegend.tsx                 legend dùng chung preview/report
    chartMath.ts                  domain, log scale, quy tắc BER=0
    referenceFiles.ts             định dạng .ber.json, Save As/Browse
    referenceStore.ts             localStorage và đồng bộ reference
    imageExport.ts                copy/xuất PNG
    types.ts                      hợp đồng dữ liệu BER
```

Backend tách hợp đồng block khỏi thuật toán xử lý: `block_registry.py` chứa `BlockSpec`, catalog và khả năng GPU; `blocks.py` chỉ chứa processor; `engine.py` biên dịch/thực thi DAG; `jobs.py` quản lý vòng đời job; `main.py` chỉ là lớp HTTP. Nhờ vậy đổi nhãn/port/default không đụng thuật toán, còn thêm processor không làm phình API layer.

`SinkChart.tsx` hiện là component điều phối trạng thái BER và dùng các module feature trên. Mọi plot đều đi qua `BerPlot`, nên preview, report, đường reference, marker và quy tắc điểm BER bằng 0 có một nguồn logic duy nhất.

## Bản desktop Windows

PyWebView tạo cửa sổ native dùng WebView2. Một tiến trình Uvicorn nội bộ phục vụ cả API và frontend production trên loopback với port trống được chọn tự động. PyInstaller gom Python runtime, backend và `frontend/dist` vào thư mục phát hành onedir chứa `SignalLab.exe`. Onedir được chọn để khởi động nhanh và tránh mỗi worker Monte-Carlo phải giải nén lại toàn bộ onefile. Người dùng cuối không chạy Vite, Node.js hoặc hai terminal; Vite chỉ còn dành cho phát triển giao diện qua `run_dev.bat`.

## Mô hình thực thi

Mỗi node nhận `inputs`, `params`, `context` và trả về dictionary các output. Graph được topological-sort một lần. Mỗi trial có seed sinh từ `SeedSequence`, vì vậy lịch worker thay đổi không làm mất khả năng tái lập. Metric của sink được giảm theo phép cộng; BER cuối cùng là tổng bit lỗi chia tổng bit đã so sánh, không phải trung bình BER từng trial.

## Song song CPU/GPU

- CPU: trial độc lập được chia thành chunk và chạy bằng `ProcessPoolExecutor`. `workers=0` nghĩa là tự chọn.
- GPU: runtime thử nạp CuPy và kiểm tra device. Các khối built-in dùng namespace mảng `context.xp`. Bản MVP dùng một GPU worker theo batch nhỏ để tránh nhiều process tranh cùng device.
- Auto: ưu tiên GPU khi khả dụng và graph tương thích, ngược lại dùng CPU; workload nhỏ chạy inline để tránh overhead.

## Source và file blocks

`text_file_source` đọc bytes UTF-8/binary của file text, còn `image_file_source` dùng Pillow để đọc pixel grayscale hoặc RGB; cả hai phát ra bitstream và một bản sao `reference`. Frontend dùng file picker rồi lưu payload base64 trong node params, không phụ thuộc đường dẫn máy cục bộ khi mở lại project.

Nhóm source coding có cặp Encoder/Decoder cho Huffman, Shannon-Fano, RLE và ZIP/DEFLATE. Huffman/Shannon-Fano là implementation cố định 2-bit-symbol phục vụ giảng dạy; encoder đóng header độ dài để decoder loại padding. RLE và ZIP giữ header độ dài tương tự để round-trip chính xác.

## Python block API

```python
def process(signal, params):
    gain = float(params.get("gain", 1.0))
    return signal * gain
```

Đây là API khuyến nghị: block nhận một mảng NumPy của một frame và trả về một mảng. Runtime tự bọc kết quả thành output `out`, tự chạy các frame độc lập trên worker CPU; người dùng không cần viết multiprocessing, batch scheduler hay mã GPU. API cũ `process(inputs, params, context) -> {"out": ...}` vẫn được hỗ trợ cho project trước đây. Code tùy biến hiện chạy với quyền của người dùng local; khi chạy dưới dịch vụ dùng chung, bắt buộc thêm sandbox, giới hạn CPU/RAM/thời gian và allowlist import.

## Định dạng dự án

Project là JSON versioned chứa metadata, nodes, edges và cấu hình simulation. UI có thể xuất/nhập trực tiếp; backend dùng Pydantic để kiểm tra.

Mỗi node có `port_orientation` (`standard` hoặc `reversed`). Đây là thuộc tính trình bày của canvas: `standard` đặt input bên trái/output bên phải, còn `reversed` đặt input bên phải/output bên trái. Engine chỉ dùng id/handle nên kết quả mô phỏng không thay đổi.

## Experiment sweep và Sink

Experiment tạo dải SNR từ `snr_db_start/stop/step`; mỗi trial nhận `context.snr_db`, vì vậy AWGN ở chế độ `experiment` không cần hard-code một giá trị. Mỗi điểm dừng khi đạt `min_frames` và (`min_errors` hoặc `max_frames`). Kết quả giữ `snr_points` để Sink vẽ BER theo SNR. Block được chọn ngay tại sự kiện bắt đầu kéo; hai sidebar có thể ẩn/hiện và kéo đổi chiều rộng. BER Meter hiển thị đồ thị SVG log-scale trong inspector sau khi có kết quả.

Console dock là lớp hiển thị phía frontend, nhận sự kiện khi nạp block, xếp hàng/chạy/kết thúc/hủy job và lỗi API. Trong lúc chạy, callback tiến độ mang theo `snr_points` gồm các điểm đã hoàn tất và điểm SNR hiện tại, vì vậy dashboard có thể vẽ BER theo thời gian thực mà không đợi job kết thúc. Engine trả thêm `sink_metrics` cho Scope, Constellation và Power Meter để inspector hiển thị tóm tắt trực quan mà không truyền mảng mẫu lớn qua API.

## Xuất kết quả và tối ưu hiệu năng

- Biểu đồ BER có thể copy trực tiếp ảnh PNG vào clipboard hoặc tải xuống; bảng kết quả theo SNR có thể copy dạng TSV, tải CSV hoặc PNG.
- Graph được biên dịch thành `node_map`, danh sách cạnh vào và thứ tự thực thi một lần trước sweep. Seed được sinh theo từng batch thay vì cấp phát toàn bộ số frame từ đầu.
- CPU dùng một `ProcessPoolExecutor` dùng lại cho toàn bộ sweep; chế độ tự động chạy inline với workload nhỏ và giới hạn số worker hợp lý để tránh overhead tạo process lớn hơn thời gian tính toán. Người dùng vẫn có thể đặt `Workers` thủ công khi benchmark hệ thống cụ thể.

## Quy trình mở rộng

Khi thêm block built-in: thêm `BlockSpec` vào `backend/app/block_registry.py`, thêm processor và đăng ký trong `PROCESSORS` tại `backend/app/blocks.py`, rồi thêm catalog dự phòng ở `frontend/src/features/blocks/catalog.ts`. Catalog backend là nguồn chính khi app đã kết nối; catalog frontend chỉ giúp UI dùng được trong thời gian backend khởi động. Cuối cùng thêm round-trip/validation test trong `backend/tests`.

Khi thêm kiểu Sink/đồ thị: tạo feature riêng trong `frontend/src/features`, định nghĩa type và hàm biến đổi dữ liệu thuần trước, sau đó mới viết component SVG/UI. Không sao chép phép chiếu đồ thị giữa preview và report.
