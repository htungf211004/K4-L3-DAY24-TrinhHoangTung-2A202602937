# Baseline — CP1

1. **Mỗi lần chạy baseline đã có agent_id/run_id và danh tính người dùng để kiểm quyền chưa?**

   Chưa: `_naive_loop()` chỉ nhận `message` và `llm`, không tạo `agent_id` hay `run_id` (`agent/loop.py:27`). Dù `run_once()` có `principal_id` mặc định là `support_l1` (`agent/loop.py:58`), khi runner còn là scaffold, nó gọi lại `_naive_loop(message, llm)` mà không truyền danh tính người dùng (`agent/loop.py:73`, `agent/loop.py:74`). Vì vậy, baseline không dùng danh tính đó để kiểm quyền trước khi đọc hồ sơ hoặc gửi dữ liệu.

2. **Trước http_post, có policy kiểm mục đích, quyền và loại dữ liệu không? Ai thực sự quyết định gửi?**

   Không có bước kiểm mục đích, quyền hay loại dữ liệu trước `read_customer()` và `http_post()` (`agent/loop.py:39`, `agent/loop.py:44`). Ticket là dữ liệu, nhưng baseline ghép nội dung ticket rồi dùng kết quả `find_injection()` để chọn khách hàng và địa chỉ gửi, tức là làm theo chỉ thị nằm trong ticket (`agent/loop.py:31`, `agent/loop.py:32`, `agent/loop.py:34`, `agent/loop.py:37`, `agent/loop.py:44`). `http_post()` chỉ kiểm URL có đúng HTTP, host `127.0.0.1` và cổng `10024` hay không; nó không kiểm dữ liệu nào được phép gửi (`agent/tools.py:76`, `agent/tools.py:77`, `agent/tools.py:78`, `agent/tools.py:84`).

3. **Dòng nào tạo body POST, và file nào ghi lại việc sink đã nhận body đó?**

   Hồ sơ đọc được được thêm vào `collected` tại `agent/loop.py:39`; body `{"records": collected}` được tạo ngay trong lời gọi `http_post()` tại `agent/loop.py:44` và gửi dưới dạng JSON tại `agent/tools.py:84`. Sink ghi đường dẫn cùng body đã nhận vào `reports/sink.log` (`sink/sink.py:37`, `sink/sink.py:45`, `sink/sink.py:46`, `sink/sink.py:47`); bản sao cần giữ cho CP2 là `reports/attack-before.log`, trong đó phải kiểm được hồ sơ synthetic `KH-000999` và các trường `cccd`, `bank_account`.
