# Danh mục 20 component — v1.0

Đây là đặc tả, không phải chứng nhận 20 component đã chạy. Runtime inventory
ở `app/components.py`; kết quả render nằm trong báo cáo nghiệm thu và artifact
của **job hiện tại**. Mọi preview phải dùng A-roll thật và giữ nguồn/timecode.
Full QC cần người xem/nghe đúng master, không suy từ unit test. Không phát hành
private footage cùng skill. Tất cả defaults dưới đây là **house rule thử nghiệm**.

Mọi component có `id`, `version=1.0`, source beat, source ranges, purpose,
decision provenance (`observed/editor_confirmed/rule/model`), status và preview
receipt. Thời gian giây hữu hạn trong kept interval; ROI nằm trong source;
output 1080×1920/30 là preset hiện tại, không phải format bắt buộc mọi tập.
Các mapping là engine đang có; biến thể chưa được kiểm không xuất hiện như
một nút component đã hoạt động.

| ID · nhiệm vụ | Dùng / bỏ khi | Tham số hợp lệ · mapping | Vùng bảo vệ · ít chuyển động |
|---|---|---|---|
| 01 Người dẫn toàn khung | Ngữ cảnh, quan điểm, kết nối, CTA / bỏ khi cần đọc demo | `fit=cover/contain`, keep in-out, punches tách riêng; `engine.edit` | Mặt, miệng, headroom; không punch |
| 02 Người dẫn trên/dưới demo | Cả biểu cảm và chi tiết đủ lớn / bỏ nếu detail nhỏ | Đặc tả host fraction .25–.4, top/bottom, crop; **chưa có generic renderer**, không bật UI | Detail và caption; full demo thay split |
| 03 Người dẫn PiP | Có thể giữ mặt mà không che bằng chứng / full demo khi không có góc trống | `layout=presenter_pip`, `pip_corner=auto/top_left/top_right/bottom_left/bottom_right`, `pip_width=.18–.36`; `engine.layouts` + edit | Target/result/contact/caption; góc đứng yên trong cutaway; hard cut |
| 04 Demo toàn khung | Thao tác/kết quả cần đọc / A-roll nếu không có chứng cứ cần thấy | `layout=full_demo`, source_start≥0, duration≥1/30, crop source pixels; planner.proof | Control/result; giữ nguyên zoom đã có, hard cut |
| 05 Chữ hook | Một promise có bằng chứng / bỏ title nếu dư | Intro artifact title, `variant=promise/result_first/list_reveal`, source passage/duration; artifacts | Mặt, proof; static title variant |
| 06 Caption theo cụm | Lời đã thu / thiếu lời thì pickup | `caption_mode=guide`, `caption_position=top/bottom`, page 1–4 từ ở renderer hiện tại, SRT phrase timing; edit | Miệng/control/result; clean static phrase, tối đa 2 dòng cần xem lại |
| 07 Nhấn từ/số | Chi tiết quan trọng đúng lời / không có trọng tâm | Caption active word hoặc keyword event, phrase source times, motion intensity 0–1 | Không sửa nghĩa/số; màu tĩnh hoặc bỏ nhấn |
| 08 Lower third | Tên/chức danh xác minh / không bịa identity | `speaker` event text, anchor, hold_frames≥1; enhance | Mặt/caption/proof; text tĩnh |
| 09 Bước/chương | Nhiệm vụ đổi / không gắn nhãn mọi câu | `chapter` event text, anchor, hold_frames≥1; enhance | Detail/caption; static label |
| 10 Phóng chi tiết | ROI vẫn còn ngữ cảnh / bỏ nếu nguồn đã zoom hoặc chữ giảm nét | Proof source crop `[w,h,x,y]`, `ui_focus` ROI; variant phóng động/chèn ô chưa mặc định | Contact/result; crop cố định |
| 11 Callout | Người xem cần định vị / bỏ nếu đã rõ | `ui_focus` output ROI, frame anchor, hold; enhance | Không che UI gốc; viền tĩnh |
| 12 Nhấn tiếp xúc | Có observed contact / không biết thì không vẽ | `contact` source pts/point→output ROI, hold frames, independent sound; cues/enhance | Chữ nút và cursor; điểm tĩnh hoặc tắt ring |
| 13 Giữ kết quả | Kết quả đã xuất hiện thật / thiếu thì pickup | `result` observed pts/result_roi + proof duration kéo đủ đọc; cues/edit | Giữ nhãn UI, đơn vị; viền tĩnh hoặc chỉ hold |
| 14 So sánh A/B | Hai state thật, cùng tiêu chí / bỏ ví dụ giả | `before_after` artifact evidence pair, source ranges/labels/duration; artifacts | Cùng zoom/đơn vị/label; cắt tuần tự |
| 15 Minh họa nội dung | Supplied B-roll/ảnh hoặc sơ đồ gốc giải thích / bỏ khi A-roll đủ | Proof clip hoặc `process_diagram` artifact, actual asset/hash/source beat | Phân biệt minh họa và proof; static diagram. Generated lab không nằm V1 |
| 16 Chuyển cảnh | Đổi bước/mức quan sát có lý do / mặc định cut | Cut qua edit.proof. Slide/zoom-blur là đề xuất riêng **chưa generic/render-test** | Detail không bị blur khi cần đọc; cut |
| 17 Music dưới giọng | Có quyền và hỗ trợ nhịp / Music Off hợp lệ | `music_mode=off/auto/my_track`, gain −60–0dB, source hash với my_track; enhance.mix | Lời, qualifier/negation; cùng bed xuyên cảnh, ducking vẫn hoạt động |
| 18 SFX sự kiện | Action/motion/result có anchor / mute từng cue hợp lệ | Sound id/muted/gain −60–6dB, offset_frames hữu hạn + lý do nếu lệch, 48k sample marker; enhance/cues | Không lấn lời, click/chime không trước action; không swish nếu ít motion |
| 19 CTA | Một việc thật cuối tập / thiếu lời mới thì title hoặc pickup | Caption/title/speaker text ở kept closing range; chưa có nút CTA riêng | Mặt + hành động + đủ thời gian đọc; static card |
| 20 Xem sớm kết quả | Source result thật, không gây hiểu sai thứ tự / bỏ nếu tiết lộ sai | Intro `result_first` với evidence source range và nhãn xem trước | Không gọi mock là result; hard cut rồi trở về bước đầu |

## Ca nghiệm thu có thể lặp

Component03 giữ cùng font/color/margins ở hai cutaway. A: bảo vệ ROI nút góc
dưới trái, Auto chọn góc khác và giữ cả cảnh. B: ROI bảng chiếm canvas, fallback04.
Góc manual va chạm phải chặn render để editor sửa, không âm thầm ghi đè.
Chỉnh góc không thay source timing/caption/music. Mỗi kết quả có layout_decision
trong plan và preview MP4 mới. Không gọi test đơn vị bố trí là đã xem video.

## Kết quả và công việc còn thiếu

UI inventory tách specified/render-tested/editorially-approved. Một component
render được không làm toàn tập READY. Split02, transition slide/zoom-blur16,
PiP rounded-corner và inset10 là backlog; dùng full demo/cut trước. Không tạo
biến thể riêng từng tập rồi gọi là tái sử dụng. Khoá override theo scene; batch
chỉ chạm các trường editor chọn, không reset scene/script/cue khác.
