# Quy ước API và dữ liệu

## Mảng một chiều

Mọi hàm nhận tín hiệu đều dùng `numpy.asarray` và yêu cầu shape dạng `[N]`. Shape `[N, 1]` hay `[1, N]` bị từ chối thay vì tự `flatten`, vì việc tự đổi shape dễ che lỗi ghép nối block.

```python
x = np.asarray([1.0, 0.5, -0.2])      # đúng: shape (3,)
x = np.asarray([[1.0, 0.5, -0.2]])    # sai: shape (1, 3)
```

## Bit, symbol và sample

- **Bit vector**: `np.ndarray`, `dtype=np.int8`, giá trị `0/1`.
- **Symbol rời rạc**: mảng Unicode một chiều, ví dụ `['A', 'B', 'A']`.
- **Sample băng gốc**: mảng float hoặc complex một chiều.

Các hàm `coding` và metric BER kiểm tra chặt bit. Các hàm signal/filter giữ được tín hiệu complex.

## Seed

Tất cả hàm ngẫu nhiên dùng `numpy.random.Generator`:

- `seed=-1` hoặc `seed=None`: entropy mới ở mỗi lần gọi.
- `seed=0..4294967295`: tái lập chính xác với cùng phiên bản thuật toán.
- Seed ngoài miền hợp lệ: `ValueError`.

Trong mô phỏng benchmark, nên đặt seed cụ thể ở từng block ngẫu nhiên và Experiment nếu cần tái lập toàn bộ phép đo.

## Đơn vị

Tên tham số ghi rõ đơn vị: `_hz`, `_db`, `_symbols`. Công suất là `mean(|x|²)`, năng lượng là `sum(|x|²)`. Hàm `db_to_linear` và `linear_to_db` chuyển **tỷ số công suất** nên dùng hệ số 10.

## Kiểm tra kích thước

Các codec yêu cầu input chia hết cho kích thước từ mã. Các metric yêu cầu hai vector bằng nhau tuyệt đối. Không padding, truncate hoặc dùng `min(length_a, length_b)` ngầm.

## NumPy và SciPy trực tiếp

Package không khóa thư viện nền. Có thể kết hợp API mức cao với hàm chuyên sâu:

```python
def process(signal, params):
    spectrum = np.fft.fft(signal)
    peaks, _ = sp.signal.find_peaks(np.abs(spectrum))
    return np.asarray(peaks, dtype=float)
```

Khi output đổi kích thước như ví dụ trên, cấu hình contract của Python Block phải phản ánh điều đó.
