# Talking Head Cutroom: rules, workflow và hooks dùng cho mọi tập

Trạng thái: quy tắc vận hành v1. Đây là hợp đồng của kit, không phải tuyên bố
model đã đạt phong cách reference. Vlog “5 repo GitHub” là bài kiểm thử đầu;
không đưa đường dẫn, tên repo hay timing của tập đó vào mặc định cho tập mới.

## 1. Những gì giữ chung, những gì thuộc từng tập

Giữ branding, logo đã được phép dùng, font tiếng Việt và sáu gate QC chung.
Mỗi tập có source hash, transcript, script tham khảo, brief, beat IDs, proof,
timeline, captions, scene versions và review riêng. Batch chỉ sửa trường được
chọn; script, source, crop, cue, scene khóa và chỉnh tay không bị ghi đè khi
đổi style. Reference dùng học phong cách không tự thành B-roll cho khách.

## 2. Rules ra quyết định

| Quyết định | Rule | Khi thiếu dữ liệu |
|---|---|---|
| Nội dung / take | Lời thu thật quyết định nội dung. Chọn câu trọn ý, giữ qualifier, tiếng cuối và nhịp nghỉ có nghĩa. | Giữ take tốt; câu mới là pickup, không ghép giọng giả. |
| Hook | Đề xuất ba hướng dựa trên lời và bằng chứng thật; aim promise/result trong 3s. | Đánh dấu hook cần thu, không hứa kết quả chưa có. |
| Demo | Chia cụm 2–3 câu; map nhận ra target → contact → result đọc được. | Giữ mặt người dẫn ở chỗ thiếu; ghi pickup chính xác. |
| Timing | Lưu source time, câu/occurrence và beat ID; master time tính lại từ cuts. UI chậm thì cho thấy sớm hoặc giữ lâu hơn. | Trim cắt qua scene phải căn lại; không âm thầm dịch click sang hành động khác. |
| Animation | Mỗi nhấn có mục đích: hướng mắt, phân cấp, giải thích hoặc chuyển ý. Style Maverick là lựa chọn từng tập, không phải mật độ hiệu ứng bắt buộc. | Presenter hold là lựa chọn hợp lệ. |
| Chữ | Font có đủ dấu; text dài reflow/nới thẻ, không thu nhỏ đến khó đọc. Captions thường tối đa hai dòng. | Preview ở kích thước điện thoại; chưa xem thì chưa xác nhận đọc được. |
| Proof | Nút, click, thành công và giá/đơn vị phải từ nguồn thật của đúng lượt chạy. Badge không chứng minh file đã mở. | Dùng Computer Use + Recordly quay bổ sung. |
| Âm thanh | Voice liên tục; motion, từng SFX và music có điều khiển riêng. Click ở contact, chime khi result hiện; peak lệch tối đa 1 frame. | Không biết contact/result thì bỏ cue hoặc để cần kiểm, không đoán theo lời. |
| Reference | Ghi file/hash, timecode, điều quan sát, cách quan sát và tham số suy ra để thử. | Frame tĩnh không chứng minh cadence hoặc âm thanh. |
| Học máy | Chỉ output spec dữ liệu có thể sửa; qua cùng validator/renderer như rules. Ghi model/checkpoint/hash. | Model lỗi phải báo; fallback rules phải được ghi rõ, không tính là inference thành công. |

## 3. Workflow cho một tập mới

1. **Intake:** import A-roll, mic rời, script và reference riêng; hash/probe,
   kiểm quyền sử dụng. Brief liệt kê lời hứa, demos, CTA và format đầu ra.
2. **Voice-first:** ASR tiếng Việt + đối chiếu cả câu, chọn take, lưu source cuts;
   xuất bản chỉ nghe giọng. Chưa nghe được phải để review pending.
3. **Plan:** ba hook → chọn hook → cụm 2–3 câu → bảng target/action/result;
   phân loại từng hình: real screen, code illustration, reconstruction hay
   presenter. Chọn reference timecodes có liên quan, ghi giới hạn quan sát.
4. **Capture:** chuẩn bị cửa sổ; Recordly đúng nguồn, mic/webcam/system audio
   tắt cho B-roll. Record trước thao tác Computer Use; giữ đến kết quả đọc được.
   Lưu project và media; thử cảnh đầu trên phone trước khi quay hàng loạt.
5. **Build qua UI:** chọn đúng recording/script; Generate intro & demos,
   preview từng scene, chỉnh và khóa quyết định. Batch không xóa override.
   Spec schema v1 hiện chạy 30fps; project cũ không có spec vẫn dùng renderer cũ.
6. **Render:** version mới; NVENC sau smoke 5s có chữ/hình. CPU fallback chỉ
   bước không tương thích, ghi encoder thực tế. Giữ nguồn, timeline và bản cũ.
