# Hướng dẫn sử dụng

## Khởi động bản desktop

1. Chạy `setup.bat` ở lần đầu.
2. Chạy `build_app.bat` để tạo `dist\SignalLab\SignalLab.exe`.
3. Chạy `run.bat` hoặc mở trực tiếp file EXE.

Bản desktop chỉ mở một cửa sổ SignalLab, không cần Node.js/Vite khi sử dụng và không mở terminal. Khi sao chép sang máy khác, phải sao chép cả thư mục `dist\SignalLab`, bao gồm `_internal`; không chỉ sao chép riêng EXE. Máy Windows đích cần Microsoft Edge WebView2 Runtime, vốn có sẵn trên Windows 10/11 được cập nhật.

`run_dev.bat` chỉ dành cho lập trình viên. Nó chạy Vite tại port 5173, nên nếu đóng cửa sổ dev server thì trình duyệt sẽ báo WebSocket mất kết nối và `ERR_CONNECTION_REFUSED`. Đây không phải cơ chế chạy của bản EXE.

Yêu cầu để build: Windows 10/11, Python 3.11+ và Node.js 20+. Lần chạy `setup.bat`/`build_app.bat` đầu tiên cần Internet để tải thư viện. Máy chỉ chạy thư mục release không cần Python hoặc Node.js.

## Tạo mô phỏng

1. Chọn khối trong thanh bên hoặc dùng sơ đồ mẫu. Khi bắt đầu kéo block, block được chọn ngay.
2. Kéo từ cổng bên phải của một khối sang cổng bên trái khối kế tiếp.
3. Chọn khối để sửa tên và tham số. Với Python Block, sửa hàm `process` theo mẫu.
4. Trong tab **Experiment**, chọn SNR Start/Stop/Step, frame tối đa/tối thiểu và lỗi tối thiểu cho mỗi điểm. Chọn worker, seed và thiết bị.
5. Nhấn **Run simulation**. Kết quả cập nhật trong panel bên phải.
6. Theo dõi **Console** ở phía dưới vùng canvas để xem job, cảnh báo và lỗi. Graph luôn nằm ở cột trung tâm làm vùng làm việc chính; Experiment/Block nằm ở inspector bên phải, còn Console dùng theme sáng và cùng chiều rộng với graph, không phủ lên hai sidebar. Hai sidebar kéo dài liên tục qua cả vùng View và Console nên không còn khoảng trống phía dưới. Có thể kéo mép trên để đổi chiều cao hoặc ẩn bằng nút Console trên thanh công cụ. Khi job đang chạy, phần **LIVE RESULTS** cập nhật BER theo từng batch.
7. Trong biểu đồ **BER vs SNR**, nhập tên đường, chọn màu và kiểu nét rồi bấm **Save reference** để lưu đường hiện tại. Dùng **Load reference…** để nạp các đường đã lưu và so sánh; legend cho phép ẩn hoặc xóa từng reference. Các đường được lưu trong trình duyệt của máy và vẫn có thể dùng sau khi mở lại app.

## Thao tác canvas

- Click block để chọn và sửa trong panel **Block**.
- Nhấn `Delete` để xóa block đang chọn cùng các đường nối của block đó.
- Khi đang nhập trong ô text hoặc Python editor, `Delete` chỉ sửa nội dung đang nhập và không xóa block.
- Dùng các nút zoom ở góc dưới canvas nếu sơ đồ lớn.
- MiniMap ở góc dưới phải được thu gọn để tiết kiệm diện tích; màu node thể hiện nhóm Sources/Source coding/Modulation/Channels/Sinks, có thể pan/zoom để xem nhanh toàn bộ graph.
- Trong panel **Block**, dùng **Port layout** để đổi giữa `Input left · Output right` và `Input right · Output left`. Cấu hình được lưu cùng file Export.
- Sau khi đổi layout, các đường nối hiện tại tự động được đo lại và bám theo handle mới.
- Dùng các nút panel trên thanh trên để ẩn/hiện **Block library**, **Inspector** hoặc **Console**. Kéo mép sidebar/console để đổi kích thước. Console giữ nguyên trạng thái ẩn/hiện khi chạy mô phỏng.

## Cấu hình Monte-Carlo

- `SNR Start/Stop/Step`: tạo dải SNR dB chạy tuần tự.
- `Max frames / SNR`: giới hạn cứng số frame tại mỗi SNR.
- `Min frames / SNR`: không dừng sớm trước số frame này.
- `Min errors / SNR`: dừng sớm khi đủ số lỗi sau khi đạt min frames.
- Với block **AWGN**, chọn `Experiment sweep` để lấy `context.snr_db`; chọn `Fixed block value` để dùng `ebn0_db` riêng.
- `Workers = 0`: hệ thống tự chọn; đặt `1` để debug dễ hơn.
- `Seed`: cho kết quả tái lập.
- `Auto`: chọn GPU nếu có và phù hợp, nếu không dùng CPU.
- Sau khi chạy, BER Meter và tab Experiment hiển thị đồ thị BER theo SNR cùng số frame/lỗi từng điểm.
- Trên biểu đồ BER, chọn **Copy** để copy ảnh PNG hoặc **PNG** để tải ảnh. Bảng **Results by SNR** hỗ trợ **Copy** (TSV), **CSV** và **PNG**, thuận tiện đưa vào báo cáo.
- Thư viện có thêm Text Source, Text File Source, Image File Source, Differential Encoder/Decoder, Huffman, Shannon-Fano, Run-Length, ZIP/DEFLATE, Repetition-3, QPSK, Rayleigh Fading, Signal Scope, Constellation Sink và Power Meter. File Source cho phép chọn file trực tiếp trong panel Block; dữ liệu được lưu trong project dưới dạng base64 để chạy được cả desktop và dev server.
- Các codec nguồn kinh điển làm việc trên stream bit: Encoder có cổng `reference` để nối vào BER, Decoder dùng cùng tham số codebook/codec để khôi phục stream. Huffman và Shannon-Fano dùng nhóm symbol 2-bit với trọng số có thể chỉnh; RLE dùng cặp count/value; ZIP dùng DEFLATE chuẩn.

## Lưu dự án

Nút Export tải file `.json`; Import đọc lại file đó. Với Python Block, viết tự nhiên theo mẫu:

```python
def process(signal, params):
    return signal * float(params.get("gain", 1.0))
```

Chỉ cần xử lý một frame và trả về mảng; runtime tự song song hóa các frame Monte-Carlo. API cũ có `inputs, params, context` vẫn được giữ tương thích. Không lưu code tùy biến từ nguồn không tin cậy rồi chạy.
