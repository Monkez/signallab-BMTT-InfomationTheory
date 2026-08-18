# Nguồn và phép đo tín hiệu

## `sl.sources.random_bits(length, seed=-1)`

Sinh `length` bit đồng xác suất. Trả về vector `int8`. `length` phải là số nguyên dương.

```python
bits = sl.sources.random_bits(4096, seed=10)
```

## `sl.sources.random_symbols(alphabet, probabilities, length, seed=-1)`

Sinh nguồn rời rạc không nhớ. `alphabet` phải gồm các symbol duy nhất, không rỗng. `probabilities` có một trọng số dương hữu hạn cho mỗi symbol; hàm tự chuẩn hóa tổng trọng số.

```python
symbols = sl.sources.random_symbols(
    ["A", "B", "C", "D"],
    [0.5, 0.25, 0.125, 0.125],
    length=10_000,
    seed=2026,
)
```

## `sl.sources.text_symbols(text, repeat=1)`

Tách chuỗi Unicode thành vector ký tự. Dùng hàm này cho các bài entropy, Huffman, Shannon–Fano trước khi chuyển sang bit.

## `sl.sources.text_to_bits(text, encoding='utf-8')`

Mã hóa text thành byte rồi tách mỗi byte theo thứ tự bit lớn trước. Kết quả phù hợp với mã kênh và điều chế.

## `sl.sources.bits_to_text(bits, encoding='utf-8', errors='strict')`

Ghép bit thành byte và giải mã text. Chiều dài bit phải chia hết cho 8. `errors` tuân theo Python codec, ví dụ `strict`, `replace`, `ignore`.

## `sl.signals.energy(signal)`

Tính năng lượng rời rạc `Σ|x[n]|²`, trả về `float`.

## `sl.signals.average_power(signal)`

Tính công suất trung bình `mean(|x[n]|²)`. Đây là quy ước dùng trong AWGN và EVM.

## `sl.signals.rms(signal)`

Tính `sqrt(average_power(signal))`.

## `sl.signals.normalize_power(signal, target_power=1.0)`

Nhân toàn bộ tín hiệu với một hệ số để công suất đạt `target_power`. Tín hiệu công suất bằng 0 bị từ chối vì không thể chuẩn hóa.

```python
x = sl.signals.normalize_power(x, target_power=1.0)
```

## `sl.signals.db_to_linear(value_db)` và `linear_to_db(value, floor_db=None)`

Chuyển tỷ số công suất giữa miền dB và tuyến tính. Input có thể là scalar hoặc mảng. `linear_to_db(0)` trả `-inf`, hoặc trả sàn nếu có `floor_db`.

## `sl.signals.upsample(signal, factor, phase=0)`

Chèn `factor-1` số 0 giữa các sample. `phase` chọn vị trí sample gốc trong mỗi nhóm và phải thỏa `0 <= phase < factor`.

## `sl.signals.downsample(signal, factor, phase=0)`

Giữ mỗi sample thứ `factor`, bắt đầu từ `phase`. Hàm không tự lọc chống alias; hãy lọc thông thấp trước khi giảm tốc nếu phổ có thể chồng lấn.
