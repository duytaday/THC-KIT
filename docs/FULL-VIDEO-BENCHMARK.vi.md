# Benchmark Talking Head Cutroom: từ reference đến video hoàn chỉnh

Chỉ kết luận kit dựng đúng hướng khi một tập mới đạt brief và QC, người xem
hiểu được hành động/kết quả, và editor mất ít công sửa hơn. Train loss, JSON
hợp lệ, số hiệu ứng hoặc số skill cài được chỉ là chẩn đoán từng phần.

## Prompt đã chốt để thực thi

> Dựng benchmark ở cấp **toàn tập** từ footage thật. Dùng các reference đã
> được phép để lập rubric flow có source hash, timecode và giới hạn quan sát.
> Giữ script, ngành nghề, branding và proof của từng khách độc lập. So rules,
> base + RAG và tuned + cùng RAG qua cùng timeline/renderer/font/mức nghe.
> Chấm sáu gate của exact MP4, flow đầu–giữa–cuối, mức hiểu của người xem,
> tỷ lệ giữ nguyên lần đầu và phút sửa/phút video. Giữ lại cả lần model bị
> từ chối; không thay rules rồi tính là model thành công. Đưa sửa đổi đã duyệt
> của tập development vào dataset mới; test cố định không đi vào train/RAG.
> Chưa xem/nghe thì để pending. Giữ mọi bản cũ và báo cả kết quả xấu.

## Chuẩn chấm

Protocol chạy được nằm ở `app/benchmarks/full-video-v1.json`. Đây là các mục
tiêu kỹ thuật ban đầu của kit, có thể đổi bằng protocol mới trước lượt đo.
Không có một điểm trung bình để bù cho sai nghĩa, thiếu demo hoặc mất đầu chữ.

| Nhóm | Đơn vị / điều kiện | Mục tiêu pilot |
|---|---|---|
| An toàn giao bản dựng | 6 gate A–F; brief, captions, timeline, dependencies và MP4 có hash | Không còn lỗi nghiêm trọng; đủ bằng chứng xem/nghe master1× |
| Đủ nội dung | Mỗi demo đã hứa có target → thao tác → kết quả đọc được; CTA thật | Tất cả beats; không lấy một demo thay năm repo |
| Flow theo reference | Opening, progression, handoff demo, readable hold, motion/type, ending | Editor chấm 1–5 kèm mốc reference và master; median hướng tới ≥4 |
| Người xem hiểu | Câu hỏi ẩn đáp án: bấm nút nào, thay đổi gì, chữ nào chưa kịp đọc | Hướng tới ≥90% câu đúng; báo số câu chưa kiểm riêng |
| Giữ bản đầu | Tập hoàn chỉnh được giữ nguyên / tập hoàn chỉnh đã duyệt | Hướng tới ≥80%; bản bị từ chối vẫn thuộc mẫu số |
| Công sửa | Phút editor **đang sửa**, không tính chờ render, / phút master cuối | Hướng tới ≤1; candidate hướng tới giảm20% so cùng tập baseline |
| Kỹ thuật | Full AV decode; output đã yêu cầu; frame count±1; −16LUFS±2; TP≤−1dBTP | Không lỗi; SFX sharp trong±1frame, captions bắt đầu với±150ms |
| Chi phí / vận hành | Wall time, actual device/encoder, render/model failures; UI không kẹt | Báo số đo; không suy giá từ thời gian hoặc số GPU hiện diện |

Tối thiểu10 tập unseen ghép cặp và3 group độc lập đã xác minh là **floor thử
nghiệm của kit**, chưa phải tính power hay đảm bảo tổng quát hóa. CI bootstrap
95% dùng group làm cluster, tập làm đơn vị so sánh, không coi10 cảnh trong
một vlog là10 tập. Mục tiêu80%/90%/20% là house targets, không gán cho một
nghiên cứu bên ngoài. Nếu chưa đủ mẫu, CI và kết luận model tốt hơn để `null`.

## Dùng reference đúng phạm vi

Reference định nghĩa cách giải thích: lời hứa → vị trí → thao tác → kết quả →
quay về người dẫn → CTA. Mỗi lựa chọn ghi `observed`, `inferred_to_test` hoặc
`house_rule`; một ảnh không xác nhận easing/SFX. Số scene changes là proxy có
thể bị sai bởi gesture hoặc bỏ sót animation trong cùng shot, không phải điểm
chất lượng. So theo nhịp/cụm ý; không kéo tiếng Việt cho bằng duration clip Anh.

Kho hiện kiểm kê29 file/28 hash khác nhau. Benchmark đầu dùng3 short được
khảo sát toàn chiều dài, kèm transcript draft và decoded frames; không gọi đó
là28 reference đã nghe. Bộ30 short user dự định bổ sung sẽ có inventory mới.
Tên tải Facebook chưa chứng minh creator độc lập: các clip trong collection
được giữ cùng group. Vlog “5 repo” đã được sửa nhiều lần là **development**.
Nó được dùng regression, không được quảng cáo là bài thi mới chưa từng thấy.

