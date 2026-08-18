# Python Block: viết thuật toán tự nhiên

## API khuyến nghị

```python
def process(signal, params):
    return output
```

`signal` là dữ liệu cổng `in` của một frame. `params` là dictionary gồm tham số block, trạng thái Experiment hiện tại và biến toàn cục. `output` có thể là list hoặc mảng NumPy một chiều; runtime bọc thành cổng `out`.

## Đọc SNR và trạng thái Experiment

Runtime tạo lại các giá trị này cho **từng frame tại từng step SNR**:

| Khóa | Ý nghĩa |
|---|---|
| `params["snr_db"]` | SNR dB của step đang chạy |
| `params["trial_index"]` | Chỉ số frame trong step, bắt đầu từ 0 |
| `params["frame_seed"]` | Seed thực tế của frame hiện tại |
| `params["device"]` | `"cpu"` hoặc `"gpu"` |
| `params["experiment"]` | Dictionary gộp `snr_db`, `trial_index`, `seed`, `device` |

```python
def process(signal, params):
    snr_db = float(params["snr_db"])
    frame = int(params["trial_index"])
    if frame == 0:
        print(f"Starting SNR point {snr_db} dB")
    return signal
```

Không truyền SNR bằng biến global Python và không tự viết vòng lặp sweep trong block. **Run Benchmark** gọi block nhiều lần và cập nhật `params["snr_db"]` đúng step tự động. **Run once** dùng giá trị SNR Start.

## Khối Variables

Thêm **Configuration → Variables** vào canvas và khai báo mỗi dòng một biến bằng Python literal:

```python
symbol_rate = 1_000_000
rolloff = 0.35
modulation = "QPSK"
pilot_indices = [7, 21, 43]
metadata = {"course": "Digital Communications", "group": 2}
```

Mỗi simulation chỉ có một Variables block và không cần nối dây. Engine đọc nó trước khi thực thi graph, bất kể vị trí block trên canvas. Python Block đọc biến theo hai cách tương đương:

```python
def process(signal, params):
    fs = float(params["symbol_rate"])
    rolloff = float(params["variables"]["rolloff"])
    return signal
```

Hỗ trợ `None`, boolean, số hữu hạn, chuỗi, list, tuple và dictionary có khóa chuỗi. Để file simulation an toàn và tái lập, Variables không chạy biểu thức, import, gọi hàm hoặc tham chiếu biến khác. Các tên runtime `snr_db`, `trial_index`, `frame_seed`, `device`, `experiment`, `variables` được dành riêng. Nếu khai báo sai, block Variables được highlight đỏ và lỗi có số dòng xuất hiện trong Console.

Thứ tự ưu tiên là: Variables → tham số riêng của Python Block → khóa runtime. Vì vậy SNR và seed runtime không thể bị ghi đè ngoài ý muốn.

## Alias có sẵn

| Alias | Giá trị |
|---|---|
| `np`, `numpy` | package NumPy |
| `sp`, `scipy` | package SciPy |
| `sl`, `signallab` | package SignalLab |
| `signal` | input hiện tại, dành cho code tương thích |

Các câu lệnh `import numpy`, `import scipy`, `import signallab` vẫn hoạt động bình thường.

## Tham số

```python
def process(signal, params):
    gain_db = float(params.get("gain_db", 0.0))
    gain = np.sqrt(sl.signals.db_to_linear(gain_db))
    return np.asarray(signal) * gain
```

Luôn dùng default hợp lý và chuyển kiểu rõ ràng. Nếu tham số sai miền, chủ động ném `ValueError`:

```python
if gain_db > 60:
    raise ValueError("gain_db must not exceed 60 dB")
```

Thông báo sẽ xuất hiện ở Console và block được highlight đỏ.

## Contract kích thước

- `same`: output phải bằng input; lựa chọn an toàn mặc định.
- Số nguyên dương, ví dụ `2048`: output phải đúng độ dài đó.
- `any`: chỉ dùng khi độ dài phụ thuộc dữ liệu và không thể khai báo trước.

## API nhiều cổng cũ

Project cũ có thể dùng:

```python
def process(inputs, params, context):
    x = inputs["in"]
    return {"out": x}
```

`context` chứa backend và seed nội bộ. API này được giữ để tương thích; block mới nên dùng API hai đối số để dễ đọc và tái sử dụng.

## Song song hóa

Không tạo process, thread hay CUDA stream trong `process`. SignalLab biên dịch DAG một lần và phân phối các frame Monte-Carlo độc lập. Một block chỉ cần là hàm thuần theo input, params và seed của block.

Tránh biến global thay đổi được, ghi cùng một file từ nhiều frame, hoặc giữ reference đến buffer của frame trước. Những thao tác đó làm kết quả phụ thuộc thứ tự worker.

## Debug

1. Chạy **Run once** với frame nhỏ.
2. Chọn block, xem toàn bộ input/output trong tab Block.
3. Hover port để xem dtype, shape, min/mean/max và sample.
4. Chỉ sau khi dữ liệu đúng mới chạy **Run Benchmark**.

## Ví dụ lọc và chuẩn hóa

```python
import numpy as np
import scipy as sp
import signallab as sl

def process(signal, params):
    fs = float(params.get("sample_rate_hz", 48_000))
    cutoff = float(params.get("cutoff_hz", 6_000))
    taps = sl.filters.fir_lowpass(cutoff, fs, num_taps=101)
    filtered = sl.filters.apply_fir(signal, taps, mode="same")
    return sl.signals.normalize_power(filtered)
```
