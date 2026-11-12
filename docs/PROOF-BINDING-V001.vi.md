# Gắn footage với yêu cầu demo của từng master

Source đang chạy: **0.14.0-dev7**, experimental. Lượt này sửa tính đúng của
benchmark và hồ sơ nguồn; checkpoint Kaggle v004 được giữ nguyên. Không có lượt
train mới hoặc kết luận style tốt hơn.

## Vấn đề và thay đổi

Benchmark trước đọc tất cả placeholder của job trong workspace hiện tại. Một
master đã đóng băng vì thế có thể nhận thêm yêu cầu quay của các scene/version
được tạo sau nó. Ba master v004 mỗi bản có20 thông báo lặp từ lịch sử, dù đã có
cutaway thủ công. Việc suy repo chỉ từ tên file còn có thể gắn sai nguồn.

- Cutaway có hai ô tùy chọn: **Demo subject** và **What must be visible**.
  Label có thể là Recordly hoặc một nghiệp vụ khác như Xuất hóa đơn. Nó được
  giữ trong settings, plan và receipt, cùng source SHA và khoảng nguồn.
- Tên file không tự gắn proof với repo. Subject khớp chính xác sau chuẩn hóa
  Unicode/case; một repo không thay proof cho repo khác.
- Native Recordly scene mang theo subject và các source anchor đã có. Không
  sinh thêm contact từ lời nói; marker/SFX giữ mốc của context gốc.
- Capture requirements lấy từ proposal hiện tại đúng script hash. Benchmark
  đọc snapshot của từng export; các placeholder lịch sử không sửa master cũ.
- Illustration/reference excerpt có thể làm cutaway nhưng bị chặn khi gắn
  thành proof thao tác thật. Cách lưu template/bind lại từng tập vẫn giữ nguyên.

| Trạng thái | Ý nghĩa và bước tiếp |
|---|---|
| UNASSIGNED | Chưa có source được gắn rõ cho yêu cầu đó; xem nguồn hiện có rồi gán hoặc quay đúng phần thiếu |
| PROVIDED_UNVERIFIED | Có source được gán và hash/range; xem thực tế để kiểm claim, thời gian đọc, chữ và tiếng |
| LEGACY_UNVERIFIED | Master cũ chỉ có hồ sơ suy từ tên file; giữ mô tả lịch sử và duyệt lại, chưa nâng thành explicit assignment |

Cả ba trạng thái đều không tự xác nhận target/contact/result hay cấp READY.
Một giá được nhìn thấy không chứng minh model đã chạy; một badge đẹp không
chứng minh phần mềm đã xuất file. Quan sát sự kiện và review master vẫn riêng.

## Kết quả thực tế

**276 test đạt:**184 app,53 QC,39 reference lab. Node syntax và Git whitespace
checks đạt. Test có trường hợp workspace đổi sau export, tên file gây hiểu nhầm,
source của repo khác, illustration giả proof, yêu cầu còn thiếu, và source được
gán nhưng chưa có contact.

Clip smoke dùng video/audio thật của đoạn Recordly, source selected-camera
00:44,500–00:49,500. Giữ các SRT cue nguyên vẹn nằm trong cửa sổ này; không xem
đó là một câu độc lập đã duyệt cắt/nghe. Export:

- ID `7aa2add6f7fb4630bc7a85ef55d6793b`.
- SHA `f2e965b82b62f3caa17f0406b97ddffe4eccd718d725f24acaba723aa0c12ed8`.
- 5s,150 decoded frames,1080×1920/30, encoder thực `h264_nvenc`.
- −16,02LUFS,−2,60dBTP; không đặt SFX trong test binding này.
- Followup `PROVIDED_UNVERIFIED`, source range0–5s; observed anchors rỗng được
  giữ nguyên, không giả mốc click. Dependency hash khớp source module hiện tại.
