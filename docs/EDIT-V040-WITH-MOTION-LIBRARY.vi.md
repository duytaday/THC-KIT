# Áp dụng thư viện Motion mới để sửa v040

Đây là yêu cầu được owner giao từ chat Refine the prompt: sau khi hoàn tất tích hợp thư viện, gửi editing prompt sang chat make videos để áp dụng cập nhật và sửa v040. Tiếp tục chỉnh video trong chat này, thực hiện render và giao revision mới có bằng chứng. Không ghi đè v040 hoặc khởi động lại training đang paused ở chat kit enhance.

## Baseline cần mở trước

- Video mới nhất đã xác định từ lịch sử chat: `D:\.codex\visualizations\2026\11\11\01a1c8a2-b6a9-7833-8a7f-ace64b506c57\recordly-review-v040\final-v040.mp4`.
- Checklist: cùng folder, `checklist.md`. Baseline là 720×1280, 30 fps, khoảng 118 giây; probe file hiện tại để xác nhận thay vì tin số lịch sử.
- Scene Recordly 00:55.133–00:57.833 đã thay hộp che bằng khung sạch và gắn PHÓNG TO MINH HỌA. Đây là still từ source thật dùng làm minh họa, không phải bằng chứng cú bấm hoặc zoom tự động.
- Animation cảm ơn được thêm theo cue khoảng 01:56.880. Giữ thông điệp CẢM ƠN MỌI NGƯỜI! và xác nhận lại cue từ SRT/voice hiện tại.
- Các component/reference excerpt đã có ở `D:\.codex\visualizations\2026\11\11\01a1c8a2-b6a9-7833-8a7f-ace64b506c57\recordly-refinement-v039\components`.
- Source recording thao tác liên tục đã tìm được: `D:\.codex\workspaces\talking-head-video-editing-skills\output\real-footage-acceptance\episode-input-v001\recordly-click-continuous.mp4`. Xác minh source hash/path/permission và chọn đúng interval; không suy ra action chỉ từ tên file.

## Cập nhật triển khai thật có thể dùng

Checkout `D:\.codex\workspaces\talking-head-video-editing-skills`, baseline git `ba8fc8004094d9d9b921470966893c149356bd3d`, và code Motion đã được version ở commit `d1435e6`. Tài liệu này giữ baseline lịch sử của lần bàn giao; dùng HEAD hiện tại và kiểm tra thay đổi chưa commit trước khi dựng. Giữ nguyên thay đổi hiện có khi mở project. Đọc `docs/MOTION-LIBRARY-BUILD-PROMPT.md` và `docs/MOTION-LIBRARY-INTEGRATION-2026-11-15.vi.md`.

Các entry point:

- `app/motion_catalog.py`: inventory, source search, recommend, apply_recipe, supplied-render import.
- `app/motion_bridge.py` + `app/animation_runtime/sample-motion.cjs`: upstream Motion 14.14.0 samples ở frame clock 30 fps, không dùng wall-clock/random easing. Các curve: motion_ease_out, motion_ease_in_out, motion_spring.
- `app/scene_plan.py`: chọn đúng current passage, template/component và recipe/easing; source/revision gates và replay-safe preview.
- `app/animation_library.py`: template native và instance riêng; giữ source observation/provenance.
- Normal UI/API: GET /api/motion-library; GET /api/motion-library/search?q=...; POST /api/motion-library/recommend; POST /api/animations/register-external. Dùng app authentication/session contract hiện có; không tạo unauthenticated API.

Library có 6 providers, 420 source references, 14 recipe records (10 Motion treatments + 4 external-output records). Các pointer không phải 420 animation sẵn sàng. Motion native path đã có render thật; OpenShot thiếu native runtime; generation từ OpenMontage/Pixelle/Hypit/Toonflow chưa cấu hình. Không ghi hoặc render giả danh các engine đó. Có thể nhập render được cung cấp rõ ràng qua adapter, giữ provider claim là unverified và inspection/rights gate. Không cài hàng loạt app/service chỉ để trang trí v040.

## Mục tiêu chỉnh sửa

