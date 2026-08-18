# Hướng dẫn sử dụng

## Khởi động bản desktop

1. Chạy `setup.bat` ở lần đầu.
2. Chạy `build_app.bat` để tạo `dist\SignalLab\SignalLab.exe`.
3. Chạy `run.bat` hoặc mở trực tiếp file EXE. Launcher tự chọn bản đóng gói mới nhất giữa thư mục phát hành chuẩn và thư mục cập nhật dự phòng, nên vẫn mở đúng tính năng mới khi bản EXE cũ đang bị Windows khóa.

Nếu SignalLab đang mở trong lúc build, `build_app.bat` tự chuyển sang `dist-update\SignalLab\SignalLab.exe` thay vì báo thất bại hoặc tự đóng ứng dụng. `run.bat` sẽ chọn bản update này ở lần mở tiếp theo.

Bản desktop chỉ mở một cửa sổ SignalLab, không cần Node.js/Vite khi sử dụng và không mở terminal. Khi sao chép sang máy khác, phải sao chép cả thư mục `dist\SignalLab`, bao gồm `_internal`; không chỉ sao chép riêng EXE. Máy Windows đích cần Microsoft Edge WebView2 Runtime, vốn có sẵn trên Windows 10/11 được cập nhật.

`run_dev.bat` chỉ dành cho lập trình viên. Nó chạy Vite tại port 5173, nên nếu đóng cửa sổ dev server thì trình duyệt sẽ báo WebSocket mất kết nối và `ERR_CONNECTION_REFUSED`. Đây không phải cơ chế chạy của bản EXE.

Yêu cầu để build: Windows 10/11, Python 3.11+ và Node.js 20+. Lần chạy `setup.bat`/`build_app.bat` đầu tiên cần Internet để tải thư viện. Máy chỉ chạy thư mục release không cần Python hoặc Node.js.

## Tạo mô phỏng

Nút **Documents** trên topbar mở trung tâm tài liệu trong một cửa sổ riêng. Ô tìm kiếm hỗ trợ tên hàm, khái niệm và ví dụ; menu chia tài liệu thành Python API, tham chiếu hàm và cách làm việc trong app. Nhấn `Ctrl+K` trong cửa sổ Documents để chuyển nhanh tới ô tìm kiếm. Nội dung được đóng gói cùng SignalLab nên đọc được khi offline.

### Open Samples — thư viện bài thực hành

Nút **Open Samples** trên topbar mở thư viện bài học được đóng gói sẵn và dùng được offline. Có thể tìm theo tên, khái niệm hoặc block; lọc theo **Digital communications**, **Information theory** và **Python labs**. Chọn một bài để xem trước:

- trình độ, thời lượng dự kiến và số block;
- mục tiêu học tập và các khái niệm trọng tâm;
- toàn bộ chuỗi block sẽ được nạp;
- quy trình thực hành từng bước;
- các kết quả cần quan sát và câu hỏi gợi ý.

Nhấn **Open this sample** để nạp graph cùng cấu hình Experiment đã hiệu chỉnh cho bài đó. Sample luôn được mở dưới dạng simulation **Unsaved**, không liên kết với file gốc; do đó có thể thay đổi tùy ý rồi dùng Save/`Ctrl+S` để chọn tên và vị trí lưu thành bài riêng. Nếu simulation hiện tại chưa lưu, app hỏi xác nhận trước khi thay thế.

Catalog hiện có chín bài:

1. BPSK không mã hóa qua AWGN — đường BER chuẩn.
2. Hamming (7,4) hệ thống qua AWGN — syndrome, sửa lỗi đơn và coding gain.
3. Mã lặp 3 — quyết định đa số và đánh đổi code rate.
4. QPSK với Constellation/Power Sink — quan hệ bit/symbol và I/Q.
5. Entropy nguồn rời rạc — P(x), I(x), H(X), Hmax và hiệu suất nguồn.
6. Huffman cho nguồn văn bản — codebook prefix, payload và SER.
7. Shannon–Fano cho nguồn văn bản — so sánh với Huffman.
8. Bộ thu BPSK bằng Python Block — quyết định ngưỡng với NumPy.
9. Kênh nhị phân đối xứng BSC(p) bằng Python Block — kiểm chứng BER xấp xỉ p.

