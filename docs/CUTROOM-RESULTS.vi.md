# Cutroom — kết quả triển khai và kiểm thử 11/11/2026

Mã làm việc: `D:\.codex\workspaces\talking-head-video-editing-skills`.
Preview được cung cấp ở thư mục video gốc đã được chạy trước khi sửa. Bản gốc,
các lần render lỗi và các master trước vẫn được giữ. Đây là bản bàn giao phát triển
đã chạy trên máy hiện tại; chưa chứng nhận sẵn sàng bán trên máy Windows sạch.

## Các thay đổi hoạt động

- Batch UI Workspace/Exports, inspector Script/Style/Cutaways; match tên tiếng Việt
  NFC/NFD, giữ script trùng tên ở trạng thái chưa gán. Áp style chỉ đổi trường đã chạm.
- Reference có ba vai trò riêng: phân tích style, dùng làm proof trên hình, đưa vào
  intake training. Phân tích ngay không cần train. Âm thanh trộn trong master không
  bị gọi là stem SFX đã xác nhận.
- Generate intro & demos từ script: passages/occurrences, storyboard, intro
  result-first/promise/list và demo software/diagram/before-after/placeholder.
  Scene có ID, phiên bản, scene.json, timeline.json, thumbnail và MP4 riêng.
  Edit/Regenerate/Disable/Export/Insert không thay cảnh khác; các bản trước còn nguyên.
- Cùng clock30fps/48kHz cho motion và cue; độc lập click/contact và chime/result.
  Music Off/auto/my track, ducking theo voice, stem riêng; không trộn audio của
  artifact lần hai hoặc khởi động lại nhạc khi chèn cảnh.
- Planner optional có built-in/base/base+retrieval/fine-tuned. Fresh worker đọc
  safetensors local, kiểm hash/revision, ghi weights thực sự đã nạp. Thiếu checkpoint
  hiển thị fallback; không đặt tên fine-tuned cho rules. Manual cues được giữ.
- Dataset v2 tách input khỏi target, gộp creator/series/family/hash/excerpt trước
  split; chỉ train split vào retrieval. Nhãn STAY_PRESENTER khác UNLABELED. Lưu sửa
  tay before/after/source/reason để editor xác nhận. Không suy lý do bỏ take từ MP4.
- Six-gate hooks chạy từ Render: freeze → render → rerender thật → decode/measure →
  review. Đúng hash/current revision và bằng chứng người xem/nghe mới được duyệt.

## Kết quả chạy thật

| Kiểm thử | Kết quả |
|---|---|
| App unit tests | 32 PASS |
| QC/hook unit tests | 46 PASS |
| Reference-lab regressions | 39 PASS |
| Native six-second smoke, current checker | 7/7 trạng thái đúng; synthetic fixture, không duyệt video thật |
| Batch UI, agents off, fresh workspace | 10 import, 8 MP4 thực, 2 Needs input, không có JS error;2 worker |
| Ba script qua UI | software2 artifact, concept2, comparison6; đúng5repo/order, thiếu proof giữ placeholder |
| Scene version/invalidation | sửa/regenerate demo giữ intro hash; sửa câu cuối chỉ gắn cờ demo; giữ export cũ |
| Actual missing-checkpoint export | For review, weights_loaded=false, fallback hiện trên UI và receipt |
| Fault click trễ4frame | đo3.975frame, REVISE; bản thử đầu thiếu vùng tìm kiếm giữ lại, checker đã sửa |
| Stale approval hash | HTTP400, “This master has changed” |
| Four scoped skills | quick_validate PASS; validator dùng PyYAML6.0.3 trong venv trên D |
| Source package giải nén | 2job qua UI; thiếu click chỉ làm1job lỗi; khôi phục/retry thành công, master kia giữ hash |
| Native EXE | launcher/runtime preview đã thích nghi với mã hiện tại; chạy thật CPython3.12.10, FFmpeg ready; giữ cache/log trên D |
| Trắc nghiệm ẩn preset | form test PASS; không nghe → audio UNVERIFIED; chưa đo sửa → null;0reviewer thật |
| Quản lý nguồn qua UI | 2render cóv001/v002; latest/history, rename giữ filename, project/search, take2 reset script/cue, archive/restore giữ hash; thumbnail source mới HTTP200 |

