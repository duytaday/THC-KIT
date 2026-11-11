# Kết quả kiểm thử production contract — 11/11/2026

Đây là kết quả triển khai nền dùng lại cho các tập sau. Chưa phải nghiệm thu
chất lượng dựng theo reference hay chứng nhận model đã train/load qua app.

| Kiểm tra thực chạy | Kết quả |
|---|---|
| App unittest suite | 57/57 PASS |
| QC tools suite | 47/47 PASS |
| Reference lab suite | 39/39 PASS |
| Compile các module animation/trainer | PASS |
| Git diff whitespace | PASS |
| GPU từ nvidia-smi | NVIDIA GeForce RTX 3070 Ti Laptop GPU, 8192 MiB |
| FFmpeg encoder inventory | h264_nvenc có sẵn |
| Render footage thật + vector chữ | 5s, 1080×1920, 30fps, 150 decoded frames |
| Encoder từ stream tag MP4 | Lavc62.28.101 h264_nvenc |
| Full AV decode smoke | PASS, không lỗi decode |
| Loudness đo trên smoke đã xuất | −17.70 LUFS integrated; −1.67 dBTP |
| Xem/nghe | Đã xem thumbnail 270×480; chưa phát/xem toàn đoạn hoặc nghe. NEEDS_REVIEW. |

Smoke: `output/reference-training/animation-hook-smoke-v001/preview.mp4`, SHA256
`31bd199b499107affcf4ca70f0444366dc857a7255d2069d44ec6c8713b0829f`.
Đây là **rules storyboard**, có nhãn cần thu/căn lời; giọng từ footage thật,
không phải bản intro đã khớp lời và không thay thế master v035.

Master v035 kiểm lại SHA256 vẫn là
`ca15d2c90348ddfa33d46e2504516075689179f31e5c1d3729deffb745603c09`.

## Dữ liệu và model

Đã sửa đọc `training.source_sha256` từ intake cũ để gộp content family trước
split; dùng full hash làm source ID. Gate kiểm cả source group, ID và hash
giữa các split. RAG phải chứa đúng các hàng train, không chỉ ID trông hợp lệ.

Dataset thử nghiệm mới `output/reference-training/animation-spec-v004`:
29 file / 28 hash / 27 content families; 108 nhãn agent (72 train, 16 val,
20 test), **0 editor-confirmed**. Keyframe tự tái dựng không được gắn một
timecode reference chưa quan sát. Các mẫu này phục vụ kiểm pipeline, chưa là
ground truth cách dựng của reference. Trước đó token audit v003: tối đa1722
tokens/prompt+target, không mẫu nào vượt3072; không cắt cụt gold spec.

`train_motion.py` là trainer thử nghiệm cho spec, chưa chạy GPU training trong
lượt kiểm contract này. Chưa có checkpoint mới để công bố, chưa tích hợp chọn
adapter spec qua UI và chưa đo first-pass acceptance/phút sửa. Giữ adapter
production tắt; không coi kiểm thử rules là bằng chứng model thắng baseline.

## Chạy lại

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
# $py là interpreter Python 3 đã kiểm chứng trên máy đang dùng.
& $py -m unittest discover -s app -p 'test_*.py' -q
& $py -m unittest discover -s talking-head-qc/tools -p 'test_*.py' -q
& $py -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py' -q
& $py app/motion_learning.py check output/reference-training/animation-spec-v004
```

Thư mục output là dữ liệu local, không đóng gói footage/reference vào Git.
Đường dẫn tuyệt đối trên máy phát triển không trở thành default của người mua.