- **NEEDS_REVIEW**: frame360px đã kiểm thấy tiêu đề release; chưa xem/nghe1×.

[MP4 smoke](D:/.codex/workspaces/talking-head-support/proof-binding-smoke-002/workspace/exports/7aa2add6f7fb4630bc7a85ef55d6793b/edit.mp4),
[project chỉnh được](D:/.codex/workspaces/talking-head-support/proof-binding-smoke-002/workspace/exports/7aa2add6f7fb4630bc7a85ef55d6793b/project.json),
[QC](D:/.codex/workspaces/talking-head-support/proof-binding-smoke-002/workspace/exports/7aa2add6f7fb4630bc7a85ef55d6793b/qc.md).

Benchmark mới dùng lại đúng bytes của ba master v004: cả ba full decode đạt,
playback loudness khớp, controls khớp.20 thông báo lịch sử/bản được thay bằng
5 nhóm `LEGACY_UNVERIFIED`, mỗi nhóm có2–3 source từ profile đã đóng băng.
Cả5 vẫn cần duyệt nội dung. Không tính việc sửa thông báo thành giảm công sửa
video hoặc tăng chất lượng model.

[Bài so mù đã sửa hồ sơ](http://127.0.0.1:59507/benchmarks/b37453020e2d4896b6016be307339ec9/index.html).
0 full human review; model improvement/first-pass/repair time vẫn chưa có số đo.
Kết quả API nằm ở `output/reference-training/proof-binding-v001/actual-results.json`.
Benchmark cũ, các master, checkpoint và mọi clip smoke trước được giữ nguyên.

## Phần còn chờ

Các kiểm thử mới chạy qua backend/API và FFmpeg. Hai ô UI đã qua syntax check;
chưa hoàn tất kiểm tương tác browser của lượt này. Recordly đã mở, chưa Record.
Computer Use dừng khi helper không xác định được URL Chrome đủ chắc chắn để
kiểm tra quyền thao tác. Sau đó không phát thêm input desktop.

Đã đọc [Computer Use SKILL.md](D:/.codex/plugins/cache/openai-bundled/computer-use/26.1029.61003/skills/computer-use/SKILL.md).
Guidance được skill yêu cầu có quy tắc “stop issuing app input” khi phiên kết
thúc. Đây là giới hạn của lượt điều khiển hiện tại; không phải người dùng thu
hồi quyền quay. Trang preview thật đã chuẩn bị ở
[localhost59509](http://127.0.0.1:59509/); đang chờ người dùng mở trong Chrome.
Chưa quay thêm FFmpeg proof, chưa gán đủ5 repo qua UI và chưa xuất master mới
thay v004. Chưa đưa clip mới vào thư viện usable.
Điểm quay tiếp theo:00:34,733–00:37,333 đang dùng GitHub cutaway; SRT ở
00:34,220–00:36,740 có câu “bảo là chèn màn hình vào đúng câu này nhé.” Trang
preview mở MP4 thật từ00:32 để quay khoảnh khắc người dẫn chuyển sang màn hình.
Đây là đối chiếu SRT/ảnh nguồn, chưa phải chứng nhận đã nghe câu đó.

Media và các cache lớn của Recordly vẫn là junction tới D. Lệnh định chuyển
phần cấu hình vật lý còn lại trên C đã bị kiểm duyệt tự động từ chối với thông
báo `blocked by policy`, trước khi process chạy. Không có dữ liệu bị xóa bởi
lệnh đó. Toàn bộ artifact do lượt kiểm thử này tạo được lưu trên D.

## Lệnh kiểm thử

Chạy từ checkout root, dùng runtime đã cấu hình trên máy:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$kitModelPython='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-animation-model\Scripts\python.exe'
$env:PYTHONPATH='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-structured-decoding-0113'
& $kitModelPython -m unittest discover -s app -p 'test_*.py'
python -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
python -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py'
node --check app/ui/app.js
```
