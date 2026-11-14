# Kiến trúc UI và backend của Talking Head Cutroom

Baseline kiểm tra: HEAD `9b4d13f9796a78ec83f1ab13d07f3c61df46ff8e`, cùng UI creator chưa commit tại ngày 13/11/2026. Đây là ứng dụng chạy riêng trên từng máy. Gói next-sprint bổ sung ST-007, ST-008, ST-012, ST-016, TASK-01/02/04/05; không thay thế nguồn lời nói, khóa cảnh hoặc các cổng QC.

## Quyết định kiến trúc

Thứ tự triển khai: luồng nghiệp vụ và tiêu chí nhận → hợp đồng API → dịch vụ nghiệp vụ → UI → kiểm thử xuyên suốt. Với UI hiện có, đọc thao tác thực tế để xác định intent, rồi đặt kiểm tra bắt buộc ở backend. Không có quy tắc mọi công ty phải làm backend trước mọi giao diện; giao diện thử nghiệm giúp phát hiện nghiệp vụ thiếu, còn API và bất biến dữ liệu cần chốt trước khi nối luồng thật.

Giữ một backend local có các module nghiệp vụ, worker dựng và kho media/version trên D. Chưa thêm microservice, tài khoản cloud hoặc cơ sở dữ liệu phân tán. HTTP handler chỉ xác thực, giải mã và chuyển lệnh; Workspace giữ revision, khóa và một lần lưu workspace nguyên tử; creator_editor xử lý lựa chọn trong một passage; engine giữ source clock và render. Model trả đề xuất có kiểm tra, không tự duyệt master.

Frontend gửi intent và bản gốc nó đang sửa. Backend kiểm tra lại bên trong cùng khóa với thao tác ghi. Một batch lỗi revision không được lưu một nửa. Worker chỉ được dispatch sau khi receipt first-cut đã lưu. Bản xuất cũ và media gốc được giữ.

## Hợp đồng đã triển khai

| Thao tác | Endpoint | Input chính | Bất biến và lỗi |
| --- | --- | --- | --- |
| Đọc đoạn lời trong master | GET /api/creator/editor?id=&export= | Recording + exact export | Trả SHA, revision, nguồn các đoạn lời, từng span source→edit; không nhận lời suy đoán là transcript đã nghe |
| Lưu settings/batch | POST /api/update | ids, revisions, changes | CAS nguyên tử; thiếu revision 400, revision cũ 409; khóa render và style giữ nguyên |
| Sửa caption của passage | POST /api/creator/caption | id, export, sha256, revision, beat, cues[{index,text}] | Chỉ cue nằm trọn passage; giữ thời gian và cue khác; tối đa hai dòng. Cue vắt qua biên dùng advanced editor |
| Đổi hình của passage | POST /api/creator/shot | id, export, sha256, revision, beat, asset hoặc chuỗi rỗng | B-roll phải thuộc recording; style-only bị từ chối. Chia shot dài và giữ offset hai bên. Không tự thay scene đã insert/khóa; footage thiếu thời lượng trả lỗi cụ thể |
| Tạo cut | POST /api/creator/first-cut | ids, revisions, request_id, niche?, story_format? | Retry cùng ID/body trả receipt cũ kể cả sau restart. Body khác cùng ID trả 409. Commit thất bại không dispatch worker |
| Audition opening | POST /api/creator/openings | id | Receipt trả baseline_export và SHA; UI dùng chính body của baseline đó |

Các caller HTTP cũ của `/api/update` cần bổ sung revisions; replay nội bộ đã được cập nhật. Python Workspace.update vẫn nhận hai tham số cho các nghiệp vụ nội bộ đang giữ khóa. HTTP handler không cho bỏ guard.

## Xung đột và nháp

409 giữ revision mới trên server. Form advanced giữ chữ đã gõ và base revision; nháp được lưu sessionStorage, xem lại/tải JSON sau reload trong cùng tab. Đây chưa phải tự gộp ba chiều. Nháp nằm trong phiên browser local, không phải sao lưu media hoặc bảo đảm sống qua đóng browser/xóa dữ liệu. Không tự tăng base revision để gửi lại toàn bộ draft. Gộp tự động theo sceneId cần lịch sử base và kiểm tra cả delete-vs-edit; chỉ triển khai với hợp đồng và test riêng.

## Kiểm chứng

Trước sửa, một request HTTP thật gửi revision 0 cho job revision 1 vẫn được 200 và nâng revision 2. Sau sửa, test cùng loại trả 409, trạng thái giữ nguyên. Các fixture cơ học được đánh dấu nonmedia, không dùng làm bằng chứng chất lượng video.

Kiểm tra UI sử dụng master thật trong workspace metadata clone. Playback, passage seeking, lưu xung đột và nháp được quan sát qua Chrome headless. Kiểm tra thấy/nghe master ở 1×, bằng chứng demo và chấp thuận editorial vẫn là các điều kiện riêng; các test API không cấp READY.

## Phần sprint tiếp theo

- ST-007: observation riêng theo hash/range, confidence hình/âm thanh độc lập; association vào passage hiện tại.
- ST-008: capability/parameter/requirement rõ; native template khác baked excerpt.
- ST-012: chọn reference/component, preview và sửa instance theo passage; template version không đổi khi sửa episode.
- ST-016: pip_shape tương thích rectangle/circle, crop và diameter; mask thật ở export, một voice route; caption/result conflict có hành động cụ thể.
- TASK-05: đo request/message/tokenizer/model identity và stage thực; media reuse, exact result reuse, KV/prefix cache là các loại khác nhau. Counter chưa có để null.

Nguồn kiến trúc: [OpenAPI](https://spec.openapis.org/oas/v3.1.html) cung cấp ngôn ngữ hợp đồng HTTP; [RFC 9110](https://www.rfc-editor.org/info/rfc9110/) mô tả conditional requests và lost updates. Cutroom hiện dùng revision trong JSON để CAS ở tầng ứng dụng, chưa tuyên bố triển khai header If-Match.
