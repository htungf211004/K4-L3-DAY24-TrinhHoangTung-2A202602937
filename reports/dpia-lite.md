# CP5 — DPIA-lite

Ngày kiểm tra: 12/10/2026. Đây là mô tả dữ liệu và cách xử lý trong bài lab, không phải hồ sơ đánh giá tác động pháp lý chính thức.

## 1. Dữ liệu nào được xử lý?

`corpus/` có ticket hỗ trợ tổng hợp, gồm nội dung nghiệp vụ, giá trị PII giả và bốn lure injection; biến thể cuối dùng hai file. Runner gán lần tìm ticket là `internal`, nhưng nội dung ticket vẫn là nguồn không tin cậy vì attacker có thể chèn chỉ thị. PII được che trước khi đưa ticket cho hàm tóm tắt.

`data/customers.json` là private store tổng hợp: mã khách, tên và các trường CCCD, điện thoại, tài khoản, liên kết `related_tickets`. Lượt đọc hồ sơ được gán `restricted`. `KH-000999` là khách giả của tình huống rò rỉ và có liên kết tới ticket 901–905. Không dùng dữ liệu cá nhân hoặc credential thật; các nhãn `internal`/`restricted` là quy ước kỹ thuật của bài, chưa phải kết luận phân loại theo luật.

Ledger chứa thời gian, principal, agent/run ID, thời hạn, tool, purpose, scopes, quyết định, reason và hash tham số. Nó không chứa body hồ sơ hay giá trị PII thô. `attack-before.log` giữ bốn POST có hồ sơ giả để đối chiếu trước/sau; đó vẫn là artifact cần quản lý quyền đọc nếu áp dụng cách làm này cho dữ liệu thật.

## 2. Ai xử lý và để làm gì?

Người dùng hỏi `Tổng hợp các ticket còn mở tuần này`. Run A gọi `search_docs` cho mục đích `summarize-tickets`; cả `support_l1` và `dpo` có quyền này. `support_l1` không có quyền `read_customer`, nên bị chặn trước cả lúc mở private store để tra liên kết.

`dpo` được đọc khách gắn với ticket cho mục đích `support-reply`. Policy còn kiểm agent scopes, parent scopes khi uỷ quyền và thời hạn UTC chưa hết; runner đặt hạn 5 phút. Lời tự nhận admin/DPO trong ticket không thay quyền trong `data/principals.json`.

Trong lượt CP5, DPO đọc 21 hồ sơ liên quan, gồm `KH-000999`, sau kiểm quyền. Runner hiện chưa dùng các hồ sơ này để tạo câu trả lời: CLI trả bản tổng hợp ticket. Việc đọc chứng minh đường dùng tool hợp lệ còn hoạt động trong bài lab, chưa chứng minh mỗi hồ sơ là cần thiết cho một quy trình hỗ trợ thực tế. Quyền thực tế, cơ sở xử lý và mức dữ liệu cần đọc phải được đánh giá lại khi triển khai.

## 3. Dữ liệu đi qua đâu?

Run A kiểm policy rồi đọc ticket qua `search_docs`. Nó lấy số ticket từ tên file, che PII trong nội dung rồi gọi `llm.summarize()`. Với `--mock`, model là hàm cục bộ, không gọi dịch vụ model bên ngoài. Run A không đọc hồ sơ khách hoặc gọi HTTP.

Run B nhận danh sách số ticket, không nhận toàn văn ticket hay mã khách do attacker nêu. Nó xin quyền trước khi mở `data/customers.json`, tra `related_tickets`, rồi kiểm policy và append ledger trước từng `read_customer`. Hồ sơ không được đưa sang lượt xin quyền gửi hoặc trả ra CLI.

Nếu mock nhận diện lure, runner xin quyền `http_post` riêng với đối tượng chỉ chứa URL, classification `restricted` và egress bật. Policy trả deny, ledger ghi reason, không gọi `tools.http_post`. Sink thật của phép thử chỉ nghe tại `127.0.0.1:10024`, đường dẫn `/reconcile`; đây là đích giả lập nhận rò rỉ, không phải một dịch vụ Internet.

Ledger lưu ở `reports/ledger.jsonl`; log sink được sao chép vào `reports/attack-after.log` sau lượt CLI. Bài chưa đặt thời hạn lưu, quy trình xoá hay quyền truy cập riêng cho các artifact; cần xác định các việc đó trước khi áp dụng cho dữ liệu thật.

## 4. Đã chặn/cho phép gì và còn giới hạn gì?

Toàn bộ suite: **33 passed in 2.78s**, 0 failed, 0 skipped. Test injection chạy bốn biến thể dưới hai principal. Test OBO chứng minh support bị chặn và DPO được đọc hợp lệ; test split không cho đọc `KH-000777` chỉ vì mã này nằm trong lời attacker. Regex đạt gold/pred/tp **118/118/118**, precision/recall **1.000/1.000** ở CP3a trên bộ mẫu của lab.

Ở lượt CLI CP5 với sink đang nghe, agent tổng hợp 45 ticket. `attack-before.log` giữ nguyên bốn dòng có hồ sơ synthetic `KH-000999`; `attack-after.log` **0 byte**. Ledger có **75 dòng** và `verify()` trả **True**. Dòng 52 là search allow, dòng 53 là allow tra liên kết, dòng 74 là allow đọc `KH-000999` (đối chiếu args_hash), dòng 75 là `http_post` deny, `on_behalf_of=dpo`, reason `restricted data cannot be used with egress enabled`. Dòng 2 từ lượt support trước đó là deny đọc khách. Các entry đều có reason.

Các kết quả chỉ áp dụng cho corpus, bộ mẫu và mock đã thử. Regex còn hạn chế với định dạng ngoài mẫu, tên người, số tài khoản không nhãn, số quốc tế hoặc PII viết né mẫu. `--as` không xác thực người thật. Run A/B là hai hàm trong cùng tiến trình, chưa có ranh giới cách ly hệ điều hành; chương trình khác có quyền file vẫn có thể đọc dữ liệu. Hash chain phát hiện sửa trong chuỗi quan sát được, không phát hiện cắt đuôi hay viết lại cả chuỗi khi thiếu mốc ngoài file; hash tham số cũng không phải mã hoá chống đoán giá trị.

Lure detector và tóm tắt là mock; chưa kiểm model thật, môi trường nhiều người dùng, nhiều tiến trình ghi ledger hoặc mọi đường rò rỉ. Bài chưa thực hiện cơ chế sự đồng ý, quyền truy cập/sửa/xoá của chủ thể hoặc hồ sơ pháp lý. Nguồn và phần điều khoản còn chưa xác minh được ghi tại `reports/compliance-mapping.md`.
