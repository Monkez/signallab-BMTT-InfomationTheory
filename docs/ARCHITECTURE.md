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
  features/projects/projectFiles.ts Save/Open đa nền tảng và desktop bridge
  features/sourceTheory/           codebook Huffman và bảng giảng dạy live
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

`contracts.py` là lớp kiểm soát tín hiệu tập trung. Nó kiểm tra tham số tĩnh, mảng 1-D không rỗng, bội số đầu vào, tỷ lệ kích thước đầu ra, port khai báo và các header độ dài của codec. `engine.execute_trial` chạy validation trước và sau từng processor rồi bọc lỗi thành `BlockExecutionError(node_id, node_label, reason)`. Cùng cấu trúc lỗi đi qua API đồng bộ và job đa process, giúp frontend đánh dấu đúng node thay vì chỉ nhận chuỗi traceback chung.

`snapshots.py` giữ tối đa bốn frame đại diện gần nhất bằng LRU trong RAM. Kết quả Run once/Benchmark chỉ trả `snapshot_id` và summary nhỏ; tab Block gọi API port theo trang 128 phần tử, còn Copy all đọc tuần tự theo chunk 4096. Vì vậy polling job không mang buffer lớn lặp lại, block ảnh không khiến DOM render hàng triệu dòng cùng lúc, nhưng người dùng vẫn truy cập được mọi phần tử. Mỗi output chỉ được đóng băng/copy về host một lần; input downstream tham chiếu lại snapshot output upstream nên không nhân đôi buffer trên từng cạnh.

`SinkChart.tsx` hiện là component điều phối trạng thái BER và dùng các module feature trên. Mọi plot đều đi qua `BerPlot`, nên preview, report, đường reference, marker và quy tắc điểm BER bằng 0 có một nguồn logic duy nhất.

## Bản desktop Windows

PyWebView tạo cửa sổ native dùng WebView2. Một tiến trình Uvicorn nội bộ phục vụ cả API và frontend production trên loopback với port trống được chọn tự động. PyInstaller gom Python runtime, backend và `frontend/dist` vào thư mục phát hành onedir chứa `SignalLab.exe`. Onedir được chọn để khởi động nhanh và tránh mỗi worker Monte-Carlo phải giải nén lại toàn bộ onefile. Người dùng cuối không chạy Vite, Node.js hoặc hai terminal; Vite chỉ còn dành cho phát triển giao diện qua `run_dev.bat`.

`DesktopProjectApi` là bridge nhỏ giữa React và hộp thoại file native. Open đọc UTF-8, Save As chọn đường dẫn, còn Save/`Ctrl+S` ghi lại đường dẫn đang liên kết. `project_files.py` ghi qua file tạm cùng thư mục rồi `os.replace`, tránh để lại file JSON dở dang nếu quá trình ghi lỗi. Bản web ưu tiên File System Access API và dùng download/upload làm fallback; logic lựa chọn nền tảng nằm riêng trong `features/projects/projectFiles.ts`.

## Mô hình thực thi

Mỗi node nhận `inputs`, `params`, `context` và trả về dictionary các output. Graph được topological-sort một lần. Mỗi trial có seed sinh từ `SeedSequence`, vì vậy lịch worker thay đổi không làm mất khả năng tái lập khi các block ngẫu nhiên dùng seed cố định. Metric của sink được giảm theo phép cộng; BER cuối cùng là tổng bit lỗi chia tổng bit đã so sánh, không phải trung bình BER từng trial.

Random Bits, AWGN và Rayleigh có seed riêng. `seed = -1` lấy một entropy gốc mới đúng một lần khi bắt đầu Run once/Benchmark; runtime tiếp tục trộn entropy đó với seed frame và CRC32 của node để các node/frame có stream độc lập, ổn định trước thay đổi lịch multiprocessing. Với `seed >= 0`, entropy gốc của run bị bỏ qua nên cùng graph, Experiment seed và block seed sẽ tái lập; frame vẫn khác nhau vì seed frame vẫn tham gia phép trộn.

`POST /api/run-once` dùng cùng DAG runtime nhưng chỉ chạy một frame đồng bộ tại `snr_db_start`. Khi bật `capture_ports`, engine tóm tắt input/output của từng node thành dtype, shape, size, min/mean/max và tối đa 8 mẫu dạng JSON-safe. Frontend gắn summary vào node để tooltip đọc trực tiếp; dữ liệu đầy đủ được giữ sau `snapshot_id` và chỉ truyền từng trang khi tab Block yêu cầu.

Job **Run Benchmark** vẫn chạy Monte-Carlo bất đồng bộ qua polling. Khi hoàn tất, engine chạy thêm một frame đại diện xác định bằng seed cấu hình tại SNR đầu tiên để trả `port_previews` và đăng ký snapshot đầy đủ. Frame này phục vụ quan sát luồng dữ liệu, không tham gia phép cộng metric và không làm thay đổi BER benchmark. Mọi chỉnh sửa topology hoặc tham số đều xóa preview/snapshot phía frontend để tránh hiển thị dữ liệu hết hạn.

## Song song CPU/GPU