Test UI dùng Playwright điều khiển trình duyệt thật, tải file và gọi renderer thật;
walkthrough là Playwright, không ghi nhãn Recordly. Chưa có lượt gọi thành công
OpenBot/MausBot. Các capability tương ứng để disconnected.

## Các file xem được

Trong `output/cutroom-motion/deliveries-v001`:

| Bản cùng media | LUFS-I | dBTP | Trạng thái |
|---|---:|---:|---|
| A current preset |−16.26|−1.70|NEEDS_REVIEW|
| B enhanced, music off |−16.26|−1.70|NEEDS_REVIEW|
| C enhanced, music on |−16.28|−1.70|NEEDS_REVIEW|
| D contrasting reference |−16.26|−1.70|NEEDS_REVIEW|

Các bản đều614frame,20.466667s,1080×1920,30fps,H.264/AAC48k; actual rerender
byte-identical. Blind-comparison giữ3nhãn ẩn; mức nghe đo−16.39/−16.37/−16.39LUFS.
Reviewer0, chưa có bản thắng, chưa suy acceptance hoặc thời gian sửa bằng0.

Trong `output/cutroom-artifacts/deliveries-v002`:

- `intro/preview.mp4`:2.6s,78frame; script mẫu Cutroom, result thật được preview
  trước, logo cộng đồng gốc, rồi presenter. **Storyboard: thiếu narration đúng mẫu.**
- `demo/preview.mp4`:10.7s,321frame; footage UI thật của **clip kiểm thử xuất MP4**,
  không phải thao tác sản phẩm/khách giả. Click/contact1.700s là candidate quan sát
  con trỏ; success badge thật3.833333s; opened MP4 thật8.233333s. Cue sheet giữ các
  sự kiện riêng. Không chứng nhận âm thanh lời dẫn vì preview này không có lời mẫu.
- `intro/scene.json`, `demo/scene.json` và timeline.json: nguồn scene chỉnh được.
- `episode/edit.mp4`: đoạn thử Recordly có **giọng thật** từ1.mp4 source49.0–69.466667,
  intro original và logo, proof thật, nhạc/SFX;20.466667s. Đây là đoạn thử, **không phải
  vlog đầy đủ năm repo hoặc tập unseen**. −16.28LUFS/−1.70dBTP,614frame, full decode.
- `episode/render-project.json`, project.json, captions.srt, stems, qc.json và
  planner-receipt.json: recipe và bằng chứng. Toàn bộ bản v001 vẫn giữ nguyên.

GPU kiểm thực: NVIDIA GeForce RTX3070Ti Laptop8GB, driver572.42; encoder tag master
`Lavc62.28.101 h264_nvenc`. Có test5s footage thật với chữ trước render. Phần ASR
nguồn được tái sử dụng từ faster-whisper CUDA int8_float16; không chạy ASR mới trong
vòng artifact này và không tổng hợp giọng người dẫn.

## QC theo timecode

