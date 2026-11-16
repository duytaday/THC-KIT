# Prompt cho Codex/Claude trong terminal

Đây là prompt vận hành dựng video. Khi phát triển hoặc mở rộng kit, dùng [master prompt đầy đủ](THC-KIT-MASTER-PROMPT.vi.md); checkpoint và yêu cầu chưa hoàn tất được ghi riêng ở đó.

Chạy trong checkout THC-KIT. Đọc `docs/HEADLESS-AUTO-EDIT.vi.md`, xác nhận interpreter/FFmpeg và workspace hiện tại. Dựng toàn bộ recording trong thư mục tuần này theo preset Tutorial Calm bằng `app/cli.py auto-edit`, kể cả khi UI đóng. Dùng engine, workspace, assignment và QC hiện có; không viết pipeline render khác.

Lấy đường dẫn recording, scripts, components, preset/template và output từ yêu cầu/cấu trúc project. Giải thích đúng CWD-relative và manifest-relative; không sao chép đường dẫn episode cũ. Nếu đủ dữ liệu, chạy `--plan-only` rồi batch ngay trong phạm vi đã được yêu cầu. Mapping mơ hồ phải hiện theo tập; các tập đủ nguồn tiếp tục. Giữ source và take chưa quyết định.

Tự chọn demo, B-roll, ảnh, animation native, logo, transition, SFX và nhạc theo câu nói, vai trò và cảnh liền kề, quyền sử dụng, runtime và preset locks. Demo chỉ phù hợp khi recording có đúng target → action → readable result; tên file và reference đẹp không chứng minh điều đó. Giữ camera/SFX đã baked và một controller mỗi thuộc tính. Có thể giữ A-roll khi thêm hiệu ứng không giúp người xem. Khi chưa có adapter phù hợp, dùng rules + scoped local retrieval; ghi model thực dùng, không tự tải/train hoặc đưa media lên cloud.

Xuất trọn mỗi tập thành MP4 mới có phiên bản và chuẩn bị A/B/C hợp lệ trên cùng voice/cut/captions. Nếu thiếu demo, ghi đúng câu cần quay, dùng presenter/minh họa có nhãn trong draft khi có thể và tiếp tục tập sau. Không thay minh họa bằng tuyên bố đã chứng minh thao tác.

Theo dõi run ID, stderr progress và `status`. Nếu dừng, `resume` run cũ; không bắt đầu run mới chỉ để chạy lại các tập đã xong. Với yêu cầu sửa một tập/câu, dùng `revise` có scope cụ thể rồi resume. Kiểm tra export ID/hash các tập không liên quan và immutable preset vẫn giữ nguyên. Không tự ghi `human`, positive training label hoặc READY. Master chờ người xem/nghe toàn bộ 1× phải `NEEDS_REVIEW`.

Bàn giao lệnh thực chạy, đường dẫn từng master và A/B/C, preset/version/hash, component thực dùng, câu và nguồn chứng minh, lựa chọn thay thế/bị loại, QC, pickup và next action. Tách rõ thử nghiệm fixture khỏi review sản phẩm thật; không gọi source hash, pixel checks hoặc decode pass là nghe duyệt. Nếu UI cần mở sau đó, dùng cùng `--data` và chỉ ba entry Files / Library / Outputs.
