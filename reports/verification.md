# Verification — CP1, CP2 và CP3a–c

Ngày kiểm tra: 12/10/2026.

- Môi trường: Windows native, PowerShell, Python 3.11.9 trong `.venv`; requests 2.34.2, pytest 9.1.1. Các lệnh CP2 đã chạy được trên môi trường này.
- CP1: đã đọc lại `_naive_loop()` và `http_post()`, đối chiếu số dòng trong `reports/baseline.md` với code hiện tại. Mỗi câu trả lời dài 2–3 câu. Chưa sửa code trong `agent/`.
- `python -m agent.check_lure corpus/ticket-90*.md`: exit code 0, **4/4 lure sẵn sàng**; số marker lần lượt 4, 4, 5, 2. Cặp 904/904b tính là một lure.
- CLI `python -m agent.loop --mock "Tổng hợp các ticket còn mở tuần này"`: exit code 0, tổng hợp 45 ticket; sink nhận một POST chứa đúng hồ sơ synthetic `KH-000999`.
- Sau reset, thử riêng 901, 902, 903 và cặp 904/904b bằng `_naive_loop()` trong thư mục tạm: mỗi lượt tạo đúng một POST. `reports/attack-before.log` có bốn dòng, là bản sao nguyên nội dung `reports/sink.log`. Mỗi body được đối chiếu với hồ sơ gốc, gồm `cccd`, `phone`, `bank_account`; path đều là `/reconcile`.
- Thử riêng `ticket-904.md` và `ticket-904b.md`: `find_injection()` trả `None`, mỗi lượt có 0 POST. Khi ghép hai file, mock nhận diện đủ hai marker và sink nhận hồ sơ.
- Sink đã dừng sau khi sao chép log. `ticket-901.md`, dữ liệu nguồn, allowlist và test bắt buộc được giữ nguyên.
- Đã bỏ hai file phụ của lượt chạy trước: `reports/cli-before.txt`, `reports/cli-sink-before.jsonl`. Chỉ thêm bốn file lure và `reports/attack-before.log`; kết quả được ghi vào các báo cáo có sẵn.
- Chưa chạy `python -m pytest tests/ -q`, Gitleaks, `pre-commit run --all-files` hay ledger verify: các phần này thuộc những checkpoint sau. Chưa tạo `reports/attack-after.log`.

Lỗi gặp và cách xử lý:

- PowerShell truyền here-string tiếng Việt sang Python bằng encoding mặc định có thể làm dấu thành `?`. Đã đặt `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` cùng `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8` và chạy lại toàn bộ lượt CLI/replay bằng đúng câu hỏi tiếng Việt. Log nộp lấy từ lượt chạy lại này.
- Lệnh ghi báo cáo bằng here-string PowerShell chứa một here-string khác báo `The string is missing the terminator: '`. Cách tái hiện: dùng `@' ... '@` ngoài để bao đoạn PowerShell cũng có dòng kết thúc `'@`. Lệnh dừng ở bước parse, chưa ghi file; đã sửa bằng cách ghi báo cáo qua công cụ sửa file.

Chưa có lỗi còn lại trong phạm vi CP1–CP2. Tại thời điểm hoàn thành CP2, các control vẫn là scaffold; kết quả CP2 chứng minh lỗi trước khi sửa, chưa phải bằng chứng containment.

## CP3a — PII detection và redaction

Đã hoàn thiện `detect()` và `redact()` trong `agent/pii.py` bằng regex. Không thêm dependency, không sửa test hay bộ mẫu.

