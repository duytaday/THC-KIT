# Motion planner v006 — nền chữ theo từng dòng

Giả thuyết trước khi sửa nằm ở
`output/reference-training/reference-spec-v006/protocol.json`: reference có nền
trắng ôm từng dòng, trong khi thẻ native cũ luôn bao cả khối. Chỉ thay cách dựng
nền, giữ lời, nguồn, font, timing và audio. Đây là thử nghiệm component; không
phải kết quả benchmark chất lượng toàn tập.

## Kit và cách dùng

Source dev12 có `box_style: panel|lines` trên text object, mặc định `panel`.
Trong **Edit animation spec → Text background**, chọn **Separate background per
line**. Font/glyph được libass đo để nền ngắn theo từng dòng; không ước lượng
chiều rộng bằng số ký tự. Text vẫn dùng cùng quy tắc wrap, source anchors,
replacement rectangles, keyframes, theme và readable hold. Không áp dụng nền chữ
cho marker nút/click/result. Manual edit sống qua regenerate; template và recipe
JSON giữ trường này để sửa tiếp. Không thêm pixel/reference asset vào bản dựng.

Đã kiểm actual decoded frame: dòng ngắn có nền ngắn riêng, giữ nguyên dấu Việt;
native validator và grammar đều chấp nhận trường mới.229app tests PASS, có test
libass thật, manual override và gói Kaggle phẳng. Legacy default ASS được so với
commit6f59f4b, giống từng byte trên case có cả emphasis/fade. Prompt8 được thêm
riêng; prompt7 của v005 và checkpoint cũ không bị viết lại.

## Pilot qua batch-editor UI

Nguồn: excerpt thật của `5-repo-voice-first.mkv`,12,566667–19,166667s, giữ trọn
câu giới thiệu năm repo theo timeline nguồn hiện có. Không phải tập mới unseen.
Hai bản được tạo qua UI, B chỉ đổi Text background; không thêm animation suy ra
vào một headline reference vốn đã hiện tĩnh tại đầu interval.

| Bản | Export ID | SHA256 |
|---|---|---|
|Panel|3f10c85b7ee54999993c722c2532d096|66d951319feae73aa8a072bc1b7c0718630893ad76b19fb43c291a277d87bb72|
|Lines|cb8f7d83c4284480bd9bf7998ea1ba06|af6fc9e02b77aab6301eed8dc54e827895664c9761c36c2118e90a1e7be835ff|

Cả hai6,6s/198frames,1080×1920/30,`h264_nvenc`, full decode PASS;
−16,43LUFS/−1,87dBTP. Voice WAV giống hash9946834b… và SRT694ae226…;
UI không có page error. Pilot đầu được giữ; kiểm fade tiếp theo phát hiện nền hai dòng chồng alpha ở vùng giao. Đã giảm padding theo font và kiểm decoded fade-in/hold/fade-out với đúng ScaledBorderAndShadow. Sẽ kiểm bản package mới riêng; không gán kết quả package cho pilot cũ. Đã xem selected phone frames0,2/1/3/5s; chưa nghe toàn
mix hoặc duyệt toàn tập1×. Hai bản vẫn **NEEDS_REVIEW**. Đây không phải video
hoàn chỉnh thay v035. Evidence ở`output/reference-training/reference-spec-v006/ui-v001/`.

## Nhãn và lượt Kaggle

Dataset`ece1a6b469368d225d2d9fb5e4f3954fa7fdf9fd2425aaf78642898dcd33ac8b`:
33train/33validation/10regression,76rows. Bảy intro đã đối chiếu source4/6/12/
14/20/21/22 được thêm `box_style=lines`; không đổi timing/word/font/geometry.
Không có source mới, không có human gold mới. Independent family count chưa xác
minh; số file/labels không được dùng thay số tập độc lập. Train-only RAG giữ nguyên
ranh giới. Max2808/3072tokens, không truncate. Ngân sách64optimizer steps từ fresh
pinned Qwen base; không resume adapter v005.

Private kernel:`duytruyenthong/talking-head-spec-training-ece1a6b46936`.
Hai lần đầu lỗi trước optimizer: CLI bỏ qua thư mục `engine`; bản ZIP kế tiếp bị
Kaggle tự giải nén thành `engine/engine/…`, mất đường dẫn bootstrap chờ. Đã giữ log
lỗi và sửa owning helper`prepare_motion_kaggle.py` dùng hai file phẳng`engine.py`
và`cutroom_media.py`, kiểm import trong Python isolated process. Dataset listing
thật đã xác nhận hai file đó trước kernel version3. Không xóa version/dataset cũ.
Version3 đã **COMPLETE**:64optimizer steps thật,33unique applied rows,76,422s
train trên`cuda:0`/một TeslaT4 trong máy2T4. Peak8.502.062.080bytes,
weight-update L2=2,524520; validation loss0,829711→0,809266. Raw generation trên
4case development/regression: base0/4, tuned1/4; intro vẫn0/2. Không dùng các số
này thay independent whole-video benchmark.

