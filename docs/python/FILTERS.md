# Bộ lọc và pulse shaping

## `sl.filters.fir_lowpass(cutoff_hz, sample_rate_hz, num_taps=101, window='hamming')`

Thiết kế FIR thông thấp pha tuyến tính bằng `scipy.signal.firwin`. Tần số cắt phải nằm giữa 0 và Nyquist. `num_taps` là số nguyên dương; số tap lẻ thường thuận tiện để có group delay nguyên.

```python
taps = sl.filters.fir_lowpass(3_000, 48_000, num_taps=129)
```

## `sl.filters.fir_bandpass(low_hz, high_hz, sample_rate_hz, num_taps=101, window='hamming')`

Thiết kế FIR thông dải với điều kiện `0 < low < high < fs/2`.

## `sl.filters.apply_fir(signal, taps, mode='same')`

Tích chập bằng FFT của SciPy. Mode:

- `same`: output dài bằng signal; phù hợp contract mặc định của Python Block.
- `full`: toàn bộ tích chập, dài `N + M - 1`.
- `valid`: chỉ phần không cần zero-padding.

```python
def process(signal, params):
    taps = sl.filters.fir_lowpass(2_000, 16_000, 65)
    return sl.filters.apply_fir(signal, taps, mode="same")
```

## `sl.filters.matched_filter(signal, pulse, mode='same')`

Lọc với đáp ứng `conj(pulse[::-1])`, tối ưu SNR tại thời điểm lấy mẫu trong AWGN khi pulse đã biết. Với tín hiệu complex, phép liên hợp được áp dụng tự động.

## `sl.filters.root_raised_cosine(beta, samples_per_symbol, span_symbols=8)`

Sinh tap root-raised-cosine đối xứng và chuẩn hóa năng lượng bằng 1.

- `beta`: hệ số roll-off trong `[0, 1]`.
- `samples_per_symbol`: số sample mỗi symbol, số nguyên dương.
- `span_symbols`: chiều dài xung theo symbol.

```python
rrc = sl.filters.root_raised_cosine(beta=0.35, samples_per_symbol=8, span_symbols=10)
tx = sl.filters.apply_fir(sl.signals.upsample(symbols, 8), rrc, mode="same")
```

Ở máy thu, dùng cùng `rrc` qua `matched_filter`, bù group delay và lấy mẫu đúng phase. API không tự đoán timing vì đây là nội dung quan trọng của bài thực hành đồng bộ.

## Dùng SciPy nâng cao

```python
sos = sp.signal.butter(6, 0.2, output="sos")
y = sp.signal.sosfilt(sos, signal)
```

Khi cần IIR, Welch PSD, resampling polyphase hay tìm peak, gọi trực tiếp `sp.signal`; `signallab` chỉ bọc các thao tác thông dụng để tên và validation nhất quán.