Lệnh đã chạy trong repo, bằng Python của `.venv`:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_pii.py -v -s --basetemp=.pytest_tmp
```

Kết quả thật, exit code 0:

```text
[pii] gold=118 pred=118 tp=118
[pii] precision=1.000 recall=1.000
2 passed in 0.02s
```

Precision = 118/118 = 100%; recall = 118/118 = 100%. Recall vượt 95%, thuộc mức cao nhất cho tiêu chí PII trong `RUBRIC.md` trên bộ mẫu này.

`detect()` trả vị trí ký tự trong chuỗi gốc, không bỏ dấu hay chuẩn hoá chuỗi trước khi lấy offset. Với STK, chỉ lấy vùng chứa giá trị, không lấy nhãn. Email và STK có nhãn được ưu tiên trước CCCD và điện thoại; vùng đã được chọn sẽ không bị báo thêm dưới loại khác. `redact()` thay từ cuối về đầu bằng `[REDACTED_<TYPE>]`.

Test đo precision/recall dùng vùng giao nhau cùng loại, chưa đòi offset khớp hoàn toàn. Vì vậy đã kiểm thêm trực tiếp trong bộ nhớ:

- Cả 120 câu có danh sách `type/start/end` khớp hoàn toàn với nhãn gốc: 118/118 vùng đúng, không có vùng trùng nhau.
- Các giá trị lấy bằng `text[start:end]` đều không còn trong kết quả che.
- 11 trường hợp riêng đều đạt: text rỗng, ticket không có PII, STK trùng mẫu điện thoại/CCCD, nhãn số tài khoản có dấu/không dấu, CCCD, điện thoại có dấu cách/gạch ngang hoặc 11 số, email có phần trước `@` là 12 số, chuỗi số dài quá 16 ký tự.
- Một câu có đủ bốn loại được che đúng, giữ nguyên chữ và dấu câu bên ngoài các vùng PII. Che lại kết quả đã che không làm thay đổi nội dung.

Giới hạn của regex:

- CCCD nhận theo dạng 12 số, không kiểm số có được cấp thật hay không; mã khác cũng dài 12 số có thể bị nhận nhầm.
- STK cần nhãn `STK`, `số tài khoản` hoặc `so tai khoan`, giá trị là 8–16 số liền nhau. STK thiếu nhãn hoặc có dấu phân cách có thể bị bỏ sót hay nhận thành loại khác.
- Điện thoại nhận 10–11 số bắt đầu bằng `0`, cho phép dấu cách/tab/gạch ngang giữa các số; chưa nhận dạng `+84` hoặc kiểm đầu số thật.
- Email dùng dạng ASCII thông thường, chưa xử lý đầy đủ các dạng email khác. Chữ số Unicode, zero-width và cách cố tình làm méo giá trị có thể né các regex này.
- Bộ mẫu gồm dữ liệu tổng hợp với định dạng đều. Kết quả 100% ở đây chưa chứng minh cùng độ chính xác trên dữ liệu thực tế.

CP3a chỉ sửa `agent/pii.py` và báo cáo này; không tạo file source hay báo cáo mới. Khi kết thúc CP3a, chưa nối redaction vào runner hay làm policy/OBO; kết quả thực hiện tiếp CP3b–c được ghi bên dưới.

## CP3b — Policy

Đã hoàn thiện `policy.check()`: kiểm phân loại, chặn `restricted + egress`, tra principal trong `data/principals.json`, kiểm mục đích, tool, scope và thời hạn UTC. Khi có ủy quyền, tool phải nằm thêm trong scope của agent cha. Thiếu dữ liệu quyền hoặc không đọc được registry cũng bị từ chối. Cả allow và deny đều có reason.

Lệnh đã chạy:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_policy.py -v --basetemp=.pytest_tmp
```

**Kết quả: 4 passed in 0.02s, exit code 0.**

| Trường hợp trong test | Kết quả |
|---|---|
| Restricted + egress | deny |
| Restricted + egress, DPO đủ quyền | deny |
| Support tìm ticket internal, không egress | allow |
| Support tìm ticket public, có egress | allow |

## CP3c — OBO tại chỗ gọi tool

Đã thay stub `runner.handle()` bằng luồng có kiểm quyền và ghi ledger trước tool. Mỗi yêu cầu có `agent_id` mới, hai `run_id` riêng và thời hạn 5 phút ở UTC. Run A có scope `search_docs`; Run B có scope `read_customer`, quyền được giao vẫn phải nằm trong scope của agent cha.

