# Kế hoạch sản phẩm SignalLab

## 1. Mục tiêu

SignalLab giúp sinh viên và nhà nghiên cứu xây dựng chuỗi thông tin số bằng sơ đồ khối, chỉ viết Python ở mức thuật toán, rồi chạy thí nghiệm Monte-Carlo có khả năng tận dụng nhiều CPU/GPU.

## 2. Phạm vi MVP

- Canvas kéo-thả, nối cổng, phóng to/thu nhỏ, lưu/mở dự án JSON.
- Thư viện khối: nguồn bit, Hamming(7,4), BPSK, AWGN, giải điều chế, giải mã, BER và Python tùy biến.
- Panel thuộc tính và trình soạn Python có mẫu NumPy.
- Kiểm tra DAG, cổng kết nối và tham số trước khi chạy.
- Job Monte-Carlo bất đồng bộ, seed tái lập, chạy tuần tự hoặc đa tiến trình.
- Chế độ `auto`, `cpu`, `gpu`; tự phát hiện CuPy/CUDA và tự hạ cấp an toàn về CPU.
- Dashboard tiến độ, BER, số lỗi bit, throughput, thời gian và cảnh báo.
- Script Windows một lần bấm cho cài đặt, chạy và build.

## 3. Các giai đoạn tiếp theo

### V1 — Công cụ giảng dạy

- QPSK/QAM/FSK, pulse shaping, đồng bộ, fading Rayleigh/Rician.
- Scope miền thời gian, phổ, constellation, eye diagram.
- Subsystem, nhóm khối, annotation, undo/redo đầy đủ.
- Notebook/report thí nghiệm và sweep Eb/N0.

### V2 — Nghiên cứu

- LDPC, Polar, Turbo; OFDM/MIMO; channel estimation.
- Scheduler theo batch cho GPU, nhiều GPU và máy từ xa.
- Cache trung gian, checkpoint job, plugin package có version.
- Experiment matrix, artifact store, so sánh và xuất báo cáo.

### V3 — Hệ sinh thái

- Marketplace khối, quản lý môi trường Python cô lập.
- Cộng tác, phân quyền, server lab dùng chung.
- Sinh code/triển khai SDR với GNU Radio hoặc SoapySDR.

## 4. Tiêu chí chất lượng

- Một sơ đồ mẫu chạy được trong dưới 3 phút kể từ lần mở đầu tiên sau setup.
- Kết quả lặp lại với cùng graph, seed và cấu hình.
- Lỗi graph/code được trả về có node cụ thể và thông báo dễ hiểu.
- UI không bị khóa khi job đang chạy; có thể hủy job.
- Không thực thi code tùy biến trên server công cộng nếu chưa có sandbox/container.

## 5. Rủi ro chính

- Python tùy biến là mã tin cậy trong bản local; triển khai nhiều người dùng phải cô lập tiến trình/container.
- Không phải thuật toán NumPy nào cũng tự chạy GPU. Quy ước `context.xp` giúp code portable; khối không tương thích sẽ chạy CPU.
- Overhead đa tiến trình có thể lớn với trial quá nhỏ; chế độ `auto` chỉ bật song song khi đủ workload.

