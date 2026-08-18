# Bắt đầu với Python trong SignalLab

Package `signallab` cung cấp các hàm xử lý tín hiệu và truyền thông số có tên, kiểu dữ liệu và quy tắc kiểm tra nhất quán. Package được xây trên NumPy và SciPy; người dùng vẫn có thể gọi trực tiếp hai thư viện nền.

## Import khuyến nghị

```python
import numpy as np
import scipy as sp
import signallab as sl
```

Trong Python Block, ba alias `np`, `sp`, `sl` đã được nạp sẵn. Vẫn nên giữ các dòng import để code có thể sao chép sang notebook hoặc chạy độc lập.

## Ví dụ chuỗi BPSK qua AWGN

```python
bits = sl.sources.random_bits(100_000, seed=2026)
symbols = sl.modulation.bpsk_modulate(bits)
received = sl.channels.awgn(symbols, snr_db=6, seed=17)
estimated = sl.modulation.bpsk_demodulate(received)

print(sl.metrics.ber(bits, estimated))
print(sl.metrics.measured_snr_db(symbols, received))
```

## Viết Python Block

Python Block chỉ xử lý **một frame**. Scheduler của SignalLab tự chạy các frame độc lập trên CPU/GPU phù hợp; không viết `multiprocessing`, thread hoặc vòng lặp Monte-Carlo trong block.

```python
import numpy as np
import scipy as sp
import signallab as sl

def process(signal, params):
    cutoff = float(params.get("cutoff_hz", 1_000))
    sample_rate = float(params.get("sample_rate_hz", 8_000))
    taps = sl.filters.fir_lowpass(cutoff, sample_rate, num_taps=63)
    return sl.filters.apply_fir(signal, taps, mode="same")
```

Mặc định `output_size=same`: output phải có đúng số phần tử như input. Nếu thuật toán chủ ý đổi kích thước, đặt `output_size` thành số nguyên cụ thể hoặc `any`.

## Quy tắc quan trọng

- Signal là mảng NumPy một chiều, không rỗng.
- Bit dùng `int8`, chỉ chứa `0` và `1`.
- Các hàm decoder/metric không tự cắt dữ liệu để làm cho kích thước khớp.
- `seed=-1` hoặc `None` tạo ngẫu nhiên mới; seed không âm cho kết quả tái lập.
- SNR dùng dB; công suất dùng trung bình `mean(|x|²)`.
- Hàm có lỗi tham số sẽ ném `ValueError` với thông báo chỉ rõ điều kiện sai.

## Chọn đúng lớp API

| Nhu cầu | Module |
|---|---|
| Sinh bit, symbol, đổi text/bit | `sl.sources` |
| Năng lượng, công suất, dB, lấy mẫu | `sl.signals` |
| FIR, matched filter, RRC | `sl.filters` |
| BPSK, QPSK | `sl.modulation` |
| AWGN, Rayleigh, BSC | `sl.channels` |
| Repetition, Hamming (7,4) | `sl.coding` |
| BER, SER, EVM, SNR đo được | `sl.metrics` |