Hai bài Python minh họa đúng mô hình lập trình của SignalLab: người học chỉ viết `process(signal, params)` cho một frame; runtime tự xử lý worker và song song hóa Monte-Carlo. Mã nguồn nằm ngay trong Python Block để đọc, chạy và sửa.

1. Chọn khối trong thanh bên hoặc dùng sơ đồ mẫu. Khi bắt đầu kéo block, block được chọn ngay.
2. Kéo từ cổng bên phải của một khối sang cổng bên trái khối kế tiếp.
3. Chọn khối để sửa tên và tham số. Với Python Block, sửa hàm `process` theo mẫu.
4. Trong tab **Experiment**, chọn SNR Start/Stop/Step, frame tối đa/tối thiểu và lỗi tối thiểu cho mỗi điểm. Chọn worker, seed và thiết bị.
5. Dùng **Run once** ở đầu tab để chạy đúng một frame tại giá trị SNR Start. Sau khi hoàn tất, rê chuột lên tên/cổng input hoặc output của block để xem kiểu dữ liệu, shape, số phần tử, min/mean/max và các mẫu đầu tiên. Dùng **Run Benchmark** để chạy toàn bộ sweep Monte-Carlo; kết quả cập nhật trong panel bên phải.
6. Theo dõi **Console** ở phía dưới vùng canvas để xem job, cảnh báo và lỗi. Graph luôn nằm ở cột trung tâm làm vùng làm việc chính; Experiment/Block nằm ở inspector bên phải, còn Console dùng theme sáng và cùng chiều rộng với graph, không phủ lên hai sidebar. Hai sidebar kéo dài liên tục qua cả vùng View và Console nên không còn khoảng trống phía dưới. Có thể kéo mép trên để đổi chiều cao hoặc ẩn bằng nút Console trên thanh công cụ. Khi job đang chạy, phần **LIVE RESULTS** cập nhật BER theo từng batch.
7. Trong phần kết quả, **Overall bit error rate** được tách thành card tổng hợp riêng; biểu đồ **BER vs SNR** nằm ở khu vực độc lập bên dưới. Legend được vẽ trực tiếp ở góc trên bên phải vùng đồ thị và đi kèm khi Copy/PNG. Chọn đường trong danh sách, chỉnh tên/màu/kiểu nét rồi bấm **Save .BER** để xuất đường thành file JSON. Dùng **Browse file** để nạp lại file reference từ máy; khi chọn một reference có thể ẩn hoặc xóa bằng hàng thao tác bên dưới. Các reference đã nạp vẫn được lưu trong trình duyệt để dùng lại sau khi mở app.
8. Bấm **Details** trên biểu đồ để mở báo cáo BER toàn màn hình. Tab **Chart** mặc định dùng đồ thị SVG độ phân giải cao riêng (viewBox lớn, nhiều vạch trục, nét/chữ không bị phóng từ preview) với legend nằm trong vùng vẽ; tab **Edit & Data** mới chứa danh sách đường, style, bảng SNR/BER/frame/error, thêm/xóa điểm, save và browse/load reference. Modal nằm trên toàn bộ app nên Console không xuất hiện chồng lên báo cáo.

## Thao tác canvas

