# Intro promise trong batch editor

Lượt này thực hiện tiếp hợp đồng của `Cutroom-Full-Audited-Codex-Prompt.txt`
(SHA256 `049fb1b32ec36b52e806502e7c3a0f7306f64a8dec2649705857f845f63e1fd2`).
Không thêm một Studio hay planner song song. Dùng Generate intro & demos,
scene lock, insert/remove và render của editor hiện có.

## Thay đổi

- Một recording có ô **Intro promise** tùy chọn. Tiêu đề là lời hứa hình ảnh
  dựa trên brief/script; không sửa lời thu, source quote hoặc phụ đề. Batch
  không phát chung một lời hứa cho nhiều tập. API từ chối vượt 140 ký tự hoặc
  sai kiểu, không cắt mất chữ âm thầm. Tiêu đề mới có cache key riêng.
- Mô tả scene trên card/preview dựa vào loại nguồn đã gán. Văn giải thích do
  model sinh vẫn giữ trong advanced JSON để chẩn đoán, không được dùng để
  tuyên bố footage thật là synthetic hoặc tự nhận đã qua QC.
- Ghi chú reference đã duyệt là guidance được chọn. Analysis tự động hoàn tất
  về sau không âm thầm thêm candidate vào guidance ấy. Analysis vẫn có trên
  asset; nguồn/hash thay đổi vẫn bị từ chối. Khi chưa có ghi chú đã duyệt,
  planner tiếp tục nhận số đo ở trạng thái candidate.

## Thử nghiệm phát triển

Protocol và evidence riêng trên D:
`output/reference-training/intro-promise-v001/`.
Không train thêm trong lượt này; dùng adapter v007 đã nạp thật trên CUDA,
SHA `cc75c7e5b47961a8763ef249a49539e2c654d004f782e013008ac493ee4fbbd4`.
Đây là vlog đã dùng để phát triển, không phải tập unseen.

Ba hook đã khai trước: “5 repo GitHub để edit video bằng AI” (chọn từ brief),
“Quay 1 phút, dựng cả buổi?”, “Chèn màn hình cho khớp lời nói”. Tiêu đề chọn
không giả là nguyên văn câu chào ở giây đầu. Reviewer vẫn cần trả lời kỳ vọng
sau khi chỉ xem [0,3), rồi kiểm payoff đủ năm repo.

Baseline UI mặc định xuất toàn tập 118,1s, SHA
`f7b443b73eb5d1b8d9aa3edcb2d7790016ef85c093cd416b65861de6fc51916a`,
trùng MP4 v007. Đổi mô tả không làm đổi hình/tiếng.

Lượt UI đầu sau đó dừng ở assertion: analyzer chạy muộn thêm candidate vào
ngữ cảnh, làm key của demo khác dù chỉ muốn đổi intro. Giữ nguyên log/model
run, scene đề xuất chưa insert, demo khóa và export cũ. Không ghi cold-run PASS.
Sau sửa `source_context.py`, chạy lại theo amendment đã lưu: chỉ một context
intro đi vào inference; đúng demo khóa cũ được tái sử dụng. Không đổi weights,
renderer, voice/SRT hoặc setting. Lượt này kiểm hợp đồng runtime, không tính là
một vòng hill climb chứng minh tăng chất lượng.

**252 app tests PASS**, gồm late-analysis regression; `node --check app/ui/app.js`
PASS. Audio nghe toàn master, câu trả lời hook, sở thích style và thời gian sửa
của editor chưa xác nhận; không tự đánh READY hoặc promote model.

## Kết quả exact export sau sửa

Master mới trong workspace riêng trên D:
`cutroom-intro-promise-001/exports/81b767c898164b93b355af2ba7846240/edit.mp4`.
SHA256 `3f16526606fbe5f695f79776159c61bf5efa34c9e22f681d2e414c0921833abc`.
118,1s; 3.543 frames; 1080×1920/30; H.264 NVENC; full decode PASS;
−16,08 LUFS / −1,65 dBTP. GPU local: NVIDIA GeForce RTX 3070 Ti Laptop GPU,
8.192 MiB. ASR baseline ghi CUDA/float16; không chạy lại ASR khi chỉ đổi title.

| Trước → sau | Kết quả |
|---|---|
|00:00–00:02,60 → cùng source/master interval|“5 repo GitHub” → lời hứa cụ thể từ brief; 0 thay đổi audio/SRT|
|00:44,50–00:55,20 → giữ nguyên|Recordly demo ID/version/plan/hash và lock giữ nguyên|
|contact00:45,967 / result00:49,000|Giữ Releases → Recordly v1.4.0; caption không che hai vùng ở frame đã xem|
|CTA01:46,54, hold135frame|Nội dung/timing cũ giữ nguyên; frame01:48 thấy CTA|

Đã kiểm tất cả78 frame intro và frame biên2,600/2,967s: chữ tiếng Việt đủ dấu,
hai dòng, không chạm mặt/caption, không thấy watermark trong khoảng đã kiểm.
Headline có sẵn từ frame đầu, static theo reference quan sát; không tuyên bố
đã học entrance mới. Sample2,533s còn chữ,2,567s hết chữ. Đây là kiểm frame,
không thay cho phone playback1× hoặc câu trả lời người xem.

Voice.wav, sfx.wav, music.wav và captions.srt hai bản trùng SHA. ASS khác do
layer headline; dialogue cues giữ nguyên. Settings, locked demo và export cũ
đều qua assertion; UI page errors0. Inference run
`3ab132cf22234f3d8e76012ec1f1e64c` chỉ có1prediction intro,
compiler repairs0. Không thay model hoặc tự dùng rules bù đầu ra model.

Trạng thái **NEEDS_REVIEW**. Vẫn cần nghe toàn mix; bằng chứng hiểu hook/payoff;
cảnh FFmpeg playback cần quay Recordly (source picker tự refresh làm helper mất
element; đã yêu cầu chọn đúng cửa sổ một lần, chưa bấm Record); output Runway
đúng lượt chạy chưa có. Không có animation nào mới được admit thư viện.
Model gain vẫn **INCONCLUSIVE**, chưa có tập B độc lập/first-pass/phút sửa.

## Chạy lại

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$env:PYTHONPATH='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-structured-decoding-0113'
python -m unittest discover -s app -p 'test_*.py'
node --check app/ui/app.js
python app/app.py --data D:\Cutroom-new-workspace --no-browser
```

Model mode cần runtime/base/checkpoint tùy chọn đã cấu hình. Trong UI chọn một
recording, mở Script → Generate intro & demos; nhập promise, giữ source facts,
khóa demo trước khi thay intro. Bản cũ còn trong export history. Harness riêng
`headline_ui.py` và `headline_ui_fixed.py` lưu cả failed run lẫn recovery; không
chạy lại mù trên workspace có kết quả sẵn.
