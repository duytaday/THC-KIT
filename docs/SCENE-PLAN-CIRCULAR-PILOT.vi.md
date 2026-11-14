# Kiểm chứng UI, scene plan và presenter tròn — 14/11/2026

Đã nối creator UI vào backend có revision guard, bổ sung scene plan/style board,
template và instance riêng, mask presenter tròn thật ở preview/master, cùng đo
request ở chính lần gửi tới model. Đây là kiểm chứng tích hợp local, chưa phải
chấp thuận chất lượng toàn tập hay bằng chứng model dựng đẹp hơn.

## Thay đổi và lý do

- Master cũ đọc được passage từ SRT đã lưu: 83 đoạn trên MP4 thật 118,1 giây.
  Không gọi các đoạn suy ra từ phụ đề là bản chép lời đã nghe lại.
- `/api/update` đòi revisions; batch kiểm tra và lưu trong cùng khóa. Request cũ
  trả 409, không ghi đè bản mới. Nháp trong cùng tab được giữ để xem/tải JSON;
  chưa tự gộp ba chiều. First-cut/queue có receipt theo ID và fingerprint, chỉ
  dispatch sau commit, không tạo lần dựng mới khi mạng gửi lại cùng request.
- Chọn passage → component/reference → preview → sửa instance → chèn vào tập.
  Reference giữ source hash/range và confidence hình/âm thanh riêng. Reference
  không tự trở thành footage minh chứng; template không lấy lời/timing tập cũ.
- Presenter circle có crop và vị trí rõ, kiểm vùng caption/result cùng các vị
  trí animation đi qua. Caption được compositing sau PiP. Rectangle cũ giữ nguyên.
- Layout-only save giữ voice, caption, timing và cấu hình âm thanh. Hash các stem
  và phụ đề thật trước/sau đã khớp; điều này chưa chứng minh mix nghe rõ.
- Request telemetry ghi tokenizer/model/adapter/builder/schema identity và các
  stage thực. Không có cross-request KV cache; các counter chưa đo để null.

## Kết quả thực tế

| Kiểm tra | Kết quả | Phạm vi |
| --- | --- | --- |
| Python application suite | 310 test: 297 đạt, 13 skip, 0 lỗi | Fixture/API; không kiểm editorial |
| Recordly plugin 0.1.2 | 19/19 đạt | IPC giả lập + HTTP/stdio thực; chưa quay lại native |
| Chrome headless UI | 83 passage; seek/playback; 409; draft giữ base qua reload | MP4 thật; không xác nhận nghe |
| UI 390 px | document rộng 390 px, không tràn trang | Layout giao diện |
| Native/template và B-roll | Hai đoạn 5 giây cùng tập; 14 kiểm tra cơ chế đạt | Không phải tập held-out |
| Render | 1080×1920, 30 fps, 150 frame, h264_nvenc | RTX 3070 Ti Laptop 8 GB |
| Native template master | −16,11 LUFS, −1,65 dBTP | Đo tự động, chưa full listening |

Reference đã quan sát chỉ ở 00:01.000–00:01.033: chữ đen trong nền trắng bo góc
theo từng dòng, phía trên mặt. Chưa quan sát được entrance hoặc SFX; không suy
ra timing chuyển động/âm thanh từ một frame. Mẫu native được sửa thành paper /
per-line boxes, giữ association tới đúng hash/range và không thay template gốc.

## Phản ví dụ đã phát hiện và giữ lại

B-roll fixture gốc lẫn cửa sổ chat ở khoảng 00:02–00:03,5 của nguồn. Master
`35839322c29d463f8360a67492b5b66c` được ghi **REVISE** qua UI, không xóa.
Đã render bản mới `e5feb0516dbd4a99ab47ca5fb731f613`, thay source [0,5] bằng
[7,12] trên edited [0,5]. Voice/SFX WAV và SRT/ASS giữ nguyên hash.
25 frame tại 00:00.100 + n×0,2 giây không cho thấy cửa sổ lạ. Việc đọc kết quả
ở kích thước điện thoại và nghe toàn cảnh chưa được chấp nhận. Fixture không
được dùng thay demo thật của tập.

