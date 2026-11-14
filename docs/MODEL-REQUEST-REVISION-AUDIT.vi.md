# Audit request sửa cảnh — 14/11/2026

Phạm vi: `cache_probe.contexts`, `motion_learning.messages`, `model_context`,
`motion_policy.infer`, worker Qwen2.5-1.5B-Instruct pinned revision và validator
scene v1. Editing agent/Codex không phải model planner này. Không đọc credential,
sealed final cohort hoặc thêm future corrections vào RAG.

## Phát hiện có bằng chứng

C4 runtime trước tại commit 08a79bb nói “keep the label visible longer”, nhưng
fixture đổi `texts` từ `Recordly` thành `Recordly rõ hơn` trong khi `frames=90`
và quote giữ nguyên. Nó đã gộp đổi chữ với ý định sửa hold, nên không đại diện
cho một yêu cầu chỉ đổi timing. Raw output bị từ chối vì chữ ngoài inventory.
Sự từ chối đó vẫn đúng với input đã gửi; kết quả lỗi cũ được giữ, không xóa hoặc
chấm lại thành pass. Chưa thể quy lỗi riêng cho khả năng kéo hold.

## Thay đổi nhỏ nhất

Giữ SYSTEMS[9], checkpoint và validator. Chỉ sửa fixture tạo request:

- R1 timing-only: texts, quote và spoken anchors giữ nguyên; scene khai báo dài
  hơn 90→120 frame và intent yêu cầu giữ chính nhãn đó. Đây là synthetic scene,
  không phải tự kéo dài nguồn nói của khách. C4 trong sáu cache probe dùng R1.
- R2 label-only: quote, anchors và duration giữ nguyên; texts và intent khai báo
  rõ nhãn mới. Chữ hiển thị có thể khác nguyên câu nói, nhưng không tự đổi voice.

Hai regression so chính tập field khác nhau và xác nhận input gốc không bị mutate.
Sáu test request-observability đạt. Đây là test hợp đồng fixture, chưa là kết quả
inference mới hoặc bằng chứng model đã sửa được cảnh.

## Lượt train liên quan

Protocol v009 thử một biến: thêm 8 fixture gốc train-only về ranh giới quote /
display inventory. Bốn intro và bốn cảnh giải thích; tĩnh hoặc slide nhẹ theo
project do agent tự tạo. Typography nền trắng theo dòng dựa trên observation
train-source hash a10c694f… tại 00:01.000–00:01.033; không suy entrance/SFX từ frame
đó. Tất cả fixture vẫn thuộc một group house-motion-fixtures, không phải tám
creator độc lập hay nhãn gold. Không dùng exact C4/5-repo corrections làm train.

Validation/regression files giữ nguyên hash; train-only RAG có 56 mẫu. Preflight
3066/3072 token, không truncate. Một lượt Kaggle private, 64 optimizer steps;
trạng thái hoàn thành/weights và kết quả mới phải đọc từ receipt thực, chưa suy
từ upload/push. So base/tuned dùng cùng RAG và sáu input development đã freeze.
Các partition từng được xem vẫn là development/regression, không thành unseen.

Không thay grader để tăng điểm, không gọi compiler repair là raw success và
không promote model từ loss/schema. Tập B mới, full-video blind reviews và human
repair minutes còn là điều kiện riêng.

## Recordly: sửa guard để phục vụ demo thật

Guard 0.1.2 dừng mọi title change sẽ cản GitHub→Releases đúng yêu cầu. Source
0.1.3 thêm `allowed_titles`: tối đa 5 tên chính xác, có tên bắt đầu; tên bổ sung
phải được `recordly_sources` quan sát trước trong 5 phút trên đúng cùng window ID.
Danh sách frozen khi start; không wildcard hoặc tự mở rộng lúc đang quay.
Tên lạ/mất cửa sổ/lỗi kiểm nguồn vẫn stop và quarantine. 23 test đạt, gồm planned
navigation, title lạ, observation cũ/sai window và retry. Native recapture chưa chạy;
polling ID/title không chứng minh pixel isolation. Installed 0.1.1 được giữ.