| Vùng | Đã xác minh | Còn cần người duyệt |
|---|---|---|
| Episode0–2.6 | title Recordly, logo gốc, mặt và caption không bị che | lời mở đầu/nhịp intro ở1×; watermark storyboard còn chủ ý |
| Episode5.333–7.033 | vào screen trước “đây”; nút Render selected(1) đọc được ở360px | đây là ví dụ export Cutroom cho lời giải thích Recordly, không chứng minh tính năng Recordly tự chạy |
| Episode7.033/frame211 | cue contact cùng clock; isolated peak lệch0frame | final-mix correlation0.644<0.65; nghe accent và toàn câu CTA/bấm vào đây |
| Episode9.167/frame275 | badge For review hiện thật, caption dưới proof; isolated peak0frame | chime final-mix và thời gian đọc ở tốc độ thật |
| Demo8.100→8.233 | sửa nhãn mở MP4 sớm4frame; v003→v004, giữ cũ; frame247 có modal thật | xem diễn tiến toàn đoạn, nghe SFX |
| Toàn master | đo format/loudness/decode/hash; voice stem không bị chia theo cutaway | nghe toàn bộ1×, tiếng cuối, caption ±150ms và lip-sync đầu/giữa/cuối |

Tôi đã xem các PNG decode kích thước điện thoại; **chưa có audio input để nghe toàn
master**, nên không xác nhận audibility. Người duyệt có audio cần xem/nghe exact
master và ghi6gate/timecode; không chuyển trạng thái READY từ số đo đơn thuần.

## Bốn kết luận riêng về model

1. **Train có xong không?** Lượt Kaggle cũ40step/TeslaT4 đã xong, nhưng input flags
   sinh từ target làm benchmark không hợp lệ. Vòng mới: **BLOCKED trước GPU**, không
   cập nhật trọng số. Không tái huấn luyện/tối ưu trên test cũ đã xem.
2. **App có nạp trọng số không?** **Không.** Test fresh worker chọn candidate thiếu
   checkpoint ghi weights_loaded=false và hiển thị built-in fallback. Không coi là
   test inference PEFT thành công; đường load trọng số thật còn chưa được kiểm.
3. **Có cải thiện tập unseen không?** **Chưa biết.** Có25file/24hash,23nhóm nội dung
   sau đối chiếu curation cũ (có bản khác độ phân giải),19nhóm presenter candidate;57nhãn thí
   nghiệm cũ chỉ sample-frame/ASR, creator unknown/provisional, chưa tương thích input
   độc lập v2. Intake mới293cửa sổ UNLABELED,0eligible/0usable. Chưa có tập người dẫn
   mới chưa dùng phát triển; không giả danh đoạn Recordly là holdout.
4. **Lợi ích có đáng chi phí không?** **Chưa biết.** Reviewer0; acceptance, repair
   minutes, preference/ties và cost/accepted minute giữ null. API spend cho built-in0
   không có nghĩa GPU/agent/human time miễn phí.