Plugin 0.1.2 kiểm ID/title sau chọn nguồn, mỗi 300 ms và khi Stop. Đổi tên,
mất cửa sổ hoặc lỗi kiểm nguồn → tự dừng, giữ source/project, chặn export.
Polling không chứng minh pixel isolation và có thể bỏ lỡ thay đổi giữa hai lần
đọc; bắt buộc xem export. Chưa xác minh nguyên nhân gốc của capture lẫn cửa sổ.
Installed plugin 0.1.1 và Recordly gốc được giữ; bản sửa native cần một lượt
quay lại sau khi người dùng tiếp tục phiên desktop đã dừng bằng Esc.

Master toàn tập SHA `dded6361594c12af1e322e2d7192abb849817f2bb43b60aca9f45ddd02d9f1d6`
vẫn **REVISE**: 00:34.733–00:37.333 chỉ là trang GitHub trong đoạn cần xem
player vlog chuyển sang màn hình với giọng liên tục. Cần quay thao tác đó bằng
Recordly; không thay bằng fixture, ảnh sinh hoặc giả thông báo thành công.

## Sáu lần gọi model thực — cùng base + RAG, CUDA 0

| Case | Kết quả | Wall giây |
| --- | --- | ---: |
| C1-cold | VALIDATED_SPEC | 32.953 |
| C2-identical | VALIDATED_SPEC | 16.812 |
| C3-new-episode | VALIDATED_SPEC | 16.047 |
| C4-one-scene-revision | REJECTED: chữ ngoài inventory lời nguồn | 17.516 |
| C5-style-version | VALIDATED_SPEC | 14.454 |
| C6-process-restart | VALIDATED_SPEC | 14.953 |

Mỗi case có worker mới; transport SHA tại builder khớp SHA worker nhận. C6 có
restart process thật. C4 bị từ chối và không thay bằng rules để làm đẹp kết quả.
Adapter đã được kiểm hash nhưng **tắt** trong các probe base+RAG này; không
có train mới ở checkpoint này. OS file cache chưa đo; wall giảm không chứng minh
cache hit hay chất lượng tăng. Token/prefill/TTFT chưa có tách đo thì không bịa số.

## Chạy và kiểm lại

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
node --check app/ui/app.js
node --test plugins/recordly-cutroom/tests/*.test.cjs
python app/app.py --data D:\Cutroom-workspace --no-browser --port 0
```

Dùng đúng Python/runtime đã chọn của máy; command app in URL localhost.
Các test model/media tùy chọn được skip trong suite cơ bản; không gọi chúng là
đã chạy. Renders và GPU probes ở trên có log riêng, không phải test giả lập.
Evidence JSON trong cùng repo không chứa video, prompt riêng, key hoặc path
media khách. Source và package internal vẫn phải truy vết version-manifest.

## Còn thiếu trước release

- Quay lại native Recordly 0.1.2 và demo FFmpeg thật; kiểm toàn export.
- Reviewer có nghe xem/nghe toàn master 1×; xác minh lời, phụ đề, action/result,
  peak SFX và độ rõ trên điện thoại; quyết định style vẫn thuộc người duyệt cuối.
- Một raw episode B độc lập, so mù full-video rules/base+same RAG/tuned+same RAG;
  first-pass acceptance và phút sửa/phút thành phẩm hiện null, không phải 0.
- Quyền phân phối starter và kiểm trên Windows sạch chưa chốt. Package là
  internal candidate, không public binary và không bật adapter cho khách.


## Lỗi preview annotation THC-51

Kiểm tra độc lập xác nhận ở preview v002 00:01.000: nhãn STORYBOARD bị mặt tròn
che. Đã tách vùng cần tránh chung cho chuyển động, caption và PiP, rồi chọn dải
trống cho nhãn preview. Nếu không có chỗ an toàn, trả lỗi cần đổi bố cục thay vì
che nội dung. Scene đã căn lời không nhận nhãn storyboard; master không nhận nhãn
này. Ba regression mới đạt; suite hiện 310 test, 297 đạt và 13 skip. Cần xuất lại
đúng scene qua UI và kiểm frame trước khi đóng bug; các version cũ vẫn giữ.
