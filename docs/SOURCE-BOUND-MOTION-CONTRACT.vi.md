# Planner ràng buộc theo nguồn — contract v1

15/11/2026 · source 0.14.0-dev23. V009 train thật vẫn bị từ chối promote:
chữ bị đổi/bỏ sót và đồng hồ entrance bị nhầm với source clock. Không chữa
bằng cách sửa output model rồi báo là model tự làm đúng.

Prompt 10 thử nghiệm chỉ chọn quyết định dựng: bố cục, component, khung chữ,
font, theme, per-line box, entrance, các pose trung gian, rotation, hold,
thay trạng thái và cue. Chữ dùng ref t0/t1; mốc dùng a0/a1 từ input hiện tại.
Compiler bind chữ, source ID/clock, ROI marker và loại evidence. Không cho model
tự khai đã nghe, provenance hay proof thành công. Không thay quyết định lỗi
bằng rules. Native validator vẫn kiểm từng frame, vùng mặt/caption và hold.

`required_texts` chỉ là nhãn bắt buộc được brief hiện tại khai rõ; inventory
còn lại không bị biến thành yêu cầu hiển thị hết. Tên bắt buộc bị bỏ hoặc được
giấu trong text của marker không vẽ chữ đều bị từ chối. Câu tiếng Việt được
chuẩn hóa NFC. Request và pre-render hook kiểm hash context để chặn dùng mốc
hoặc nội dung của tập cũ. Các cue âm thanh vẫn độc lập với vị trí thẻ.

Contract cũ/prompt 9 giữ nguyên làm mặc định. Checkpoint cũ không bị diễn giải
lại theo prompt mới. Prompt 10 chưa có constrained decoder; phải dùng chế độ
unconstrained có compiler/validator strict. Chưa có checkpoint prompt 10 được
chứng minh tốt hơn tại thời điểm kiểm compiler.

## Bằng chứng đã chạy

- `python -m unittest discover -s app -p 'test_*.py'`: 336 tests,
  323 đạt và 13 skip; không có failure.
- 56 train-only native targets → decision → native: toàn bộ ASS frame events
  trùng byte, giữ easing/rotation/geometry/hold/sound semantics; không repair.
- Pinned tokenizer trên 99 mẫu thuộc các partition development cũ:
  tối đa 2939/3072 token, không truncate, không lỗi chuyển target/RAG.
- Counterexamples: nhầm source hash, ref bịa, source frame dùng làm entrance,
  pose trung gian trùng frame, vùng cấm, thiếu nhãn, ROI marker tự tạo và
  provenance do model tự khai đều bị từ chối.

Đây là kiểm contract và serialization; chưa đo chất lượng dựng toàn tập,
khả năng nghe, first-pass acceptance hay phút sửa trên mỗi phút video.
Không lấy 56 mẫu train làm bằng chứng generalization. Vẫn cần cùng nguồn,
cùng RAG, cùng renderer, mức nghe khớp, tập mới không vào train/RAG và so mù.

## Lệnh

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python app/prepare_motion_kaggle.py DATASET --out NEW_PACKAGE --owner duytruyenthong --steps 64 --prompt-version 10
```

Lệnh prepare không upload/train. Chỉ một experiment private được đóng băng
sau preflight; raw footage và bản sửa vlog không được đưa vào package này.
