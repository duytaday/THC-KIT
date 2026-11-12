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
Lượt version3 đã được xác nhận RUNNING; chưa coi là train thành công khi chưa có
terminal receipt, optimizer steps và weight hash. Chi tiết cuối ghi vào receipt
riêng trong output trước khi import/reload candidate.

## Chạy lại và rollback

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python app/app.py --data D:\Cutroom-new-workspace --no-browser
python app/prepare_motion_kaggle.py D:\dataset --out D:\NEW-package --owner YOUR_OWNER --steps 64
```

Không gửi raw media lên Kaggle. Giữ v005 labels/checkpoint/master và commit6f59f4b
để rollback. Default sản phẩm vẫn rules, model chưa production-approved. Còn cần
human watch/listen, lựa chọn style, first-cut acceptance, phút sửa thực tế và tập B
độc lập trước quality promotion; không dùng pilot này thay bằng chứng đó.
