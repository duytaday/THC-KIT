# Generative lab — kết quả thực tế và giới hạn

Đã train thật CogVideoX2B video-diffusion LoRA trên Kaggle riêng tư, độc lập
với adapter chọn quyết định dựng cũ. Không gọi một edit-selector là model sinh video.
V1 footage thật vẫn là luồng mặc định; không sinh người dẫn hoặc giọng.

- Base `zai-org/CogVideoX-2b`, revision
  `1137dacfc2c9c012bed6a0793f4ecf2ca8e7ba01`.
- 14 silent clips:12 train từ3 family,2 development-holdout từ1 family khác.
  Creator grouping chưa xác minh, nên không tuyên bố unseen-creator benchmark.
  Nguồn do user xác nhận sở hữu; không suy quyền phát hành lại footage.
- Hai TeslaT4, T5 thực tế `cuda:1/float16`.32optimizer steps thực sự áp dụng,
  training-only39,5956s, peakGPU0~7,0GB, weight-deltaL2=2,021911.
- Adapter SHA256
  `893fd28e0ec2223445e05e5a3467ddc3fdb2ea847acc63cf3a58e145fd071fe8`.
- Run đầu lỗi torchao không tương thích trước optimizer; log giữ nguyên.
  Worker mới loại dependency tùy chọn không dùng rồi chạy thành công.
- Inference mới qua UI→private Kaggle:720×480,17frames,8fps,40steps, cùng
  prompt/seed3407 cho baseline/candidate;413,117s toàn lượt inference.
  Receipt xác nhận `weights_loaded=true`, active adapter `talking-head-style`
  và đúng SHA trên. Tải đúng file, kiểm hash, full decode cả2MP4.

Baseline SHA `51de410f9c4d59d53f17b55491ac27e185db9c63e5259c1d0c66aa3756fcfcce`.
Candidate SHA `e7be6de2344a058ee471c4e50deea160197769ae0cb7fdb582f4f36f92bb2a45`.

**Chưa dùng cho khách.** Preview256px đầu bị mờ/khối. Inference720px nhận ra
laptop/timeline nhưng cả baseline lẫn candidate có chữ giống watermarkPOND5,
trái yêu cầu không có chữ/logo. Không xóa dấu đó để biến clip thành asset đã
được duyệt; giữ ở lab và đánh REVISE. Không có bằng chứng model tốt hơn hoặc
giảm thời gian sửa. Development denoising loss thấp hơn không đo mỹ thuật.

UI đã import compactZIP, gửi prompt+seed (không gửi customer recording), refresh
job COMPLETE, tạo editable illustration có disclosure AI và source passage.
Scene **chưa insert**, không thay hình/giọng trong master thật. API từ chối
adapter selector, zero-step receipt, ZIP traversal và adapter/preview sai hash.
Kaggle URL thực tế được lưu từ CLI để tránh nhầm slug, refresh/cache có tính
idempotent. Không lưu token trong workspace/repo. Package không kèm checkpoint.

Kết luận riêng: **train thật: có; load/inference thật: có; chất lượng tốt hơn:
chưa chứng minh; đáng chi phí cho khách: chưa đo**. Chi phí/quota chỉ đánh giá
khi có so mù tập chưa thấy, lỗi proof, cue giữ nguyên, phút sửa/phút thành phẩm
và chi phí/phút video được chấp nhận. Không đẩy thêm train lớn trong luồngV1.

Nguồn kỹ thuật đã tra cứu: [model card](https://huggingface.co/zai-org/CogVideoX-2b),
[Diffusers CogVideoX training](https://huggingface.co/docs/diffusers/training/cogvideox),
[finetrainers](https://github.com/huggingface/finetrainers).