- Click block để chọn và sửa trong panel **Block**.
- Nhấn `Delete` để xóa block đang chọn cùng các đường nối của block đó.
- Khi đang nhập trong ô text hoặc Python editor, `Delete` chỉ sửa nội dung đang nhập và không xóa block.
- Dùng các nút zoom ở góc dưới canvas nếu sơ đồ lớn.
- MiniMap ở góc dưới phải được thu gọn để tiết kiệm diện tích; màu node thể hiện nhóm Sources/Source coding/Modulation/Channels/Sinks, có thể pan/zoom để xem nhanh toàn bộ graph.
- Trong panel **Block**, dùng **Port layout** để đổi giữa `Input left · Output right` và `Input right · Output left`. Cấu hình được lưu cùng file Export.
- Sau khi đổi layout, các đường nối hiện tại tự động được đo lại và bám theo handle mới.
- **Run once** hữu ích để kiểm tra nhanh luồng dữ liệu trước khi benchmark. Sau **Run once** hoặc **Run Benchmark**, hover hay focus bằng bàn phím vào từng port để xem bản tóm tắt dữ liệu mới nhất. Trong tab **Block**, mục **Current port data** liệt kê đầy đủ mọi input/output của block đang chọn, gồm dtype, shape, tổng số phần tử và từng giá trị kèm chỉ số. Dùng nút Previous/Next để duyệt hết mảng theo trang hoặc **Copy all** để sao chép toàn bộ port. Khi sửa graph/tham số, snapshot cũ tự bị xóa để tránh hiểu nhầm.
- Mỗi block có ô **Signal size contract** trong inspector. Nếu tham số, input hoặc output vi phạm hợp đồng, quá trình dừng tại đúng block đó: node có viền đỏ và badge **Contract error**, còn Console ghi tên block, kích thước mong đợi và kích thước thực tế. Sửa graph/tham số sẽ xóa trạng thái lỗi cũ để có thể kiểm tra lại.
- Dùng các nút panel trên thanh trên để ẩn/hiện **Block library**, **Inspector** hoặc **Console**. Kéo mép sidebar/console để đổi kích thước. Console giữ nguyên trạng thái ẩn/hiện khi chạy mô phỏng.

## Cấu hình Monte-Carlo

- `SNR Start/Stop/Step`: tạo dải SNR dB chạy tuần tự.
- `Max frames / SNR`: giới hạn cứng số frame tại mỗi SNR.
- `Min frames / SNR`: không dừng sớm trước số frame này.
- `Min errors / SNR`: dừng sớm khi đủ số lỗi sau khi đạt min frames.
- Với block **AWGN**, chọn `Experiment sweep` để lấy `context.snr_db`; chọn `Fixed block value` để dùng `ebn0_db` riêng.
- `Workers = 0`: hệ thống tự chọn; đặt `1` để debug dễ hơn.
- `Seed`: cho kết quả tái lập.
- Random Bits, AWGN và Rayleigh có thêm `seed` riêng ở tab **Block**. Giá trị mặc định `-1` sinh dữ liệu/nhiễu mới ở mỗi lần Run once hoặc Run Benchmark. Đặt số nguyên từ `0` đến `4294967295` để tái lập kết quả; runtime vẫn tự tạo stream khác nhau cho từng block và từng frame.
- Muốn benchmark tái lập hoàn toàn, đặt seed cụ thể cho tất cả block ngẫu nhiên và giữ nguyên Seed trong Experiment. Chỉ cần một block còn `-1` thì lần chạy sau có thể cho chuỗi mẫu/BER khác.
- `Auto`: chọn GPU nếu có và phù hợp, nếu không dùng CPU.
- Sau khi chạy, BER Meter và tab Experiment hiển thị đồ thị BER theo SNR cùng số frame/lỗi từng điểm.
- **Run Benchmark** là tên mới của thao tác Monte-Carlo trước đây. Sau khi benchmark hoàn tất, port preview đại diện được lấy từ một frame xác định tại SNR Start; dữ liệu đầy đủ của mọi frame không được gửi lên UI nên app vẫn nhẹ với mô phỏng lớn.
- Trên biểu đồ BER, chọn **Copy** để copy ảnh PNG hoặc **PNG** để tải ảnh. Bảng **Results by SNR** hỗ trợ **Copy** (TSV), **CSV** và **PNG**, thuận tiện đưa vào báo cáo.
- Thư viện có thêm Text Source, Text File Source, Image File Source, Differential Encoder/Decoder, Huffman, Shannon-Fano, Run-Length, ZIP/DEFLATE, Repetition-3, QPSK, Rayleigh Fading, Signal Scope, Constellation Sink và Power Meter. File Source cho phép chọn file trực tiếp trong panel Block; dữ liệu được lưu trong project dưới dạng base64 để chạy được cả desktop và dev server.
- Các codec nguồn kinh điển làm việc trên stream bit: Encoder có cổng `reference` để nối vào BER, Decoder dùng cùng tham số codebook/codec để khôi phục stream. Huffman và Shannon-Fano dùng nhóm symbol 2-bit với trọng số có thể chỉnh; RLE dùng cặp count/value; ZIP dùng DEFLATE chuẩn.