- CPU: trial độc lập được chia thành chunk và chạy bằng `ProcessPoolExecutor`. `workers=0` nghĩa là tự chọn.
- GPU: runtime thử nạp CuPy và kiểm tra device. Các khối built-in dùng namespace mảng `context.xp`. Bản MVP dùng một GPU worker theo batch nhỏ để tránh nhiều process tranh cùng device.
- Auto: ưu tiên GPU khi khả dụng và graph tương thích, ngược lại dùng CPU; workload nhỏ chạy inline để tránh overhead.

## Source và file blocks

`text_file_source` đọc bytes UTF-8/binary của file text, còn `image_file_source` dùng Pillow để đọc pixel grayscale hoặc RGB; cả hai phát ra bitstream và một bản sao `reference`. Frontend dùng file picker rồi lưu payload base64 trong node params, không phụ thuộc đường dẫn máy cục bộ khi mở lại project.

Miền lý thuyết nguồn dùng mảng NumPy Unicode 1-D (`<U...`) làm **symbol stream**, không truyền một Python string nguyên khối. Cách biểu diễn này giữ từng ký tự quan sát được trong port inspector, cho phép kiểm tra size/serialize snapshot và vẫn phù hợp với scheduler. `text_symbol_source`/`text_file_symbol_source` phát ký tự; `discrete_symbol_source` lấy mẫu theo alphabet và `P(x)`; `source_analyzer` trả từng `P(x)`, `I(x)=-log2(P(x))` cùng metric entropy, entropy cực đại và hiệu suất. `symbols_to_bits` là ranh giới tường minh chuyển symbol sang UTF-8 bitstream trước mã kênh/điều chế.

Nhóm source coding có cặp Encoder/Decoder cho Huffman, Shannon-Fano, RLE và ZIP/DEFLATE. Huffman/Shannon-Fano là implementation cố định 2-bit-symbol phục vụ giảng dạy; encoder đóng header độ dài để decoder loại padding. RLE và ZIP giữ header độ dài tương tự để round-trip chính xác.

Các cặp `symbol_huffman_*` và `symbol_shannon_fano_*` nhận trực tiếp symbol stream và model alphabet/xác suất, phát bitstream có header số symbol rồi khôi phục chuỗi ký tự. Chúng tồn tại song song với codec bit-pair cũ để project trước đây không đổi ngữ nghĩa. `ser` so sánh chuỗi symbol sau giải mã; BER vẫn chỉ dành cho bitstream.

Huffman symbol dùng quy tắc phá hòa xác định: hàng đợi ưu tiên theo trọng số rồi theo thứ tự chèn. `features/sourceTheory/huffmanCodebook.ts` triển khai cùng quy tắc để inspector dựng codebook tức thời mà không gọi runtime; test backend khóa các từ mã khi xác suất bằng nhau để UI và encoder không lệch nhau.

## Python block API

```python
def process(signal, params):
    gain = float(params.get("gain", 1.0))
    return signal * gain
```

Đây là API khuyến nghị: block nhận một mảng NumPy của một frame và trả về một mảng. Runtime tự bọc kết quả thành output `out`, tự chạy các frame độc lập trên worker CPU; người dùng không cần viết multiprocessing, batch scheduler hay mã GPU. API cũ `process(inputs, params, context) -> {"out": ...}` vẫn được hỗ trợ cho project trước đây. Code tùy biến hiện chạy với quyền của người dùng local; khi chạy dưới dịch vụ dùng chung, bắt buộc thêm sandbox, giới hạn CPU/RAM/thời gian và allowlist import.

## Định dạng dự án

Project là JSON versioned với định dạng `signallab-simulation`, chứa graph và toàn bộ cấu hình Experiment. File mặc định có đuôi `.slab.json`, nhưng vẫn mở được project `.json` cũ. UI theo dõi chữ ký chỉ của dữ liệu có thể lưu (không gồm preview/runtime error) để hiện trạng thái Unsaved chính xác. Lệnh New tạo graph rỗng, khôi phục cấu hình Experiment mặc định, xóa snapshot/kết quả và gọi `clearProjectFileTarget()` để lần Save đầu tiên luôn đi qua Save As.

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

Mỗi block mới đồng thời phải khai báo mô tả `SIZE_CONTRACTS` và thêm quy tắc input/output tương ứng trong `contracts.py`. Không được padding, truncate hoặc lấy `min(input sizes)` ngầm trong processor; mọi thay đổi kích thước phải là một tỷ lệ/header rõ ràng hoặc tham số chủ ý như `Python Block.output_size`.

Hamming (7,4) dùng ma trận sinh hệ thống `G = [I4 | P]`. Mỗi codeword có thứ tự `[d1,d2,d3,d4,p1,p2,p3]`; decoder dùng parity-check tương ứng và ánh xạ syndrome về đúng tọa độ hệ thống. Processor không tự padding/cắt phần dư vì hợp đồng runtime đã yêu cầu kích thước input là bội của 4/7.

Khi thêm kiểu Sink/đồ thị: tạo feature riêng trong `frontend/src/features`, định nghĩa type và hàm biến đổi dữ liệu thuần trước, sau đó mới viết component SVG/UI. Không sao chép phép chiếu đồ thị giữa preview và report.