7. **QC và sửa:** ba hook cuối dưới đây; kiểm đúng MP4, sửa lỗi xác nhận vào
   version mới. Lưu trước/sau master time, stable beat và source time.
8. **Học từ sửa:** lưu proposal/final, sai khác frame/crop/hold/caption và lý do.
   Phân biệt editor-confirmed với inferred/agent-experimental. Cặp đã duyệt vào
   RAG; chỉ train khi đủ dữ liệu và có benchmark độc lập.

## 4. Hooks đang thực thi

| Điểm chạy | Implementation | Việc thực sự kiểm |
|---|---|---|
| Trước render animation | `app/motion_hooks.py::before_render`, được `engine/edit.py` gọi | Schema/text inventory, unique source anchors, số frame, span còn nguyên sau trim, vùng bảo vệ xuyên đường chuyển động, checkpoint identity nếu khai fine-tuned. Không spec thì giữ tương thích project cũ. |
| Khi dựng animation | `app/motion_render.py` | Spec → vector ASS theo frame; receipt, source-linked SFX qua bus hiện có. Không biến đồ họa thành bằng chứng thao tác thật. |
| Trước render master | `talking-head-qc/tools/qc_hook.py before-render` | Profile từ brief/timeline, hash dependencies, không ghi đè master. |
| Sau render master | `qc_hook.py after-render` | Decode đầy đủ, format/frame/audio, đo loudness/true peak và sáu gate; ghi lịch sử QC. |
| Trước giao | `qc_hook.py release` | Kiểm lại exact master và approval hiện hành; receipt chỉ khi READY. |

Đây là hooks của pipeline local, không phải global Codex/Git hook. Spec hợp lệ
chưa có nghĩa là nút dễ nhìn, lời đã khớp hoặc mix dễ nghe. Preview storyboard
vẫn được dựng để duyệt thiết kế, nhưng không được giả làm bản khớp lời.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
# $py: interpreter đã chọn; $v: thư mục version mới, đã có brief/timeline/profile
& $py talking-head-qc/tools/qc_hook.py before-render $v
# Render qua Cutroom hoặc renderer hiện có vào version đó.
& $py talking-head-qc/tools/qc_hook.py after-render $v --skill-root $skill
# Sau khi người có khả năng xem/nghe hoàn tất review.json:
& $py talking-head-qc/tools/qc_hook.py release $v --skill-root $skill
```

Status: **REVISE** khi có lỗi xác nhận; **NEEDS_REVIEW** khi thiếu chứng cứ xem/
nghe; **BLOCKED** khi công cụ/input không chạy; **READY** chỉ khi exact master
đạt sáu gate và người duyệt cuối phê duyệt. Thay brief, timeline, captions,
renderer, model hoặc master thì sign-off cũ không còn đủ.

## 5. Vòng học và điều kiện bật preset

Inventory → gộp duplicate/content family/creator/series → chia train/val/test
trước khi tách scene → RAG chỉ train → train adapter mới, giữ checkpoint cũ →
load lại trong worker mới → render qua cùng UI/renderer → so mù trên tập chưa
dùng làm mẫu. Ba nhánh: rules, base + RAG, tuned + cùng RAG. Giữ cùng media,
audio, mức nghe và chỉ đổi quyết định cần thử. Giữ riêng điểm intro và demo.

Ghi số thực, không điền ước lượng thay người dùng: tỷ lệ đoạn giữ nguyên lần
đầu = đoạn được chấp nhận không sửa / đoạn được duyệt; phút sửa/phút thành
phẩm = phút sửa được đo / tổng phút video cuối được duyệt. Thêm proof match,
đọc chữ, che khuất, timing SFX, render success và chi phí. Reviewer không nghe
được phải để audibility unverified. Không tự kích hoạt adapter cho khách chỉ
vì train/load thành công hoặc nhiều hiệu ứng hơn.

### Giới hạn hiện tại

- Đã có QC hooks và workflow UI nền. Animation spec/renderer/hook mới đang
  được kiểm thử; chưa công bố mọi lựa chọn schema là component đã đạt QC.
- Dataset spec hiện là nhãn tái dựng thử nghiệm của agent, **0 nhãn editor xác
  nhận**; không phải project/keyframe gốc của reference. Train trên các nhãn
  rules này chỉ kiểm pipeline/distillation, chưa chứng minh học đúng cách dựng.
- Corpus hiện chưa đủ mục tiêu 50 reference duy nhất. Không dùng source trùng
  để tăng số lượng hoặc coi test gần trùng là chứng minh tổng quát hóa.
- Không hứa giống hoàn toàn reference; chỉ nâng trạng thái khi có kết quả so
  mù, lỗi được sửa và người dùng đánh giá trên tập mới.
