# Talking Head Cutroom — bắt đầu trong một trang

Bản nội bộ Windows x64. Giải nén toàn bộ ZIP vào thư mục có quyền ghi trên D,
mở **Talking Head Cutroom.exe**. Giữ runtime và app cạnh EXE. Project, bản xuất,
cache nằm trong workspace và .cache cạnh EXE. Chưa chứng nhận máy Windows sạch.

1. Chọn **Add recordings** để thêm bản quay. Chọn recording cần dựng; **Make
   first cut** nhận niche dạng chữ thường, hoặc để trống. Story recipe và visual
   style là hai lựa chọn độc lập. Mặc định là video dọc1080×1920/30fps.
2. Lần đầu cần FFmpeg6.1+ và FFprobe: dùng **Encoder setup**, hoặc đặt hai EXE
   phù hợp vào bin cạnh launcher rồi **Check again** trong Settings. Download của
   kit lưu bản pin8.1.2 vào workspace/tools, khoảng104MB; không cài vào hệ thống.
   Không cần GPU;
   máy tương thích ưu tiên NVENC, bước không hỗ trợ quay về CPU và lưu log.
3. Nhận dạng giọng là tùy chọn: **Download local captions** hiện nơi lưu và tiến
   trình, tải model đa ngôn ngữ small khoảng486MB cùng thư viện. Ghi âm không được
   upload. Sau khi tải, dùng lại offline. Hoặc **Attach a prepared TXT / SRT**;
   TXT ước lượng timing, SRT giữ timing từng cụm, cần nghe đối chiếu với take.
4. **Usable B-roll** là footage được phép đưa vào video. **Style reference** chỉ
   dùng quan sát nhịp, không tự xuất hiện trong hình/tiếng. Với tên file bình thường,
   chọn **Label / assign to recording**, mô tả cảnh và kiểm preview. Gợi ý chưa tự
   chèn: xác nhận hoặc đặt tay trong Cutaways; khai target/contact/result khi có.
5. Đọc brief và các đoạn không chắc. Bản đầu giữ các câu/take còn phân vân để
   tránh mất nghĩa. Nghe câu trọn vẹn trước khi trim; có **Restore entire take**.
   Sửa phụ đề trong Script; thay timing SRT được giữ. Logo trong Style, motion,
   từng sound cue và music độc lập. Batch chỉ áp trường bạn đã thay; scene khóa giữ.
6. Khi có footage kết quả thật đã gắn result anchor, **Compare4-second openings**
   dựng thử host-first/proof-first cùng audio, chỉ đoạn mở đầu. Lựa chọn là đề xuất
   biên tập; chưa có dữ liệu hiệu quả người xem. Thiếu proof thì giữ người dẫn.
7. **Queue selected** xuất phiên bản mới. Trong Exports tải MP4, SRT, Edit plan,
   cue sheet và QC. Các cut trước vẫn còn. Project tự lưu vào workspace; đóng/mở
   lại để tiếp tục. Nếu dừng giữa render, queue lại: dùng các stage cache còn hợp lệ.
   Đừng đóng trong lúc đang upload nguồn; chỉ bản import hoàn tất mới được nhận.

Technical checks chưa phải duyệt nội dung. Xem/nghe đúng MP4 ở1× và kích thước
điện thoại, kiểm tiếng cuối, phụ đề, target → action → result, mức mix và CTA.
Chưa xem/nghe đủ: **NEEDS_REVIEW**. Lỗi xác nhận: **REVISE**, sửa cut mới. Chỉ
duyệt **READY** sau khi sáu gate có chứng cứ và người duyệt cuối ký exact master.

Example đi kèm là hình/test signal tổng hợp, không có người nói. Import MP4 và
SRT cùng tên để thử encoder. Nó không chứng minh ASR hoặc chất lượng dựng thật.
Model fine-tune, animation/style adapters và Kaggle là các tính năng thử nghiệm,
cần runtime riêng; không bắt buộc cho đường dựng cơ bản. Chưa bật model cho khách.

Nếu lỗi: xem stage cạnh recording và workspace/cutroom.log, .cache/launch-error.txt.
Giữ nguồn và bản xuất cũ. Không xóa workspace để thử lại. Quyền phân phối starter
chưa xác nhận nên gói này dùng nội bộ; việc xuất bản do chủ sản phẩm quyết định.