Adapter SHA256:
`b5c78d754f7709fdada6a46417c0e280194dc68fd620952c3f06f432e6e36d6c`.
Đã import vào workspace kiểm gói và fresh worker local`cuda:0` nạp lại base
adapter inactive / tuned adapter active. Cùng context, prompt8, decoder và train-
only RAG. Cả hai intro previews render qua UI, không cần compiler repair; MP4
cùng SHA36458bbd… và đều chọn `panel`. Excerpt chỉ nói số lượng repo nên
storyboard còn placeholder tên; không coi đó là năm demo hoàn chỉnh. Nhãn lines
mới thuộc host, route intro hiện yêu cầu full: cần kiểm cách chọn treatment phù
hợp trước khi kết luận train thêm sẽ tự giải quyết. Model vẫn **INCONCLUSIVE**.

## Gói Windows đã kiểm riêng

Internal dev12:source commit013c253/source_dirty=false, embeddedPython3.12.10.
ZIP17.652.928bytes/152files, SHA256
`98eb2b09abc97e2f78f27b2963679f26f5f66511f0d563814523897322f99595`.
Gói ở`D:\.codex\workspaces\talking-head-support\releases\Talking Head Cutroom 0.14.0-dev12`.
Build đầu dùng nhầm starter thiếu Cutroom.exe, được giữ riêng; build sau dùng
starter gốc trên D. Native launcher/Windows sạch chưa thử; grant của starter còn
cần chốt trước public distribution. Không thay instance đang chạy của người dùng.

Đã smoke5s qua backend gói, footage thật +caption +lines:150frames/NVENC/full
decode. Smoke dùng level nguồn scene-preview (−23,67LUFS/−9,83dBTP), không phải
master mix pass. Sau đó xuất A/B qua batch UI của chính gói, port59514:

|Bản sau sửa fade|Export ID|SHA256|
|---|---|---|
|A panel|18ecc0a291d5426d888a2c706cffaf2a|66d951319feae73aa8a072bc1b7c0718630893ad76b19fb43c291a277d87bb72|
|B lines|fd10144e053f4e0bab8ce41a35976f65|ce9893bc6d7ef62acb9e2a79679d36e76ddaf96eeec90623e0089731a8d730e4|

Cả hai198frames/1080×1920/30, NVENC/full decode, −16,43LUFS/−1,87dBTP;
voice/SRT cùng hash. A trùng byte với panel cũ. Before/after cùng nguồn
12,566667–19,166667 → master0–6,6s. Đã xem phone frames0,2/1/3/5s trên B mới:
title/dấu Việt đầy đủ ở các frame đó, chữ trên tóc và caption dưới mặt.
Chưa nghe/certify toàn master1×; giữ **NEEDS_REVIEW**.

Harness phục hồi sau response body bị Chrome evict, modal đã đóng và API snapshot
bỏ private folder. Đã kiểm stored state/hash/dependencies/candidate và base run
hoàn tất, chỉ gọi tuned chưa chạy. Không rerender/reimport do lỗi quan sát. Kết
quả **PASS_AFTER_HARNESS_RECOVERY**, không phải cold-run pass; app0page errors.
Evidence:`packaged-ui-v001/results.json`, `packaged-smoke.json`,
`actual-results-v001.json`. Không admit clip vào usable library; default giữ nguyên.
Download all-output bị dừng khi đang kéo2,88GBbase cache; chỉ tải adapter/receipt
bằng file-pattern, không restart kernel.

## Chạy lại và rollback

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python app/app.py --data D:\Cutroom-new-workspace --no-browser
python app/prepare_motion_kaggle.py D:\dataset --out D:\NEW-package --owner YOUR_OWNER --steps 64
kaggle kernels status duytruyenthong/talking-head-spec-training-ece1a6b46936
kaggle kernels output duytruyenthong/talking-head-spec-training-ece1a6b46936 -p D:\NEW-model-output --file-pattern 'talking-head-motion-spec/(provenance.json|evaluation.json|predictions.json|retrieval-train-only.json|motion-spec-package.zip|adapter/[^/]+)$' --page-size 200
```

Không gửi raw media lên Kaggle. Giữ v005 labels/checkpoint/master và commit6f59f4b
để rollback. Default sản phẩm vẫn rules, model chưa production-approved. Còn cần
human watch/listen, lựa chọn style, first-cut acceptance, phút sửa thực tế và tập B
độc lập trước quality promotion; không dùng pilot này thay bằng chứng đó.