## Thực hành lý thuyết nguồn với text

- **Text Symbol Source** phát mỗi ký tự Unicode thành một symbol nhìn thấy trực tiếp; **Text File Symbols** làm tương tự với file UTF-8. Các block Text Source cũ vẫn phát bits để project cũ tiếp tục hoạt động.
- **Discrete Symbol Source** cho nhập `alphabet`, `probabilities`, `length` và `seed`. Ví dụ `A,B,C,D` với `0.5,0.25,0.125,0.125`; các trọng số không bắt buộc cộng đúng 1 vì runtime tự chuẩn hóa, nhưng phải dương và đủ một giá trị cho mỗi symbol.
- Nối nguồn vào **Source Information Analyzer**, chạy **Run once**, rồi chọn analyzer. Tab Block hiển thị từng symbol, `P(x)`, lượng tin riêng `I(x)=-log2(P(x))`, entropy `H(X)`, entropy cực đại `log2(M)` và hiệu suất nguồn.
- **Huffman Symbol Encoder/Decoder** và **Shannon-Fano Symbol Encoder/Decoder** nhận trực tiếp chuỗi text, dùng cùng alphabet/xác suất ở hai phía và cho ra bitstream ở encoder. Nối `reference`/kết quả decoder vào **Symbol Error Rate** để đo SER.
- Khi chọn **Huffman Symbol Encoder**, mục **Current Huffman Codebook** hiển thị ngay symbol, xác suất đã chuẩn hóa, lượng tin, từ mã và độ dài. Bảng cùng H(X), chiều dài trung bình và hiệu suất cập nhật tức thời mỗi khi sửa alphabet hoặc probabilities; không cần chạy mô phỏng.
- Huffman Symbol Encoder mặc định chỉ xuất payload mã prefix, không chèn dữ liệu ẩn. Ví dụ `A|A|A|B|C|D → 0|0|0|10|110|111 → 00010110111`. Sau Run once, mục **Current encoded sequence** tách rõ Symbols, Codewords, Huffman payload và số bit. Tùy chọn **Include 32-bit symbol-count header** mặc định tắt; nếu bật phải bật cùng tùy chọn trên Huffman Symbol Decoder. Khi bật, UI hiển thị riêng header, payload và serialized output để không nhầm header là từ mã Huffman.
- Không cần header khi mỗi frame là một mảng có biên rõ ràng: decoder đọc mã prefix tới hết payload và báo lỗi nếu kết thúc giữa một codeword. Chỉ bật header khi cần tự mô tả số symbol để lưu trữ/ghép frame; trong bài đánh giá hiệu suất nén nên dùng số bit payload, không tính framing.
- Khi chỉ cần đưa text chưa nén sang mã kênh hoặc điều chế, dùng **Symbols to UTF-8 Bits**. Đây là điểm chuyển đổi rõ ràng từ miền ký tự sang miền bit.

Luồng mẫu phân tích: `Text Symbol Source → Source Information Analyzer`. Luồng mã hóa nguồn: `Text Symbol Source → Huffman Symbol Encoder → ...bit channel... → Huffman Symbol Decoder → Symbol Error Rate`.

## Hợp đồng kích thước tín hiệu

Mọi port phải mang mảng một chiều, không rỗng. Runtime không còn tự cắt phần dư hoặc để BER so sánh theo nhánh ngắn hơn:

