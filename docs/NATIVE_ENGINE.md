# Native Monte-Carlo engine

## Mục tiêu

Native engine là đường thực thi chuyên cho benchmark BER tốc độ cao trên một máy. React/FastAPI vẫn quản lý project, job, progress và kết quả; hot loop chạy trong module C++20 `_native_core` qua pybind11 và nhả Python GIL. oneTBB chia iteration space trên các core mà không spawn hoặc pickle graph sang nhiều Python process.

`Run once` luôn dùng Trace Executor Python để giữ đầy đủ port data. `Run Benchmark` với `Execution engine = Auto` biên dịch graph sang native plan khi graph thuộc tập được hỗ trợ, nếu không sẽ fallback về NumPy/CuPy mà không đổi kết quả UI.

## Graph được tăng tốc

Phiên bản native 0.2 nhận diện topology theo type/port, không phụ thuộc id, vị trí hoặc chiều hiển thị:

- `Bit Source → BPSK → AWGN → BPSK Demodulator → BER Meter`.
- Chuỗi trên có thêm `Hamming (7,4) Encoder/Decoder`.
- Chuỗi trên có thêm `Repetition-3 Encoder/Decoder`.
- Thay BPSK bằng QPSK, gồm cả chuỗi không mã hóa, Hamming và Repetition khi coded length chia hết cho 2.
- Chuỗi 16-QAM/AWGN/16-QAM Demodulator/BER không mã hóa.

AWGN có thể lấy SNR từ Experiment hoặc giá trị fixed của block. Planner yêu cầu topology chính xác; graph có thêm sink quan sát, Python Block, codec khác hoặc topology khác sẽ chạy compatibility engine để không làm sai metric waveform. Results hiển thị native plan hoặc lý do Auto fallback. Chọn `Native` thay vì `Auto` để yêu cầu nghiêm ngặt; graph không hỗ trợ sẽ báo lỗi rõ ràng.

## Tối ưu đang dùng

- Fused metric-only kernel: không tạo mảng source/encoded/symbol/noise/decoded trong benchmark.
- BPSK + AWGN + hard decision được rút gọn đúng phân phối thành binary decision error với `p = Q(1/sigma)`; Run once vẫn tạo waveform AWGN thật để quan sát.
- QPSK dùng hai binary decision độc lập theo đúng biên độ I/Q hiện tại. 16-QAM lấy mẫu trực tiếp bốn vùng quyết định `(-∞,-2),[-2,0),[0,2),[2,∞)` từ CDF Gaussian; không cần sinh số Gaussian hoặc symbol trung gian nhưng vẫn giữ đúng phân phối BER.
- Philox4x32x10 counter-based RNG: kết quả không phụ thuộc số thread.
- Hamming systematic và Repetition-3 được encode/channel/decode/reduce trong cùng kernel.
- oneTBB `parallel_reduce` với grain lớn và `task_arena` giới hạn worker.
- Python chỉ gọi native theo tile; early-stop và Cancel được kiểm tra giữa các tile.
- JobManager chỉ cho một benchmark nặng chiếm tài nguyên máy tại một thời điểm, tránh nhiều job cùng dùng toàn bộ core.

## Build và benchmark

`setup.bat` cài dependency và build native engine tự động. Có thể chạy riêng:

```bat
build_native.bat
benchmark.bat
benchmark.bat --bits 65536 --frames 1000
benchmark.bat --modulation qpsk --coding hamming74 --repeats 5
benchmark.bat --modulation qam16 --coding none --min-speedup 2
benchmark_regression.bat
```

Benchmark thực hiện warm-up rồi báo median của nhiều lượt; `--min-speedup` trả exit code 2 nếu native thấp hơn ngưỡng. `benchmark_regression.bat` khóa ba workload BPSK, QPSK và 16-QAM ở ngưỡng tối thiểu 2× để phát hiện tụt hiệu năng lớn mà vẫn chịu được nhiễu tải nền.

Trên máy phát triển Intel Core Ultra 7 258V (8 logical CPU), workload Hamming 10.000 frame × 4.096 source bit đạt 398,1 Mbit/s với native 8 worker so với 18,3 Mbit/s bằng Python/NumPy một worker, nhanh hơn 21,79 lần. Đây là số đo tham khảo của đúng workload và máy đó; dùng `benchmark.bat` để lấy số liệu tại máy triển khai.

Build cần Visual Studio 2022 C++ Build Tools. CMake, pybind11 và oneTBB được pin trong `backend/requirements-native.txt`; người dùng không cần mở Developer Command Prompt.

Native artifacts `_native_core*.pyd` và `tbb*.dll` được sinh trong `backend/app`, không commit vào Git, và được PyInstaller thu vào release desktop.

## Reproducibility và semantics

Native RNG dùng key kết hợp block seed, Experiment seed, node id, SNR index, trial index và counter trong frame. Cùng graph/seed cho cùng error count dù thay số worker. Native engine không cam kết bit-for-bit trùng RNG NumPy cũ; correctness được khóa bằng deterministic tests, BER giảm theo SNR và test catalog/contract hiện có.

Scientific gate đo hàng triệu bit và yêu cầu BER BPSK, QPSK, 16-QAM nằm trong khoảng tin cậy 6σ quanh công thức/CDF của đúng runtime convention. QPSK hiện diễn giải SNR theo năng lượng symbol giống engine Python hiện hữu; native không âm thầm đổi sang một quy ước Eb/N0 khác.

## GPU

GPU CUDA/CuPy cũ vẫn là compatibility backend. Máy phát triển hiện dùng Intel Arc 140V nên native GPU phù hợp về sau là plugin SYCL. Plugin chưa được build mặc định vì máy chưa có oneAPI compiler/runtime; Auto chỉ công bố/chọn backend đã thực sự khả dụng và đo được. Không cài toolchain hệ thống lớn một cách ngầm định trong `setup.bat`.

## Mở rộng native catalog

Mỗi kernel mới phải có matcher topology/port, deterministic test giữa một/nhiều worker, statistical hoặc round-trip correctness test, fallback test và benchmark trước/sau. Không dùng shortcut phân phối nếu graph có sink cần thống kê waveform trung gian mà kernel không tái tạo đúng metric đó.