1. Review toàn v040 theo script, voice và footage. Tạo một shot/change map ngắn: timeline range, lời nói, vấn đề thực, reference interval/quan sát, treatment phù hợp, asset/proof cần có, vùng cần bảo vệ. Giữ các đoạn đã phù hợp; không phủ animation lên mọi câu.
2. Với cảnh cần nâng, lọc purpose/input/runtime/aspect/readable hold/complexity trước rồi xếp theo reference style/niche. Mood calm/minimal có thể thắng default. Recipe phải khớp component. Dùng API hoặc cùng module contracts; lưu recipe/catalog/runtime hash và tham số thực tế trong revision manifest.
3. Dựng lại motion/layout quan sát từ reference thành component native chỉnh sửa được, có entrance/hold/exit, typography, placement và source-linked observation. Tạo variant riêng; không chỉ đổi tên một clip baked thành editable template. Audio reference chỉ có trạng thái observed khi thật sự nghe được.
4. Ưu tiên Recordly: hình minh họa phải khớp ý đang nói, zoom bám đúng vùng thật và còn đủ context/readable hold. Giữ nhãn minh họa trên still/freeze. Nếu mô tả action/result, cần footage thật và source-time evidence; thiếu thì NEEDS_PICKUP, vẫn tiếp tục được các scene khác. Không dùng zoom, circle, click SFX hoặc hình mô phỏng để khẳng định cú bấm chưa ghi được.
5. Presenter circle chỉ dùng ở cảnh phù hợp, bottom-right khi không che control/result/caption/platform overlay. Dùng nguồn presenter hiện tại và native mask thật. Nếu che nội dung, chỉnh size/corner/layout có lý do; không ép circle vào mọi cảnh.
6. CTA được dựng theo reference CTA đã chọn và actual words của tập. Giữ lời cảm ơn cuối video. Nếu script không có offer/destination/CTA cụ thể, không tự thêm quảng cáo hoặc gọi hành động mới; dùng title/closing treatment phù hợp. Generic CTA recipe không chứng minh tái tạo đúng reference.
7. Giữ duration/source order/voice/caption timing, lock và mix hiện tại nếu không có lý do sửa được chứng minh. Khi cần SFX, gắn với đúng cue hình/lời; dùng gain/mute có kiểm soát và không lấn giọng. Ghi lại từng thay đổi âm thanh. Không dùng loudness toàn video để kết luận từng SFX nghe rõ hoặc khớp bằng tai.
8. Kiểm tra native geometry ở 9:16 và output thực 720×1280. Nếu component render ở 1080×1920, scale/composite rõ ràng về target, kiểm tra lại font/hold/circle/caption ở kích thước phone. Không đổi toàn master lên 1080 chỉ để báo thông số cao hơn.

## Readiness và evidence

NEEDS_RUNTIME: cho xem tham khảo/dependency/mẫu thay thế, chưa chèn với nhãn executable. READY_TO_RENDER cần smoke render thật cho template + runtime hash/version + assets của project. READY_FOR_SCENE cần kiểm tra trên đúng footage hash/source interval/aspect/template version/scene revision và quyền xuất. Đổi những dữ liệu đó phải kiểm tra lại. NEEDS_PICKUP là gate nội dung riêng. App hiện mới có runtime capability labels và scene NEEDS_REVIEW; ghi evidence vào manifest trung thực, không tuyên bố toàn bộ badge/invalidation UX đã ship (THC-54).

## Thực hiện và nghiệm thu

- Hash/probe v040 trước chỉnh. Giữ toàn bộ baseline và các source; ghi output vào folder revision mới trên D (v041 nếu đang dùng version tuần tự).
- Render scene preview cho các thay đổi chính trước, xem frame entrance/peak/hold/exit và những thời điểm presenter/caption/control có thể giao nhau. Sau đó xuất master qua normal compositor/workflow; không chỉ giao prompt hoặc ảnh mockup.
- Re-probe master: aspect, fps, duration/frame count, audio/video streams, decode; kiểm tra nguồn voice/mix/captions được giữ hay thay đổi chính xác ở đâu.
- Xem contact sheet toàn video và frame chi tiết ở source transitions, Recordly, CTA/cảm ơn, circle và phần giá/demos nếu có. Nếu có khả năng nghe, nghe liên tục đúng master và ghi review gắn hash. Nếu không nghe được, giữ listening UNVERIFIED và master NEEDS_REVIEW; nêu rõ phần human review còn lại.
- Regression triển khai đã quan sát 347 total / 334 passed / 13 skipped (UTF-8); đó không thay cho kiểm tra video revision này. Không tự ghi READY hoặc tự nhận tăng chất lượng model.
- Giao MP4 có preview inline, đoạn before/after cho thay đổi chính, change map, editable component/instance manifests và QC/checklist với hash output. Báo ngắn gọn phần chưa kiểm chứng.

Tracking hiện có: THC-53 In Review (core integration); THC-54 readiness; THC-55..59 runtimes/generation; THC-52 reference CTA; THC-51 circular annotation; THC-45 integration evidence; THC-46 exact demo/master. Nếu cập nhật tracking, dùng site https://duytruyenthong.atlassian.net và space/project THC đã được owner xác nhận, tìm issue sẵn trước khi tạo mới. Không đóng engine setup hoặc full-master review chỉ vì video đã render.

Tham khảo kết quả: https://duytruyenthong.atlassian.net/wiki/spaces/THC/pages/3506177 và https://duytruyenthong.atlassian.net/wiki/spaces/THC/pages/3538993. Local evidence/package: `D:\.codex\visualizations\2026\11\11\01a1cbdf-fc9e-70b1-8a2c-3255abbcc981\motion-openshot-integration`.