- Hamming (7,4): encoder dùng dạng hệ thống quen thuộc trong giáo trình `c = [d1 d2 d3 d4 p1 p2 p3]`, yêu cầu input chia hết cho 4 và tạo `7/4` số phần tử. Decoder yêu cầu input chia hết cho 7, sửa tối đa một bit lỗi trong mỗi codeword rồi trả về bốn bit dữ liệu đầu tiên.
- Repetition-3: encoder tạo kích thước gấp 3; decoder yêu cầu input chia hết cho 3.
- QPSK: modulator yêu cầu số bit chẵn và tạo một symbol trên hai bit; demodulator khôi phục hai bit trên một symbol.
- Differential, BPSK, AWGN và Rayleigh phải bảo toàn chính xác kích thước input/output.
- Huffman, Shannon-Fano, RLE và ZIP kiểm tra output decoder theo header/count trong stream; dữ liệu lỗi hoặc thiếu không được âm thầm chấp nhận.
- BER Meter yêu cầu `reference` và `estimate` có kích thước hoàn toàn bằng nhau.
- Python Block mặc định `output_size = same`. Chỉ đặt một số nguyên dương hoặc `any` khi block được chủ ý thiết kế để thay đổi kích thước.

Các tham số `length`, `repeat`, `weights`, SNR và `output_size` được kiểm tra trước khi chạy; input trùng kết nối, port không tồn tại và output khai báo thiếu/thừa cũng bị từ chối.

## Lưu dự án

- **New** tạo một simulation trống, trả cấu hình Experiment về mặc định, xóa kết quả/preview hiện tại và ngắt liên kết với file đang mở. Nếu project có thay đổi chưa lưu, SignalLab sẽ hỏi xác nhận; lần Save đầu tiên của simulation mới luôn cho chọn tên và vị trí file.
- **Save** lưu toàn bộ sơ đồ, vị trí block, code Python, tham số block và cấu hình Experiment. Lần đầu lưu sẽ hỏi vị trí/tên file; các lần sau ghi lại đúng file đó.
- Nhấn `Ctrl+S` để Save, hoặc `Ctrl+Shift+S` để **Save As** sang một file mới.
- **Open** duyệt và mở file mô phỏng. SignalLab dùng đuôi `.slab.json` để dễ phân biệt, đồng thời vẫn mở được file project `.json` cũ.
- Chấm vàng và nhãn **Unsaved** cạnh tên project báo có thay đổi chưa lưu. Khi New, Open hoặc Reset trong trạng thái này, ứng dụng yêu cầu xác nhận để tránh mất dữ liệu.
- Bản desktop dùng hộp thoại file Windows và ghi file an toàn qua bản tạm; bản web dùng File System Access API nếu trình duyệt hỗ trợ, nếu không Save sẽ tải file xuống.

Với Python Block, viết tự nhiên theo mẫu:

```python
import numpy as np
import scipy as sp
import signallab as sl

def process(signal, params):
    gain = float(params.get("gain", 1.0))
    return sl.signals.normalize_power(signal * gain)
```

Python Block nạp sẵn `np/numpy`, `sp/scipy` và `sl/signallab`; các dòng import vẫn hoạt động và giúp code dễ mang sang notebook. Chỉ cần xử lý một frame và trả về mảng; runtime tự song song hóa các frame Monte-Carlo. API cũ có `inputs, params, context` vẫn được giữ tương thích. Xem tài liệu đầy đủ trong Documents hoặc thư mục `docs/python`. Không lưu code tùy biến từ nguồn không tin cậy rồi chạy.

Trong tab **Block**, vùng `process.py` là Python IDE editor thật với:

- line number, syntax highlighting, active line và fold gutter;
- tự đóng ngoặc, bracket matching, autocomplete và lịch sử undo/redo;
- phím `Tab` thụt bốn spaces như Python;
- font lập trình và màu cú pháp rõ ràng trên nền editor tối.

Nhấn **Open editor** để mở cửa sổ code lớn. Cửa sổ này giữ một bản nháp riêng: **Cancel** đóng mà không thay đổi block, **Apply changes** mới đưa code về simulation. Có thể dùng `Ctrl+S` hoặc `Ctrl+Enter` ngay trong editor để Apply; các phím này không ghi file project khi cửa sổ code đang mở. Thanh trạng thái hiển thị Python 3, UTF-8, số dòng, số ký tự và trạng thái Modified. Các nút **API docs**, **Copy** và **Reset** giúp mở tài liệu, sao chép toàn bộ hoặc khôi phục code template.