Giữ cùng nguồn, EDL, proof, renderer, caption treatment, style, music; chỉ đổi
planner trong ba arm. Hai model arm có cùng prompt/version và train-only RAG.
Loudness playback chênh >0,5LU không được gọi matched. Index xem mù giữ nguyên
bytes master; nếu tạo audition normalize riêng, phải ghi hash và đo lại bản đó.

## Hooks, workflow và skills đang nối vào pipeline

| Bước / hook | Mã / skill | Đầu ra và failure thật |
|---|---|---|
| Import / intake | `workspace.import_asset`, `speech.py`; `talking-head-edit` | Probe/hash, script của đúng take; lỗi input được báo riêng |
| Voice-first | Local faster-whisper, EDL/cut map | Giọng thật, qualifier và cuối chữ giữ lại; ASR không giả làm đã nghe |
| Reference → plan | `reference_motion.py`, `storyboard.py`; reference-flow skill | Nhãn có nguồn, ba hook/cụm ý, proof đúng repo; thiếu thì pickup |
| Native animation | `motion_specs`, `motion_policy`, `motion_hooks.before_render` | Spec dữ liệu qua validator; source anchors/locks bất biến; lỗi model lưu attempt |
| Render | `engine.edit`, `ffmpeg-skill`; optional HyperFrames/Remotion | NVENC/CPU receipt; một voice/caption bus; scene preview không chịu LUFS toàn chương trình |
| Master pre/post | `qc_hook before-render/after-render`, `qc_bridge` | Bounds/dependencies, decode/loudness/cues trên exact MP4; fail không thành READY |
| Benchmark full video | Exports → **Benchmark full videos**, `video_benchmark.py` | Freeze exports, rubric, review mù phone360px, gates, quiz, active repair timer |
| Revision / learning | Scene versions, corrections, `video_benchmark feedback/merge-feedback` | Cặp trước/sau được editor duyệt và có trong master; test corrections bị quarantine |
| Trước release | `qc_hook release` + người duyệt cuối | Duyệt exact master hiện hành; benchmark không tự cấp READY |

Giữ `talking-head-edit` làm entry point; không cần thêm một agent framework.
`talking-head-editor` bổ sung diagnostics/cut và graphics; HyperFrames/Remotion
là adapter hình; `video-shotcraft` dùng cho cảnh demo sản phẩm có nguồn thật;
Recordly ghi thao tác Computer Use. CapCut/MoneyPrinterTurbo là bước tùy chọn.
Trạng thái từng adapter và giới hạn đã render nằm trong
`docs/VIDEO-SKILL-INTEGRATION-RESULTS.vi.md`. Không bật cả catalog thành mặc định;
composition đã có voice/caption không nhận thêm lớp thứ hai.

## Chạy và lưu feedback

Trong UI chọn Exports → Benchmark full videos → các bản cùng tập → reference
phù hợp → Measure. Trang review dùng video360px, tên preset ẩn, thứ tự đảo;
reviewer nhập từng gate, các mốc và câu trả lời. Người không có audio để phần
nghe chưa kiểm. Lưu review tạo version mới trên D, không sửa review cũ.

Developer commands từ checkout root:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python app/video_benchmark.py run CONFIG.json --out NEW_RUN
python app/video_benchmark.py score NEW_RUN --review REVIEW.json --out NEW_SCORE
python app/video_benchmark.py feedback NEW_RUN --review REVIEW.json --workspace WORKSPACE --sources SOURCE_REGISTRY.json --out NEW_PAIRS
python app/video_benchmark.py merge-feedback FROZEN_DATASET --pairs NEW_PAIRS/feedback-pairs.json --out NEW_DATASET
```

SOURCE_REGISTRY ghi source SHA, source_video_id, source_group, scope development
hay locked_test và permission. Correction cần editor identity, before/after,
source span, review duyệt ID đó và spec thực sự xuất hiện trong recipe của
master đã xem. Chỉ duyệt hình thì bỏ SFX khỏi supervision. Chưa có cặp đạt thì
export ghi0, merge từ chối; không biến suy luận của agent thành human gold.

Nếu một test group được đưa vào học, cần ghi quyết định retire và dùng group
mới cho benchmark kế. Không chuyển nhãn của cùng tập sang train rồi vẫn tính
nó là unseen. Training package mới giữ parent fingerprint, hashes và checkpoint
cũ. Train/load được chỉ cho phép chạy thử, chưa cho phép bật cho khách.

Thiết kế tách nhóm theo nguồn dựa trên nguyên tắc chống leakage trong
[scikit-learn grouped cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
Giữ biến nhiễu trong cùng block và đảo thứ tự theo
[NIST randomized block designs](https://www.itl.nist.gov/div898/handbook/pri/section3/pri332.htm).
Các ngưỡng sản phẩm ở trên do kit đặt, không phải kết luận từ hai tài liệu này.
