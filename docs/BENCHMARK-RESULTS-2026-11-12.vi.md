# Kết quả benchmark ngày12/11/2026

Đã có benchmark toàn tập chạy local qua UI và CLI. **Chưa có bằng chứng model
tốt hơn rules trên tập mới.** Các tỷ lệ editor giữ bản đầu, viewer comprehension
và phút sửa/phút video vẫn `null`: chưa có lượt người xem/nghe đủ điều kiện.

| Exact export | Kích thước / fps | Giây / frame giải mã | LUFS / dBTP | Kết luận |
|---|---|---|---|---|
| V035 · `ca15d2c90348ddfa…` |720×1280/30|118,1/3543|−14,08/−1,49|Baseline development; QC còn review |
| Smoke có footage và chữ · `eb419191271e8d27…` |1080×1920/30|5/150|−16,03/−3,24|NVENC thực, decoded samples đã xem; chưa nghe |
| Full rules v001 · `25b586e90665fd2b…` |1080×1920/30|118,1/3543|−16,08/−1,65|Xuất qua batch UI; cần sửa CTA riêng và diagnostic footer |
| Full rules revision · `081b1b816158b8a8…` |1080×1920/30|118,1/3543|−16,08/−1,65|CTA được giữ4,5s; footer chỉ còn ở scene preview; full review vẫn pending |

MP4 full rules là **mẫu benchmark của pipeline native**, không thay v035 làm
cut đã được người dùng duyệt. Nó dùng selected camera cut + SRT của v035,
những capture thật đã có và source-linked intro/Recordly spec. Không tự đưa
reference-only pixels vào video. Branding/logo toàn tập, nhịp dựng, phụ đề thực
sự theo lời và độ đủ của mỗi tính năng còn phải đối chiếu brief đầy đủ khi giao.

## UI và thay đổi đã kiểm

- Generate có chọn style Balanced/Maverick riêng cho từng lượt. Một proof gán
  Recordly trong tập5 repo không điền thay4 demo còn lại. Scene/old cuts giữ lại.
- Exports → **Benchmark full videos** chọn bản và reference, giải mã/đo trọn,
  đảo thứ tự, giấu preset, mở video360px và phiếu sáu gate/flow/quiz/repair timer.
  Đã chạy route tạo benchmark và lưu một phiếu automation ở trạng thái pending,
  **không có quyền xem/nghe**, reviewer0; không dùng phiếu đó cấp READY.
- Reference master được xem riêng trong review, không chèn vào output. Private
  mapping URL trả404. Thay bound master/brief/caption làm score từ chối review.
- 3 short reference32,73/71,07/31,73giây được phân tích scene candidates toàn
  chiều dài. Có phase timecodes và frame/ASR evidence; không chứng nhận nghe1×.
  Detector chỉ thấy1 scene change trong clip71giây dù có nhiều chuyển động thẻ:
  đây là proxy yếu, không biến nó thành target nhịp cắt.
- Preview2,6giây từng bị master loudness gate chặn: −20,81LUFS/−0,94dBTP.
  Đã sửa bằng policy preview giữ mức giọng nguồn và true-peak ceiling; master
  vẫn phải qua −16LUFS±2/TP≤−1. Không hạ chuẩn master để cho test qua.
- Encoder thành công được ghi vào `ffmpeg-encode.jsonl` và `edit-review.json`.
  RTX3070Ti Laptop8GB; smoke và master thực tế dùng `h264_nvenc`. ASR của cut
  118,1giây chạy local CUDA/float16; các lần sửa sau dùng lại transcript đó.

Before/after trong revision: CTA `01:46,54 → 01:46,533` (roundframe3196),
beat `cta`, source raw khoảng`02:08,37`; hold135frames. Recordly footer được
bỏ khỏi master ở`00:44,5–00:55,2`; target/contact/result và lời/phụ đề không retime.
Phone samples: result title rõ tại`00:49,2`; CTA nguyên cụm tại`01:48,5`.
Đây là quan sát frame, chưa phải full normal-speed watching/listening.

## Lượt Kaggle và model thật

Private run: `duytruyenthong/talking-head-spec-training-2e27d2b3d964`.
Qwen2.5-1.5B pinned base, LoRA spec planner,192 optimizer steps trên `cuda:0`
TeslaT4. Receipt liệt kê2T4 có sẵn; trainer dùng một device, không gọi là
multi-GPU training. Checkpoint SHA:
`869444f8c7f28742e04287a8a346a40e202fe7689da5b3734a44e41f456a9818`.

38 labels: train23 =22 quan sát visual timecoded từ15 reference +1 fixture;
validation5 từ3 source khác; test10 từ **một** raw vlog. Tổng27 nhãn visual
reference;0 nhãn editor xác nhận. Unknown SFX không bị biến thành mute labels.
Không upload reference media; đây là học **spec/decision**, không phải model
sinh video pixels. Vlog đã dùng phát triển không là bằng chứng unseen quality.

Validation loss **2,0730 → 2,6183**. Small schema check trên4 scene contexts:
cả hai arm intro0/3, demo1/1; số này không phải điểm toàn video. Worker local
mới đã nạp đúng checkpoint/base/RAG trên CUDA. Trong context toàn tập:

| Arm | Intro | Demo | Full export |
|---|---|---|---|
| Rules | Hợp lệ | Hợp lệ |Có118,1s; đã sửa hai lỗi pipeline/CTA nêu trên |
| Base + RAG | Lead ngoài giới hạn | Thiếu evidence type |Bị chặn; không thay rules âm thầm |
| Fine-tuned + cùng RAG | Text ngoài inventory nguồn | Hợp lệ,0 compiler repairs |Batch bị chặn bởi intro |

Vì chưa có đủ3 full arms hợp lệ, benchmark không có paired winner/CI. Adapter
vẫn experimental, không bật production. Cần thêm nhãn target bám inventory/
anchor và balance tiếng Việt; cân nhắc giảm miền quyết định model thay vì để
model gõ lại toàn bộ text/keyframe. Phải đo lại bằng cùng protocol sau sửa.

## Vòng học đã nối và các blocker

`video_benchmark feedback` yêu cầu correction được editor duyệt, source group,
exact-master review và corrected spec thực sự có trong render recipe. Chỉ duyệt
hình thì bỏ audio supervision. `merge-feedback` tạo dataset/RAG mới và chặn
source/group/creator đã giữ cho validation/test. Chưa có cặp editor duyệt thật;
không train thêm từ câu trả lời trắc nghiệm hoặc phiếu automation.

V035/raw vlog cùng một source family; khi cho vào học cần retire test group
và lấy tập mới làm bài kiểm kế tiếp. T1 take nói ba tên và câu bên vai: user
xác nhận chưa có. Chưa đủ tập mới/creator identities và chưa có full hearing
review, viewer answers, repair sessions hay bằng chứng giới hạn chi phí.

Code tests:105 app +51 QC +39 reference-lab =195 PASS; skill validation PASS.
Unit tests là guardrails; số195 không phải điểm chất lượng phim.

Đường dẫn bằng chứng private trên máy:
`output/benchmarks/full-v001`, `nvenc-smoke-v002`, `ui-full-v001`,
`ui-repair-v002`; workspace benchmark `1cc311f7e9d44c8580e193fd942cef60`.
Các recordings, MP4, source paths và weights không commit vào source repo.
