# Flow reference và cách áp dụng vào tập hiện tại

Đã kiểm kê29 file/28 hash/27 content families; chưa xác minh creator độc lập.
Ba reference dưới đây được khảo sát toàn chiều dài bằng ASR tiếng Anh trên CUDA
và frame giải mã lấy mẫu. Không chứng nhận đã nghe hoặc xem chuyển động1×.
Các khoảng là phase windows để dựng thử; keyframe suy từ MP4 là ước lượng.
User đã xác nhận sở hữu corpus và cho phép thử nghiệm private.

| Reference / SHA256 | Flow quan sát và timecode | Dùng lại / giới hạn |
|---|---|---|
| `…0a4a.mp4` · `a10c694f20fb32f31d6378571845db59004bd4139c3b2c9c0188350c4637e5bc` | 00:00–00:04 lời hứa + mặt; 00:04–00:13 cửa sổ thao tác; 00:13–00:16 kết quả rồi mặt; 00:16–00:23 ví dụ tiếp; 00:24–00:28 ngữ cảnh giá; 00:28–00:32,7 CTA | Học vòng câu nói → thao tác → kết quả → trở về người dẫn. Không sao chép lời hứa hoặc xác nhận tính đúng của giá. |
| `…1092.mp4` · `6209825458c19b4df43900fc07437e57115f4b98ddb0faed4f6157439322196e` | 00:00–00:00,67 thẻ Gemini xoay/bay vào; khoảng00:00,70 thẻ chuyển sang ô B và giữ; các mục tiếp khoảng00:06,64 /00:09,84 /00:21,54 /00:28,96 /00:32,58 /00:36,12 /00:42,56 /00:46,42 /00:49,70 /00:53 /00:58,56 /01:05,58; CTA01:09,14–01:10,8 | Học một mục được nhấn rồi về trạng thái ổn định. Không thêm tier/ranking vào lời Recordly vốn không chấm hạng. Nhảy vị trí ở khoảng0,70s là quan sát trên bản giải mã30fps, không phải easing/project gốc. |
| `…2c95.mp4` · `b7660ade50da31851a6896b993db1f5b5ed3fd8e95f6592e8e92bbfec4f7defc` | Khoảng00:00–00:27 lặp tên kỹ thuật → ảnh kết quả → mặt, mỗi cụm3–4s; CTA00:27–00:31,6 | Giữ mỗi ý có payoff riêng. Header nói5 nhưng ASR/hình gợi ý tới7 kỹ thuật: cần editor xác minh; không coi sai lệch promise/payoff này là chuẩn tốt để train. |

Các bằng chứng local nằm trong `output/reference-training/flow-analysis-v001/`:
source receipt, transcript draft và frame grids. Riêng thẻ tier-list được kiểm
từng frame của excerpt1,5s sau khi crop; không suy ra SFX từ hình hoặc mixed audio.

## Áp dụng có nguồn vào pilot Recordly

Pilot là đoạn20,466667s từ vlog hiện tại, không phải bản vlog118,1s hoàn chỉnh.
Source host SHA `c56551f1af3ef7dbaa8f69f9264012bf3173b2b07fee4d61757e2e25df13d03a`.
Master UI mới: export`ca907cb91a844fc8ab3f2f441eec5803`,
SHA `26dd9c4ccc319a5d5bc3c6f7247674583ca9c743d5beebd3bb38d80cf87adf9d`.

| Lựa chọn của mình | Nguồn ảnh hưởng | Mốc trong pilot / footage thật |
|---|---|---|
| Giới thiệu tên trước khi vào chi tiết | Reference tier-list00:00–00:00,70; house rule không copy ranking | Lời giới thiệu Recordly00:00,03–00:01,83; thẻ vào khoảng00:00,433. Hai thẻ native là proposal còn cần duyệt hierarchy. |
| Cho thấy vị trí rồi mới click | Reference headshot00:04–00:13; actual contact lấy từ capture hiện tại | B-roll bắt đầu00:05,5667; nút Releases được thấy trước contact; click tại00:07,0333/frame211, khớp ASR “đây”00:07,04 trong giới hạn frame. Screen-source contact01,476s; capture gốc02:49,476. |
| Chỉ báo kết quả sau khi nó có thật | Reference headshot00:13–00:16 | Trang Recordlyv1.4.0 hiện tại master00:10,0667/frame302; source proof04,5s. Giữ đến00:16,2667 để đọc, rồi trở lại mặt. Chime có isolated peak đúng frame302; audibility trong mix vẫn chưa xác minh. |
| Giữ toàn câu và phụ đề | Quy tắc giọng thật của kit; không lấy nhịp nói reference ép sang tiếng Việt | Audio/caption timeline giữ nguyên; sửa CTA theo câu trả lời trực tiếp của user. Sample phone360px đã kiểm nút, contact và tên bản release. Chưa nghe toàn master. |

Ảnh hưởng reference trong bảng là **diễn giải do agent**, ghi lại để editor xem
và sửa. Không khẳng định model đã tự học các khoảng này: hai pilot LoRA spec
đang dùng fixtures/rules distillation, số reference media đưa vào loss là0.

## Animation library

- Hai native templates đã lưu từ scene intro/demo; khi dùng lại phải thay lời,
  anchor và proof theo tập mới. Preview silent không mang giọng cũ sang tập mới.
- Excerpt đầu `f285806fc1894374851fc20b39bcf27e` giữ nguyên, REVISE:
  khoảng00:00,067–00:00,667 bị crop mất mép trên thẻ.
- Excerpt mới `74284f50a3c3472a99c2619b9220a67c`, source00:00–00:01,5,
  crop[1080,1036,0,884], SHA
  `50d20a2b03ded2afcb1806131a4abc52d441499a6d6e44eb211948350e298956`:
  đã kiểm45 frame gồm frame0 riêng +44 tile. Không thấy watermark không mong
  muốn, không mất mép trên thẻ; giữ chuyển động đi vào từ mép trái vốn có.
  Chỉ nhập làm illustration. Gemini, B-tier, logo app và mép áo đã bake vào hình;
  chúng không biến thành tên repo/text sửa được hoặc proof cho lượt chạy mới.

## Phần còn thiếu

Chưa có review nghe1×, user chọn bố cục/mức animation, hay first-pass/repair-time
metrics. Lời00:16,35–00:18,49 nói về zoom Recordly: capture này chủ yếu chứng
minh click→trang đích, chưa đủ chứng minh chỉnh zoom trong editor Recordly.
Cần quay riêng đúng thao tác đó trước khi gọi là demo đầy đủ tính năng đã nói.
Không dùng excerpt tham chiếu để che khoảng thiếu này.
