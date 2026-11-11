# Reference badges và train tiếp — 11/11/2026

User yêu cầu tự bật preset và train thêm từ4reference mới. Hai phần độc lập:
**Reference badges là preset motion gốc theo luật**, còn **CogVideoX LoRA là
model sinh minh họa thử nghiệm**. Không gọi preset theo luật là model đã train.

## Train đã hoàn tất

Private Kaggle run `duytruyenthong/talking-head-cutroom-reference-refresh-v1`:

- 64 optimizer steps mới **đã áp dụng**, nối từ checkpoint32steps, tổng96steps.
- Parent SHA `893fd28e0ec2223445e05e5a3467ddc3fdb2ea847acc63cf3a58e145fd071fe8`.
- New SHA `8c0af84e2fe66e353e59a8c2ecaeaacf2dbc72280d3bf55b070dc8fb5eb88d83`.
- Receipt `parent_weights_loaded=true`; weight deltaL2=3,107243; training loop
  83,7196giây trên2TeslaT4. Giữ model nền/revision như lượt trước.
- Nạp trọng số cha, **khởi tạo optimizer mới** cho dữ liệu cập nhật; không gọi
  đây là phục hồi toàn bộ optimizer state chưa được lưu từ lượt trước.
- 28silent clips:26train/2development cũ giữ nguyên.14crop mới từ4video; loại
  hai crop có ảnh người lồng trong màn hình. Mỗi crop có hash/source timecode.
  Không upload voice hoặc toàn bộ video dài. User cho phép train thử nghiệm
  riêng tư; không suy quyền phân phối lại tư liệu.
- 4source mới được giữ cùng nhóm train thận trọng; creator split chưa xác minh.
  Development loss không phải kiểm định trên creator/tập độc lập.
- Development baseline khớp **chính xác** loss cuối của checkpoint cha, rồi đổi
  từ[0,318486;0,298380] thành[0,317866;0,271225]. Điều này hỗ trợ bằng chứng
  train tiếp đúng weights, không chứng minh video đẹp hơn.
- Đã tải adapter/receipt/4preview, kiểm hash và full decode17frames mỗi clip.
  Đã import compactZIP thật qua UI, giữ checkpoint cũ.

Lệnh nối checkpoint cho lần thử có dữ liệu đủ điều kiện:

```powershell
python app/generative_train.py --dataset "DATASET" --out "NEW_RUN" --steps 64 --resume-sha256 "PARENT_SHA256"
```

Worker Kaggle tìm parent receipt hoàn tất và adapter đúng SHA trong input; nếu
thiếu/sai thì dừng, không âm thầm train lại từ model nền. Không cần thư viện
model để dùng editor local. Model worker mới đã chạy thật trên Kaggle.

## Preset bật trong editor

Style → Motion profile → **Reference badges · original motion preset**.
Đã bật cho job vlog “5repoGitHub”, intensity0,6. Giữ script, music, cue/anchor,
source proof và các override đã có. Title/name lấy từ lời và nội dung của user.

Thông số có thể tái tạo: DejaVu Sans Bold58px, panel#2100BA, slide tối đa32px,
settle280ms và fade90ms ở intensity1. Intensity0 giữ badge tĩnh, không xóa thông
tin. Đây là thời gian thử do kit chọn; frame reference không đo được easing.
Plan freeze version1, tham số và reference hash/timecode. Không chép pixel hay
tên/chức danh của creator vào video người dùng.

Reference đã xem: sơ đồ có các label tại10s; lower third tại1s của clip7skills;
badge/callout cạnh người dẫn tại1370,266667s của clipClaude2.0. Chỉ kết luận
hierarchy/bố cục nhìn thấy. Không suy nhạc/SFX hay cadence từ các frame này.

5giây thử NVENC:150frames, SHA
`28c79a77c56011df8b4081b106c24a95287794d74d0e5a56fd162d639afc3bf1`,
đã xem frame360px. Giữ các bản cũ; bản mới đi qua normal UI và exact-master QC.

## Hai lỗi thực tế trên EXE đã sửa

1. Năm SFX có delay dài làm bus FFmpeg8.1.1 bị kẹt ở EOF khi trộn với pad vô
   hạn. Đổi sang từng input hữu hạn, pad/trim đúng sample count, chunk1024 và
   một filter thread. Ca118,1s chạy0,219s; cue timing không bị dời. Dừng đúng
   FFmpeg child đã xác minh, giữ failed artifacts và các master trước.
