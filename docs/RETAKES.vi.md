# Kiểm và bỏ take lặp trong Cutroom

Trong Outputs, mở **Kiểm take lặp** trên bản xuất mới nhất của recording đã có
transcript từng từ. Hai đoạn hiển thị câu nói, mốc nguồn, mốc bỏ trong MP4 và
take sẽ giữ. Mở preview trước/sau và nghe điểm nối. Chọn xác nhận rồi bấm
**Áp dụng và xuất bản mới**. Nếu câu lặp để nhấn ý hoặc lời và timing chưa rõ,
giữ bản hiện tại hoặc chỉnh tay. Không có chế độ tự áp dụng.

Tính năng dựa trên workflow preview/apply/undo của
[MakeMyClip](https://github.com/MakeMyClip/editor). Cutroom dùng cut map trong
creator context, transcript source và queue của chính nó. Chỉ đề xuất hai câu
liền nhau có token trùng khớp, kể cả dấu tiếng Việt, số và từ phủ định. Một
đề xuất cần mốc từ có độ tin cậy, khoảng nghỉ và rìa cắt an toàn. Các đoạn
đụng cutaway, motion, SFX, mở đầu có proof, bìa hoặc automation được giữ lại.
Việc trùng chữ không xác định được cách nói hay ý định nhấn mạnh.

## CLI và khôi phục

Dùng `app/cli.py retakes --workspace WORKSPACE --request FILE --json`. Nạp
`talking-head-qc/tools/use_d_storage.ps1` trước khi chạy trên máy này. Tệp JSON
`list` nhận `operation`, `id` (recording) và `export`. `preview` nhận thêm
`revision`, `sha256` và `choice` từ kết quả list, trả ID preview. `apply`
nhận cùng thông tin, `preview`, `confirmed: true` và `request_id` ổn định.
UI lưu và xếp render. Với batch, CLI có thể `resume` run để xuất revision
đã lưu. CLI dùng API loopback khi workspace đang mở trong UI.

Sau khi áp dụng, mở bản hiện tại và chọn **Khôi phục và xuất bản mới**. `undo`
dùng `id`, `export`, `sha256`, `revision`, `confirmed: true` và request ID
riêng. Lệnh chỉ khôi phục retake gần nhất nếu revision chưa có thay đổi khác.
Undo cũng có thể dùng khi render lỗi và bản cũ vẫn là bản mới nhất phát được.
Lịch sử giữ export cũ. Dùng request ID cũ để retry cùng thao tác.

## Nghiệm thu ngày 21/11/2026

Harness local dùng câu tiếng Anh từ TTS tổng hợp, màn hình demo mô phỏng và
mốc từ gán trong fixture. Browser mở Outputs, tạo hai preview, xác nhận và
xuất revision 2. Public CLI đọc đúng revision, retry không sửa thêm, request
cũ với ID mới trả 409 và undo sinh revision 3.

| Revision | Độ dài | SHA-256 | QC |
|---|---:|---|---|
| 1 | 11,0 s | `1303545e4cd717f5366964d92115fe809ffaf227576f9f83498ebbb52663b251` | NEEDS_REVIEW |
| 2 | 8,6 s | `6489b09aa579c40e8fd38f4ddfe3c938a6a5abc7de39ee6c357cb852c143b559` | NEEDS_REVIEW |
| 3 | 11,0 s | `1303545e4cd717f5366964d92115fe809ffaf227576f9f83498ebbb52663b251` | NEEDS_REVIEW |

Ba MP4 decode đầy đủ. Cắt 1,20–3,60 s bỏ một caption lặp và giữ câu còn lại.
Demo bắt đầu 7,70 → 5,30 s. Click bắt đầu 8,90 → 6,50 s với mốc nguồn và gain
giữ nguyên. UI mất 5,70 s từ nút Apply đến MP4 mới trên fixture. Tải ZIP cũ
sau đó tiếp tục lấy đúng MP4. Đổi riêng nội dung caption đăng bài giữ hash
MP4 và ảnh. Kiểm thuật toán có ca số, phủ định, dấu, lặp để nhấn, Việt–Anh,
câu dang dở, thiếu mốc, demo và cue được bảo vệ.

Số đo trên fixture không thay cho số lần creator sửa tay, đo mất đầu/cuối
tiếng trên recording thật, hay một buổi nghe toàn bộ đúng master ở 1×. Chưa
có dữ liệu xác định cần đổi aligner/VAD hoặc huấn luyện model.
