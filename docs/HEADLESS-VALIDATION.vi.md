# Nghiệm thu headless — 2026-11-16

Phạm vi: mục 12, native rules + local retrieval, không cần UI/LoRA. Kiểm tra từ public CLI thực, gọi các tiến trình Python riêng; không gọi trực tiếp renderer thay cho CLI.

| Kiểm tra đã chạy | Kết quả quan sát |
|---|---|
| Hồi quy app | 392 ca: 379 đạt, 13 skipped theo điều kiện môi trường; UTF-8 trên Windows |
| Batch UI đóng | 3 recording có narration tổng hợp + SRT; xuất đủ 3 master, mỗi master 12 s, 1080×1920, 30 fps, 360 frames; full AV decode đạt |
| Script / demo mapping | Manifest dùng đường dẫn Unicode/tương đối; hai `capture.mp4` khác action được ghép đúng Export / Add subtitles |
| Đối chiếu pixel độc lập | NCC đúng nguồn 0,9957 / 0,9953; sai nguồn khoảng 0,51; kết quả hiện đúng frame 150 |
| Thiếu Save demo | Tập 3 xuất draft có nhãn MINH HỌA; pickup ghi nguyên câu và yêu cầu target → action → readable result; batch tiếp tục |
| A/B/C sau batch | Hook/demo/CTA đều có 3 variant khác nhau; decoded PCM giống nhau trong từng visual comparison; UI mở được link và phát đồng bộ 1× |
| Dừng/chạy tiếp | Stop sau khi hoàn tất tập 1, process kết thúc; process mới status/resume giữ nguyên export ID/hash tập 1 và không tạo logical export trùng |
| Sửa riêng tập 2 | Scoped cue “Add subtitles”, source/master 3–9 s; music stem giảm đo được 2,999 dB tại 4–5 s, 0 dB tại 1–2 và 10–11 s; voice stem không đổi; tập 1/3 và preset không đổi |
| Retry revision | Lặp directive trước và sau export vẫn chỉ một logical change; ID trùng payload khác bị từ chối |
| Dữ liệu CLI/UI | Files / Library / Outputs hiện cùng workspace; component fixture lưu từ Library xuất hiện trong `cli.py library` khi UI đang giữ OS lock |
| Các kiểm tra khác | JavaScript syntax, release-module allowlist, skill validator và staged diff whitespace đạt |

Fixture chứa test pattern, Windows synthetic speech và software UI mô phỏng có nhãn; không có diễn viên/khách hàng thật. Các mốc capture là dữ liệu fixture đã biết, không phải engine tự hiểu và chứng minh mọi claim. Đây là kiểm tra vận hành, correspondence và scope. Chưa đánh giá chất lượng sáng tạo, retention hoặc khả năng chuyển sang ba tập người dùng thật.

Không có training/model promotion/provider call hay provider prompt-cache hit mới. Prefix ổn định chỉ được ghi là prefix hash. Không tạo human approval. **Mọi master vẫn NEEDS_REVIEW; listening UNVERIFIED**, kể cả hai tập không thiếu demo. Tập thiếu demo còn cần pickup trước release. Clean-Windows installer, mid-encode power-loss recovery, native OpenShot/external generation và readiness UI đầy đủ vẫn chưa được nghiệm thu trong lượt này.

Thực thi lại theo [hướng dẫn CLI](HEADLESS-AUTO-EDIT.vi.md). Local handoff giữ exact argv, master/preview paths, preset/component receipts, SHA, progress và evaluation JSON. Chỉ source, tests, docs và preset/template mẫu được xuất bản; workspace/media/model riêng không nằm trong commit.
