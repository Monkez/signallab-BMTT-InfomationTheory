# Kế hoạch sản phẩm SignalLab

## 1. Mục tiêu

SignalLab giúp sinh viên và nhà nghiên cứu xây dựng chuỗi thông tin số bằng sơ đồ khối, chỉ viết Python ở mức thuật toán, rồi chạy thí nghiệm Monte-Carlo có khả năng tận dụng nhiều CPU/GPU.

## 2. Phạm vi MVP

- Canvas kéo-thả, nối cổng, phóng to/thu nhỏ, lưu/mở file mô phỏng `.slab.json`; Save ghi lại file hiện tại và hỗ trợ `Ctrl+S`.
- Thư viện 55 khối gồm nguồn, source/channel coding, DSP, PSK/QAM/OOK/2-FSK, AWGN/Rayleigh/Rician, receiver, BER/SER/EVM và Python tùy biến.
- Panel thuộc tính có Python IDE editor với syntax highlighting, line number và cửa sổ chỉnh sửa lớn chuyên biệt; code mẫu dùng NumPy/SciPy/SignalLab.
- Kiểm tra DAG, cổng kết nối và tham số trước khi chạy.
- Job Monte-Carlo bất đồng bộ, seed tái lập, chạy tuần tự hoặc đa tiến trình.
- Chế độ `auto`, `cpu`, `gpu`; tự phát hiện CuPy/CUDA và tự hạ cấp an toàn về CPU.
- Dashboard tiến độ, BER, số lỗi bit, throughput, thời gian và cảnh báo.
- Quét SNR dB theo start/stop/step; mỗi điểm có giới hạn frame tối thiểu/tối đa và số lỗi tối thiểu.
- AWGN tham chiếu SNR của Experiment hoặc giữ giá trị cố định; Sink BER hiển thị đồ thị BER theo SNR.
- Canvas dùng toàn bộ vùng bên trái; thư viện block mở từ nút Add trên toolbar, có search và các nhóm thu gọn mặc định. Chỉ Properties inspector bên phải có thể ẩn/hiện và kéo đổi kích thước.
- Console dock phía dưới ghi lại trạng thái job, cảnh báo và lỗi để debug mô phỏng ngay trong app.
- Dashboard realtime cập nhật BER theo SNR khi simulation đang chạy; biểu đồ và bảng có thao tác copy/export PNG, TSV và CSV.
- Engine tối ưu graph lookup, seed theo batch và tái sử dụng process pool; auto mode tránh multiprocessing cho workload nhỏ để giảm độ trễ.
- Native Batch Executor C++20/oneTBB fuse các chuỗi BER BPSK/AWGN phổ biến, dùng Philox tái lập độc lập số thread; Auto planner fallback về engine Python cho graph chưa hỗ trợ.
- Python Block dùng API đơn giản `process(signal, params) -> array`; scheduler đảm nhiệm song song hóa các frame, không bắt người dùng viết mã multiprocessing/GPU.
- Python Block có fast path `process_batch(signals, params_batch)` tùy chọn, persistent process workers, metadata cache và runtime hint inline/process/batch-size; API frame cũ giữ tương thích.
- Python Block đọc trực tiếp SNR/trial/seed/device của frame hiện tại qua `params`; khối Variables không cổng khai báo literal toàn cục một lần cho mọi Python Block.
- Package `signallab` trên NumPy/SciPy cung cấp API nhất quán cho nguồn, tín hiệu, lọc, điều chế, kênh, mã và metric; NumPy/SciPy trực tiếp vẫn được hỗ trợ.
- Menu Documents mở cửa sổ offline độc lập, có tìm kiếm full-text và tài liệu hàm/quickstart chi tiết cho người học.
- Thư viện mở rộng với Text Source, differential source coding, repetition code, QPSK, OOK, 8-PSK Gray, 16-QAM Gray, Rayleigh fading, Scope, Constellation và Power Meter.
- Mã chập rate-1/2 (7,5), hard Viterbi, FIR/DC Blocker/Normalize Power, 2-FSK, Rician K-factor và EVM Meter có contract/test/sample end-to-end.
- Config dùng draft + Save; mọi ô số tham số hỗ trợ xóa trắng và scientific notation. Results có progress bubble theo step và trạng thái running/completed trực quan.
- Bổ sung Text File Source và Image File Source (file picker, base64 project payload), cùng các codec nguồn kinh điển Huffman, Shannon-Fano, RLE và ZIP/DEFLATE theo cặp Encoder/Decoder.
- Script Windows một lần bấm cho cài đặt, chạy và build.
- Bản desktop Windows có `SignalLab.exe`, chứa frontend production và backend local, không cần Vite khi sử dụng.

## 3. Các giai đoạn tiếp theo

### V1 — Công cụ giảng dạy

- QAM bậc cao hơn, pulse shaping, carrier/timing synchronization và equalization (2-FSK/QPSK/8-PSK/16-QAM/Rayleigh/Rician đã có).
- Scope miền thời gian, phổ, constellation, eye diagram.
- Subsystem, nhóm khối, annotation, undo/redo đầy đủ.
- Notebook/report thí nghiệm và sweep Eb/N0.

### V2 — Nghiên cứu

- LDPC, Polar, Turbo; OFDM/MIMO; channel estimation.
- Typed native plan/fusion đã hỗ trợ QPSK và 16-QAM/AWGN/BER; tiếp tục nghiên cứu Rayleigh có equalization rõ ràng và các metric phổ biến trước khi nhận topology mới.
- Scheduler theo batch cho GPU, nhiều GPU và máy từ xa (ngoài phạm vi tối ưu single-machine hiện tại).
- Cache trung gian, checkpoint job, plugin package có version.
- Experiment matrix, artifact store, so sánh và xuất báo cáo.

### V3 — Hệ sinh thái

- Marketplace khối, quản lý môi trường Python cô lập.
- Cộng tác, phân quyền, server lab dùng chung.
- Sinh code/triển khai SDR với GNU Radio hoặc SoapySDR.

## 4. Tiêu chí chất lượng

- Một sơ đồ mẫu chạy được trong dưới 3 phút kể từ lần mở đầu tiên sau setup.
- Kết quả lặp lại với cùng graph/cấu hình khi mọi block ngẫu nhiên dùng seed cố định; `seed=-1` chủ ý tạo run mới, còn runtime vẫn tránh lặp cùng mẫu giữa các frame.
- Lỗi graph/code được trả về có node cụ thể và thông báo dễ hiểu.
- UI không bị khóa khi job đang chạy; có thể hủy job.
- Không thực thi code tùy biến trên server công cộng nếu chưa có sandbox/container.

## 5. Rủi ro chính

- Python tùy biến là mã tin cậy trong bản local; triển khai nhiều người dùng phải cô lập tiến trình/container.
- Không phải thuật toán NumPy nào cũng tự chạy GPU. Quy ước `context.xp` giúp code portable; khối không tương thích sẽ chạy CPU.
- Overhead đa tiến trình có thể lớn với trial quá nhỏ; chế độ `auto` chỉ bật song song khi đủ workload.
- Native executor chỉ nhận topology được planner chứng minh tương thích; Python Block và graph tổng quát luôn có đường chạy compatibility chính xác.