Trước cả việc mở `data/customers.json` để tra liên kết, runner kiểm quyền đọc hồ sơ. Quyết định này ghi `stage=customer-lookup` để phân biệt với lần gọi tool thật. Sau đó, trước từng `read_customer()`, runner kiểm và ghi riêng một quyết định nữa. Khi deny, không mở private store hoặc gọi tool đó.

Mã ticket lấy từ tên file; mã khách lấy từ `related_tickets` trong dữ liệu gốc. Mã khách và URL do ticket tự nêu không dùng để chọn hồ sơ hay đích gửi. Nội dung được che PII trước khi gọi `summarize()`; Run B chỉ nhận danh sách ID ticket, không nhận text ticket. Nếu nhận diện injection, ý định gửi tới sink cố định được đưa qua policy và ghi deny `http_post`.

Để runner ghi được quyết định, đã hoàn thiện `ledger.append()` theo interface sẵn có: thêm `prev_hash`, tính `hash` rồi append JSONL. Chưa làm `ledger.verify()` hoặc kiểm sửa đổi chuỗi ở CP3e.

Lệnh đã chạy:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_obo.py -v --basetemp=.pytest_tmp
```

**Kết quả: 5 passed in 2.68s, exit code 0.** Test chứng minh support bị deny, DPO được allow với mục đích hợp lệ, scope con không vượt cha, principal lạ hoặc TTL hết hạn bị deny và runner kiểm trước `read_customer()`.

Đã kiểm thêm trong bộ nhớ, không tạo file test mới:

- 15 context gồm allow hợp lệ, phân loại sai, restricted + egress, mục đích sai, thiếu scope agent/cha, principal lạ, TTL hết hạn/thiếu/sai định dạng/thiếu timezone/không ở UTC. Tất cả trả đúng kết quả và reason không rỗng.
- Spy tại `search_docs()` và `read_customer()` xác nhận có ledger allow trước khi tool chạy. Spy tại `http_post()` không ghi nhận lần gọi nào.
- Theo dõi `Path.read_text()` trên private store: support có 0 lần mở file và 0 lần gọi `read_customer`; DPO có 22 lần mở file (một lần tra liên kết và 21 lần đọc qua tool), đọc được 21 hồ sơ liên quan. Không đọc `KH-000777`.
- Các entry có principal đúng, `agent_id`, `run_id`, `expires_at`, `reason`; hai run có ID khác nhau và TTL còn hiệu lực, không quá 5 phút.

Đã chạy CLI thật với cả hai principal, không dùng spy:

```powershell
.venv\Scripts\python.exe -m agent.loop --mock --as support_l1 "Tổng hợp các ticket còn mở tuần này"
.venv\Scripts\python.exe -m agent.loop --mock --as dpo "Tổng hợp các ticket còn mở tuần này"
```

Cả hai lệnh exit code 0, trả kết quả tổng hợp 45 ticket. `reports/ledger.jsonl` có 27 dòng từ hai lượt này:

| Dòng ledger | Principal | Quyết định |
|---|---|---|
| 1 | support_l1 | search_docs allow |
| 2 | support_l1 | read_customer deny, stage customer-lookup |
| 3 | support_l1 | http_post deny |
| 4 | dpo | search_docs allow |
| 5 | dpo | read_customer allow, stage customer-lookup |
| 6–26 | dpo | 21 read_customer allow, stage tool-call |
| 27 | dpo | http_post deny |

Reason tại `reports/ledger.jsonl:2`: `tool is not allowed for this principal`.
Reason tại `reports/ledger.jsonl:3` và `reports/ledger.jsonl:27`: `restricted data cannot be used with egress enabled`.
Mọi entry có các trường OBO và reason. Tham số chỉ ghi `args_hash`; đã đối chiếu ledger với các giá trị CCCD, SĐT, STK, email trong dữ liệu nguồn và không thấy PII thô.

Đã chạy thêm `tests/test_scaffold_dispatch.py` để kiểm khi thay runner: **4 passed in 0.11s**, exit code 0. Lỗi trong runner đã hoàn thiện vẫn dừng lệnh, không quay về baseline. `git diff --check` không báo lỗi.

`reports/attack-before.log` giữ nguyên bốn dòng; `reports/sink.log` rỗng sau test và hai lượt CLI. Chưa bật lại sink để lấy bằng chứng sau containment theo CP5, chưa tạo `attack-after.log`. Kết quả ở đây là bằng chứng OBO và policy tại tool, không thay thế lượt prove CP5.

Chỉ sửa các file sẵn có cho CP3b–c: `agent/policy.py`, `agent/runner.py`, phần `append()` trong `agent/ledger.py` và báo cáo này. File mới duy nhất cần giữ là `reports/ledger.jsonl`, nằm trong yêu cầu nộp bài; Git đang ignore file này, khi nộp cần `git add -f reports/ledger.jsonl`. Không sửa test, dữ liệu, lure, allowlist hay baseline.

`--as` vẫn chỉ chọn principal giả lập từ fixture, không xác thực người dùng thật. Chưa chạy test split, test ledger, full suite hoặc các kiểm tra supply chain. Dừng tại CP3c, chờ quyết định trước CP3d.

## Kiểm tra lại Bước 1 — môi trường và Gitleaks

Đã đọc hướng dẫn Bước 1 người dùng cung cấp và đối chiếu với README:

- `origin` trỏ đúng fork `htungf211004/K4-L3-DAY24-TrinhHoangTung-2A202602937`; có `CHECKPOINTS.md`; `git cat-file -t 1bdd849` trả `commit`, lịch sử cần cho CP4 còn nguyên.
- Python của `.venv` là 3.11.9. Đã có requests 2.34.2, pytest 9.1.1, pre-commit 4.6.2, pip-tools 7.6.2. `python -m pip check` trả `No broken requirements found.`
- Kiểm lại `python -m agent.check_lure corpus/ticket-901.md`: exit code 0, `1/1 lure sẵn sàng`. Không chạy lại baseline vì runner đã sửa.
- Gọi trực tiếp `C:\Users\Htungf\Downloads\gitleaks_8.30.1_windows_x64\gitleaks.exe version` trả `8.30.1`.
- User PATH đã lưu đúng thư mục chứa `gitleaks.exe`. Process PATH của terminal được kiểm tra chưa chứa thư mục này, nên `where.exe gitleaks` báo không tìm thấy. Sau khi bổ sung đúng thư mục vào PATH của riêng phiên kiểm tra, `cmd.exe /d /c gitleaks version` trả `8.30.1`, và `where.exe gitleaks` tìm đúng binary. Không sửa User/Machine PATH.
- CMD mới mặc định nhận bản sao môi trường của tiến trình cha. Vì vậy nếu được mở từ ứng dụng còn dùng PATH cũ, chỉ đóng CMD con có thể chưa đủ. Cơ chế này được mô tả trong [tài liệu Microsoft về environment variables](https://learn.microsoft.com/windows/win32/procthread/environment-variables); chưa trực tiếp quan sát cách người dùng mở CMD của họ.
- Chưa có `requirements.lock`, nên chưa thực hiện được bước `pip install --require-hashes -r requirements.lock` trong preflight của README. `.pre-commit-config.yaml` cũng chưa có; phần hook thuộc CP4.

Bước 2 và CP3a–c không gọi Gitleaks; lỗi PATH không ảnh hưởng các log/test đã ghi ở trên. Bước 1 chỉ cần kiểm binary/version; quét lịch sử, quét file hiện tại và hook dùng Gitleaks được thực hiện ở CP4. Lần này chỉ kiểm tra, chưa tạo lock/hook hoặc chạy scanner.