Model nhỏ được giữ theo đường có sẵn: Qwen2.5-1.5B-Instruct revision
989aa7980e4cf806f80c7fef2b1adb7bc71aa306, QLoRA rank8/40step, không train face/voice.
Trainer v2 định nghĩa4arm rules/base/base+RAG/adapter+sameRAG. Freeze retrieval, prompt,
media, decoding và renderer khi so sánh hai nhánh RAG; accuracy component không thay
cho blind review complete episodes. Log lưu config/split/data/code/checkpoint hashes
và actual optimizer steps. [PEFT chính thức](https://huggingface.co/docs/peft/package_reference/peft_model)
là cơ sở cho đường nạp adapter; chưa có checkpoint hợp lệ để xác minh nó trên app.

## Lệnh tái chạy

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py app/app.py --data '.\output\cutroom-workspace'
& $py -m unittest discover -s app -p 'test_*.py'
& $py -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
& $py -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py'
node --check app/ui/app.js
& $py app/learning_inventory.py 'D:\Video editing\Talking head video editing skills\reference videos' --profiles output/cutroom-motion/reference-profiles --out output/cutroom-learning/NEW-intake
& $py app/train_planner.py --dataset output/cutroom-learning/intake-v001/dataset-v001 --out output/cutroom-learning/NEW-run --validate-only
& $py app/prepare_planner_kaggle.py output/cutroom-learning/intake-v001/dataset-v001 --out output/cutroom-learning/NEW-private-package
& $py app/cli.py qc output/cutroom-artifacts/deliveries-v002/episode
```

Trainer preflight hiện trả exit3/BLOCKED đúng dự kiến. Kaggle notebook riêng đã tạo
ở output/cutroom-learning/kaggle-private-v002; chưa upload/chạy GPU mới. Khi đủ nhãn
và split hợp lệ, chuẩn bị package mới rồi chạy notebook private; gate chạy trước
cài thư viện, không upload raw video. Không ghi đè intake/split/test đã đóng băng.

UI acceptance cần Playwright1.65 + Chrome, PYTHONPATH trỏ runtime test trên D:
`python app/artifact_acceptance.py --url http://127.0.0.1:8773 --out NEW-UI-RUN`.
Script này dùng workspace đã import source tutorial/screen; batch test trống:
`python app/browser_acceptance.py --url NEW-EMPTY-SERVER --out NEW-BATCH-RUN`.
Actual logs/screenshots: output/cutroom-artifacts/ui-run002, fix-run001,
output/cutroom-validation/final-run001 và output/final-qc-validation/run008-cutroom-final.

Intake mới nhất `output/cutroom-learning/intake-v003` tái sử dụng family/scope hints
từ manifest cũ, giữ creator/series chưa xác minh và nhãn chưa duyệt. Không lấy quyền
sở hữu làm bằng chứng danh tính creator. Native preview hiện ở
`output/cutroom-release/Cutroom-Windows-dev-v005/Cutroom.exe`, dùng workspace đã có
các bản thử trên D. Launcher v001 từng bị từ chối ghi cache ở gốc D; bản sửa dùng
cache bên trong workspace. Gói này là development handoff, chưa là release thương mại.
Phiếu xem mù: `output/cutroom-learning/viewer-quiz-v001/index.html`; đáp án nằm ngoài
gói reviewer, câu trả lời không tự duyệt master hoặc tự vào tập train. User đã chọn
phương án C ở checkpoint về so sánh unseen có kiểm soát.

## Bổ sung quản lý source theo phản hồi trực tiếp

Nguồn gốc và rendered cut hiện có nhận diện riêng: source ID, take number, filename
gốc, tên hiển thị và project. Source có tìm kiếm/lọc project/active/archive; Exports
mặc định chỉ hiện cut mới nhất, có lịch sửv001/v002… và liên kết về nguồn. Tên file
tải xuống có version. Manage mở đường dẫn/hash gốc và Show in Explorer.

Add new take tạo một nguồn mới cùng family; giữ style, tách script/events/cutaways,
chỉ giữ script take cũ ở ô reference không áp dụng. Đổi tên/project là metadata
tổ chức, không thay file/brief/master hoặc chuyển approval. Archive không xóa asset
hay export; job archived không được queue nhầm. File import mới có filename dễ đọc
trong thư mục source ID, còn đường dẫn cũ được giữ tương thích.

Đã kiểm qua UI tại output/cutroom-validation/source-management-v002. Workspace
đang mở có2source active:1.mp4 đầy đủ và đoạn thử Recordly20s;4source storyboard test
archived;9export cũ giữ nguyên hash. Nguồn đầy đủ mới import chưa gán script/timecode
cũ một cách tự động. Sửa lỗi thumbnail khi chuyển cách lưu nguồn đã được kiểm bằng
HTTP200 và ảnh decode. Đây không phải lượt render lại vlog đầy đủ hoặc train model
sinh B-roll: animation hiện vẫn từ code/rules và demo dùng footage thật.

## Điều kiện còn thiếu trước release

Nghe/xem exact master; narration pickup cho script mẫu; proof riêng cho từng repo
nếu giao vlog5repo; nhóm creator/series/excerpt và nhãn temporal/independent-input;
new unseen episode, blind review với người nghe được; actual adapter inference;
clean-Windows test và distribution grant của supplied preview. Chưa tự động publish,
chưa đẩy media riêng tư lên GitHub, chưa tuyên bố sale-ready.
