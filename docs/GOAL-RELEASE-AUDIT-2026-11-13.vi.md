# Audit mục tiêu Talking Head Cutroom — 13/11/2026

Mục tiêu toàn bộ **chưa đạt**. Latest prototype là export
`7516aea3a68f4a53a27714c3337a62a6`, SHA256
`5ac2b54d41a75896df62e6d305a27320a1cfe534d7a1dda6ca33e8bf586db0b7`,
trạng thái **REVISE**. Không thu hẹp mục tiêu thành native pass, loss giảm hoặc
chạy EXE thành công. Bản này là một biến thể cỡ chữ để user đánh giá.

| Yêu cầu | Bằng chứng hiện tại | Kết luận |
|---|---|---|
| Reference có quyền, grouping và train-only RAG | User xác nhận sở hữu;29 files/28 hashes;group conservative;48 train rows riêng validation;source/PTS receipts | Có intake/split;creator độc lập và human gold chưa xác minh |
| Train thật Kaggle và reload | Version1 COMPLETE;64 steps;weight update và adapter hash f4ded53f…;worker base/tuned nạp đúng, adapter inactive/active | Đạt phần train/load, không chứng minh style gain |
| Intro/demo sửa được trong normal UI | Artifact JSON/history;source-bound Recordly anchors;manual v003 font-only qua Controls;locked demo giữ nguyên | Đạt đường đi UI đã kiểm;scene còn cần editorial judgment |
| Không đổi nghĩa/lời/caption/branding và giữ cut cũ | New/old full PCM,stems,SRT,ASS dialogue cùng hash;settings/locked record không đổi;sáu masters/v035/checkpoints giữ hash | Đạt các invariant đã đo;nghe từ/cut thật còn thiếu |
| Layout/motion/text/readable holds | Native guards;sample phone frames;intro v003 đủ sáu text;validator vẫn từ chối nhiều case model | Có diagnostic, chưa đạt reference fidelity theo người duyệt |
| Proof thật | Recordly contact/result anchors và frames có evidence;FFmpeg frame35.500 còn là GitHub page | Chưa đạt;phải capture preview thật và xuất version mới |
| SFX và mix | Isolated cue peaks đúng frame;full master−16,08 LUFS/−1,65 dBTP;final-mix alignment/hearing còn unverified | Chưa đạt sign-off nghe;không suy từ peak/PCM rằng mọi từ nghe rõ |
| Full-video rules/base/tuned so mù trên tập chưa dùng | Tập5repo là development/regression;base/tuned cùng MP4;component validation đã dùng;chưa có tập B raw mới | Chưa đạt đánh giá độc lập hoặc cải thiện fine-tune |
| First-pass acceptance, phút sửa và viewer answers | Gallery/UI chuẩn bị;0hook answers,0human-confirmed corrections;metrics null | Chưa đo, không điền số giả hoặc dùng thời gian agent/optimizer thay editor |
| Chỉ admit clip được kiểm watermark | Không admit các fixture STORYBOARD hoặc master thử vào usable library;library current0 | Không admit sai;không claim có asset mới được duyệt |
| Exact-master approval | Decode3543frames;hash/encoder/audio/captions và reviewer frame-only có record;0full1×hearing/watch sign-off | REVISE, tuyệt đối chưa READY |

## Phụ thuộc bên ngoài còn thiếu

Các điều kiện này lặp lại ở lượt Recordly/dev20, dev21 và lượt typography v003.
Các lượt ấy có tiến bộ kỹ thuật thật; sau các sửa/preview đã hoàn tất, phần
nghiệm thu còn lại cần input hoặc thay đổi trạng thái bên ngoài:

1. Recordly live HUD vẫn chọn Facebook. Computer Use đã lỗi activate và recovery;
   lần đọc lại cuối vẫn cùng source. Chưa Record. Cần user chọn đúng cửa sổ
   **FFmpeg preview · 5 repo GitHub – Google Chrome**, chưa bấm Record. Khi đổi
   xong, agent kiểm mic/webcam/system audio rồi quay thao tác, export và sửa cut.
2. Thư mục take user cung cấp vẫn chỉ có `1.mp4` (37.593.117 bytes). Chưa có raw
   tập B mới để kiểm full-video generalization. References đã dựng không thay
   thế raw/script/proof của một episode mới. Tập5repo sửa rồi đưa train/RAG chỉ
   còn là regression, không biến thành unseen vì đổi tên file.
3. Không có người có khả năng nghe đã xem/nghe exact master ở1×, chấm fidelity,
   trả lời quiz và ghi phút sửa thực. Agent chỉ kiểm decoded frames/số đo;
   không thể tự ký thay người nghe hoặc tự suy ra lựa chọn style của user.

Không còn train/render handle đang chạy cần chờ trong lượt này: Kaggle COMPLETE;
full render và pair-builder đều terminal thành công. Không tạo job mới chỉ để
lấp khoảng thiếu feedback. Không promote model/preset hay xuất READY.

## Điều kiện tiếp tục và kết thúc

- Có nguồn Recordly đúng: capture→scene mới→new master→decode/QC→xem/nghe.
- Có tập B: freeze dữ liệu chưa dùng;so rules/base/tuned cùng RAG,source,renderer
  và mức nghe,giữ raw failure/repair;không trộn tập này vào train trước chấm.
- Có reviewer: chọn treatment trên cặp có audio giống nhau và cùng timebase;
  lưu timecodes,first-pass và thời gian sửa thật. Nếu dùng correction để train,
  chuyển nó thành development và chọn holdout mới cho lần chứng minh kế tiếp.
- Chỉ kết thúc mục tiêu khi đầy đủ toàn bộ yêu cầu,desired fidelity có bằng chứng
  và exact master được duyệt. Các câu hỏi hiểu biết trong
  `SESSION-UNDERSTANDING.md` còn chờ trả lời, không được tự đánh mastered.
