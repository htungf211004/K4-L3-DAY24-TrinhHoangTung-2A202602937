# CP4 — Token giả trong lịch sử Git

Ngày kiểm tra: 12/10/2026. Dữ liệu của bài lab là token giả vô hiệu; không dùng token để gọi dịch vụ và không chép nguyên giá trị vào báo cáo.

## Scanner và bằng chứng

- Scanner: **Gitleaks 8.30.1**, xác nhận bằng `gitleaks version`; binary đã có trong PATH.
- Commit chứa token giả: **`1bdd849922156c868a5ee9293d68f5b72e242d2c`** (viết ngắn `1bdd849`).
- File trong commit: **`lab-fake-secret.txt:1`**; rule: **`lab24-synthetic-token`**.
- Fingerprint: `1bdd849922156c868a5ee9293d68f5b72e242d2c:lab-fake-secret.txt:lab24-synthetic-token:1`.

Lệnh quét dùng `--redact`, nên phần Finding và Secret của token giả hiện `REDACTED`:

```powershell
gitleaks git --config .gitleaks.toml --redact --verbose .
gitleaks dir --config .gitleaks.toml --redact --verbose .
```

| Lần kiểm | Kết quả | Exit code |
|---|---|---:|
| Lịch sử, cấu hình ban đầu | 8 commit; 1 finding, đúng file/commit/rule nêu trên | 1 |
| File hiện tại, cấu hình ban đầu | 1 finding `generic-api-key` tại `.venv/Lib/site-packages/setuptools/_distutils/msvccompiler.py:45` | 1 |
| Lịch sử, sau chỉnh allowlist | Vẫn 8 commit và 1 finding token giả; rule của lab vẫn hoạt động | 1 |
| File hiện tại, sau chỉnh allowlist | `no leaks found` | 0 |

Exit code 1 của quét lịch sử là kết quả mong đợi của CP4. File chứa token đã bị xoá ở commit sau nhưng nội dung cũ vẫn nằm trong lịch sử.

## Finding trong thư viện và phạm vi allowlist

Đã mở đúng dòng 45 của `msvccompiler.py`: biến `RegEnumKey` nhận hàm cùng tên từ module `win32api`. Đây là phép gán hàm đọc registry trong thư viện `setuptools`, không phải credential. Rule tổng quát nhận nhầm tên/giá trị của phép gán này.

Chỉ thêm một allowlist đường dẫn vào `.gitleaks.toml`: regex `^\.venv[\\/]`, khớp thư mục `.venv` ở gốc repo trên cả hai kiểu dấu phân cách. Không bỏ qua cả repo, không allowlist commit token giả và không tắt `lab24-synthetic-token` hoặc các rule mặc định. Đã chạy lại cả quét lịch sử và quét file sau sửa. Phạm vi sạch được báo ở đây không bao gồm thư viện trong `.venv/`.

Lượt quét sau khi viết báo cáo từng báo thêm 2 finding `generic-api-key`, do hai báo cáo trích nguyên phép gán bị nhận nhầm nói trên. Đã đổi đoạn trích thành mô tả bằng lời, giữ nguyên allowlist chỉ cho `.venv/`. Quét lại file hiện tại trả `no leaks found`, exit code 0.

## Dependency và hook

Đã tạo `requirements.lock` bằng pip-tools **7.6.2** trên Python **3.11.9**, từ `requirements.txt`, với phiên bản chính xác và SHA-256 cho cả 11 dependency trực tiếp/gián tiếp. Đã cài lại cả 11 package với `pip install --require-hashes -r requirements.lock --force-reinstall`; exit code 0. Việc cài lại buộc pip kiểm artifact tải/cached thay vì chỉ báo package đã có sẵn. Lock này được sinh trên Windows/Python 3.11; nếu đổi nền tảng hoặc Python cần kiểm lại dependency theo môi trường đích. Cách sinh hash dùng theo [tài liệu pip-tools](https://pip-tools.readthedocs.io/en/stable/#using-hashes).

`.pre-commit-config.yaml` dùng repo chính thức `https://github.com/gitleaks/gitleaks`, pin `rev: v8.30.1`, hook `gitleaks-system`, `pass_filenames: false` và chỉ rõ `.gitleaks.toml`. Đã chạy `pre-commit install`, hook được cài tại `.git/hooks/pre-commit`; `pre-commit run --all-files` báo `Passed`.

Hook này dùng Gitleaks trong PATH. Theo [định nghĩa hook tại v8.30.1](https://github.com/gitleaks/gitleaks/blob/v8.30.1/.pre-commit-hooks.yaml), entry dùng `git --pre-commit --redact --staged --verbose`: phạm vi là diff đã stage. Vì vậy kết quả hook không thay cho hai lệnh quét toàn bộ lịch sử/file hiện tại ở trên. Chưa stage hoặc commit thay đổi CP4.

## Nếu đây là secret thật

Phải thu hồi hoặc **rotate** tại dịch vụ cấp token trước, rồi cập nhật nơi dùng hợp lệ. Kiểm nhật ký truy cập để tìm việc dùng sai, xác định quyền và dữ liệu có thể đã bị truy cập, xử lý các bản sao trong log, artifact, cache, clone và fork có liên quan. Nếu cần làm sạch lịch sử Git, phối hợp với người giữ các bản sao và quét lại sau xử lý.

Xoá file khỏi HEAD không thu hồi token đã lộ và không xoá nội dung khỏi commit cũ. Pin phiên bản, hash lock và hook giúp kiểm dependency hoặc phát hiện chuỗi đáng ngờ ở những lần thay đổi tiếp theo; chúng không làm credential cũ mất hiệu lực. Bài này chỉ ghi cách ứng phó, không rotate hay thao tác với credential thật.
