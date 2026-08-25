# Quy trình phát triển cho AI

1. Kiểm tra `git status` và đọc docs/status.
2. Chốt phạm vi, cập nhật `agents/STATUS.md` khi bắt đầu/kết thúc mốc lớn.
3. Backend: giữ engine độc lập HTTP; thêm test thuật toán và tính tái lập.
4. Frontend: giữ schema khối đồng bộ API; build TypeScript sau thay đổi.
5. Không đưa secret, virtualenv, node_modules hay output build vào git.
6. Dùng `git` cho status/diff/commit/push; không dùng `gh`.
7. Trước bàn giao chạy `test.bat` hoặc pytest + npm build.
8. Giữ ranh giới module: registry block ở `block_registry.py`, processor ở `blocks.py`; dữ liệu/logic BER ở `frontend/src/features/ber`, không đưa trở lại `App.tsx`.
9. Nếu thêm block phải cập nhật backend registry, processor map, frontend fallback catalog, tài liệu và test trong cùng thay đổi.
10. Nếu thêm/sửa bài học Open Samples, cập nhật `samples/catalog.json`; bảo đảm metadata học tập đầy đủ, graph chạy được bằng Run once và `backend/tests/test_samples.py` pass.
11. Khi mở rộng native fast path, cập nhật đồng thời matcher trong `backend/app/native_engine.py`, kernel ở `native/src`, test so sánh/tái lập và `docs/NATIVE_ENGINE.md`; không cho planner nhận topology chưa được chứng minh tương thích.
12. Build native bằng `build_native.bat`; trước release chạy `test.bat`, `benchmark_regression.bat` và `build_app.bat`. Kiểm tra `_native_core` cùng TBB DLL được PyInstaller gom cạnh package backend.
13. Khi sửa Python Custom Block runtime, khóa cả API frame/PORTS cũ, `process_batch`, params riêng từng frame, persistent worker trên Windows và benchmark `benchmark_python.bat`; không suy luận rằng process pool luôn nhanh hơn inline.
14. Numeric UI phải cho phép draft rỗng và scientific notation; không dùng `Number(input.value)` trực tiếp trong controlled input vì `Number("")` biến thao tác xóa thành 0.
15. Sample mới/sửa phải pass cả Run once lẫn benchmark ngắn trong `test_samples.py`; sink metric mới phải đi qua helper tổng hợp dùng chung cho hai đường chạy.
16. Phân biệt frame logic với vector trong frame: không ép sample giáo dục tăng `Source.length` chỉ để benchmark nhanh. Scheduler phải batch nội bộ frame nhỏ; budget frame/error không đặt trần nghiệp vụ tùy ý và phải có test vượt mốc một triệu.
