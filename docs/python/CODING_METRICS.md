# Mã kênh và chỉ tiêu chất lượng

## `sl.coding.repetition_encode(bits, repeat=3)`

Lặp mỗi bit `repeat` lần. Output dài `repeat × N`.

## `sl.coding.repetition_decode(bits, repeat=3)`

Quyết định đa số trên từng nhóm. Input phải chia hết cho `repeat`; output dài `N/repeat`. Với repeat chẵn, trường hợp hòa được quyết định là 0, vì vậy thực hành thường chọn repeat lẻ.

## `sl.coding.hamming74_encode(bits)`

Mã Hamming hệ thống theo thứ tự giáo trình:

`[d1, d2, d3, d4, p1, p2, p3]`

với:

- `p1 = d1 ⊕ d2 ⊕ d4`
- `p2 = d1 ⊕ d3 ⊕ d4`
- `p3 = d2 ⊕ d3 ⊕ d4`

Input phải chia hết cho 4; output dài `7N/4`.

```python
sl.coding.hamming74_encode([1, 1, 0, 1])
# array([1, 1, 0, 1, 1, 0, 0], dtype=int8)
```

## `sl.coding.hamming74_decode(bits)`

Tính syndrome, sửa tối đa một bit lỗi trong mỗi codeword và trả bốn bit dữ liệu hệ thống. Input phải chia hết cho 7. Hamming (7,4) không đảm bảo sửa đúng khi một codeword có từ hai lỗi trở lên.

## `sl.metrics.bit_errors(reference, estimate)` và `ber(...)`

Đếm lỗi bit hoặc trả tỷ lệ lỗi bit. Hai vector phải cùng kích thước và chỉ chứa 0/1.

## `sl.metrics.symbol_errors(reference, estimate)` và `ser(...)`

Tương tự BER nhưng dùng được với symbol Unicode, số nguyên hay complex; so sánh phần tử chính xác.

## `sl.metrics.evm_rms(reference, estimate, percent=True)`

Tính RMS EVM chuẩn hóa theo RMS của reference. Mặc định trả phần trăm; đặt `percent=False` để nhận tỷ lệ.

## `sl.metrics.measured_snr_db(clean, noisy)`

Ước lượng `10log10(Pclean / P(noisy-clean))` khi biết tín hiệu sạch. Hai vector phải bằng kích thước.

## Bài thực hành gợi ý

1. Tạo cùng một nguồn bit và so sánh BER BPSK có/không Hamming tại nhiều SNR.
2. Đặt seed cố định để hai nhánh dùng cùng dữ liệu, sau đó tăng frame đến khi đủ số lỗi thống kê.
3. So sánh BER đo được với giới hạn lý thuyết; ghi rõ đang dùng SNR/sample hay Eb/N0.
4. Gây một và hai lỗi trong từng codeword để quan sát giới hạn sửa lỗi của Hamming.
