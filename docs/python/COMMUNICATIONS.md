# Điều chế và kênh truyền

## `sl.modulation.bpsk_modulate(bits, amplitude=1.0)`

Ánh xạ `0 → +A`, `1 → -A`. Input chỉ được chứa bit 0/1.

## `sl.modulation.bpsk_demodulate(symbols, threshold=0.0)`

Quyết định cứng trên phần thực: sample nhỏ hơn threshold thành bit 1.

## `sl.modulation.qpsk_modulate(bits, normalize=True)`

Ghép hai bit liên tiếp thành nhánh I và Q theo ánh xạ `(1-2bI) + j(1-2bQ)`. Khi `normalize=True`, chia `sqrt(2)` để năng lượng symbol trung bình bằng 1. Số bit phải chẵn.

## `sl.modulation.qpsk_demodulate(symbols)`

Quyết định cứng dấu phần thực/ảo và trả bit xen kẽ I/Q đúng thứ tự của modulator.

## OOK

- `sl.modulation.ook_modulate(bits, amplitude=1.0)` ánh xạ `0 → 0`, `1 → amplitude`.
- `sl.modulation.ook_demodulate(symbols, threshold=0.5)` quyết định cứng theo phần thực tại ngưỡng cấu hình.

## 8-PSK Gray

- `sl.modulation.psk8_modulate(bits)` ghép ba bit thành một trong tám pha trên đường tròn đơn vị. Số bit phải chia hết cho 3.
- `sl.modulation.psk8_demodulate(symbols)` chọn pha gần nhất và khôi phục ba bit Gray trên mỗi symbol.

## 16-QAM Gray

- `sl.modulation.qam16_modulate(bits, normalize=True)` ghép bốn bit thành symbol vuông I/Q; mặc định chia `sqrt(10)` để năng lượng symbol trung bình bằng 1 với dữ liệu đều.
- `sl.modulation.qam16_demodulate(symbols, normalized=True)` quyết định cứng theo các biên `-2, 0, +2` trong constellation chưa chuẩn hóa và trả bốn bit trên mỗi symbol.

## `sl.channels.awgn(signal, snr_db, seed=-1, measured=True)`

Thêm nhiễu Gaussian trắng thực hoặc phức. Khi `measured=True`, công suất tín hiệu được đo trên chính frame input; khi `False`, hàm giả định công suất tín hiệu bằng 1.

```python
rx = sl.channels.awgn(tx, snr_db=8.0, seed=123)
```

Với tín hiệu complex, tổng công suất nhiễu được chia đều cho I và Q. `snr_db` ở đây là tỷ số công suất sample, không tự chuyển đổi từ Eb/N0; người dùng cần tính hệ số theo số bit/symbol, coding rate và oversampling trong thí nghiệm tương ứng.

## `sl.channels.rayleigh_fading(signal, snr_db=None, seed=-1, flat=False)`

Nhân tín hiệu với hệ số fading phức có công suất trung bình 1. `flat=False` sinh hệ số độc lập theo sample; `flat=True` dùng một hệ số cho toàn frame. Nếu có `snr_db`, AWGN được thêm sau fading.

## `sl.channels.binary_symmetric_channel(bits, crossover_probability, seed=-1)`

Lật từng bit độc lập với xác suất `p` trong `[0,1]`. Đây là kênh nhị phân đối xứng dùng trong bài lý thuyết kênh rời rạc.

## Ví dụ BER BPSK

```python
bits = sl.sources.random_bits(200_000, seed=1)
tx = sl.modulation.bpsk_modulate(bits)
for snr_db in range(0, 11, 2):
    rx = sl.channels.awgn(tx, snr_db, seed=snr_db)
    estimate = sl.modulation.bpsk_demodulate(rx)
    print(snr_db, sl.metrics.ber(bits, estimate))
```