2. Python nhúng `._pth` không tự thêm thư mục script ngoài vào module path,
   khiến checker báo thiếu `_platforms` dù file có thật. Bootstrap thêm đúng
   script directory, dùng UTF-8 và chạy nguyên checker upstream. Test isolated
   Python với sibling import, đường dẫn có dấu và argument tiếng Việt pass.

Không bypass gate hoặc điền approval để chữa lỗi runtime. Bản có lỗi dependency
được giữ BLOCKED; bản mới phải chạy lại QC. Unit43app +47QC +39reference-lab pass.

## Bằng chứng và giới hạn

Private artifacts dưới `output/reference-training/`: `refresh-v001` chứa
dataset/receipt/checkpoint; `preset-test-v001` chứa5sNVENC;
`preset-activation-v002` chứa actualUI import và submit inference;
`preset-activation-v003` chứa lần chạy EXE sau sửa checker. Media và weights
không đưa lên GitHub. Không dùng log train hoặc số loss để tự cấp READY.

Lượt inference thực tế gửi qua UI dùng720×480/17frames/40steps, cùng prompt và
seed3407 như lượt trước. Kết quả so chất lượng phải dựa trên MP4 đã tải/kiểm,
không dự đoán trước từ training loss. Voice/full-mix listening và review1× vẫn
cần reviewer có khả năng nghe; agent phiên này chưa có khả năng đó.

### Kết quả native và A/B

EXE development v010 đã chạy đúng UI→render→rerender→full QC. Bản mới
`c1698a4bd44845c9a78cdaac68a08b16` có SHA
`3886f268a8ea3872ee6a44578cf8f09d944954f91caa393150e964768219d4ad`:
118,1s,1080×1920/30,3.543frames,h264_nvenc,AAC48k,−16,07LUFS/−1,65dBTP.
Full decode và rerender byte-identical. Bộ checker hoạt động trên Python nhúng;
bản bị BLOCKED trước sửa giữ nguyên, không đổi thành READY bằng cách bỏ gate.

Đối chiếu project trước/sau: mọi setting ngoài motion profile/intensity giữ
nguyên; voice.wav, sfx.wav và music.wav **đều khớp từng byte** với bản trước.
Năm SFX marker stem lệch0frame. Final-mix correlation thấp do trùng giọng:
UNVERIFIED, không suy là đã nghe đạt. Đã kiểm frame phone-size; chưa có lượt
nghe/xem toàn bộ1×. Master mới **NEEDS_REVIEW**.

A/B8s lấy master19,80–27,80: A hình trước, B badge mới; cả hai mux cùng một
AAC audio. Measured−15,91LUFS/−1,71dBTP bằng nhau. Source phrase từ caption là
“cái đầu tiên á, chính là FFmpeg Skill”; cần reviewer nghe xác nhận. Output
`output/reference-training/deliveries-v001` có MP4, A/B, SRT, recipe/timeline,
cue sheet, QC và validation.json. Không có trim mới, mọi timestamp giữ nguyên.

### Kiểm model trên worker mới

Native UI import đúng adapter mới, gửi prompt-only và tải actual job
`duytruyenthong/talking-head-cutroom-generate-d13c9b09e426` COMPLETE.2TeslaT4,
388,396s; `weights_loaded=true`, active adapter `talking-head-style`, đúng SHA
8c0af… . Cả2MP4 đã hash/full-decode17frames. Baseline model nền có SHA **giống
chính xác** baseline lần trước; prompt/seed/resolution/steps giữ nguyên.

Candidate mới SHA
`5d5e3ebbb6879cdd5d9e963fbeeb3919ad503ad340fcc22a96b11bb70c0c1716`.
Đã so frame đầu/giữa/cuối với parent candidate720px: cả base/parent/new đều có
chữ giống watermarkPOND5 trên màn hình laptop. **REVISE**, không chèn vào vlog,
không tuyên bố chất lượng B-roll tốt hơn từ loss giảm. Lưu source/model output
để audit; không xóa watermark rồi coi là asset đã được duyệt.

Một lượt kiểm animation3thẻ riêng dùng prompt thực nghiệm cũ/seed3408, cùng
model và settings, đã được gửi qua UI để kiểm đúng nhóm minh họa vừa học.
Kết quả và giới hạn được ghi vào artifact riêng sau khi job hoàn tất.

Cách nạp model-level LoRA tham khảo [Diffusers PEFT loader](https://huggingface.co/docs/diffusers/api/loaders/peft).
