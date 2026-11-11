# Áp dụng tài liệu “cỗ máy content” vào Cutroom

Đã đối chiếu tài liệu người dùng cung cấp với editor hiện có. Phần có ích nhất
là các bước có hợp đồng đầu ra rõ, dữ liệu thương hiệu chung và người duyệt cuối.
Một máy dựng local chưa cần tám agent thường trực, database chung hay publisher.

| Ý tưởng trong tài liệu | Áp dụng trong kit | Giới hạn thực tế |
|---|---|---|
| Ngữ cảnh thương hiệu chung | Logo/brand accent trong scene design; style đổi không thay script/cutaway từng bản | Asset bên thứ ba chỉ đóng gói khi có quyền |
| Researcher có nguồn | Reference analysis lưu hash, source range, observation, confidence | Scene detector không biết ý định editor, không chứng minh tính đúng của claim |
| Writer bàn giao script | Script/SRT từng recording, passage ID, occurrence, timing basis | Script dán vào không chứng minh người dẫn đã nói |
| Editor tạo artifact | Intro/demo có source quote, version, scene JSON, timeline và preview | Thiếu proof tạo pickup, không dựng thành công giả |
| QA độc lập | Sáu QC gates, full decode, cue/stem và exact-master hash | Không có audio input thì không xác nhận nghe rõ |
| Human approval | Review đúng revision/hash, bằng chứng xem/nghe và timecode | Không có tự động Publish; không gọi trạng thái rendered là published |
| Học từ sửa tay | Lưu before/after, source anchor, editor reason/confirmation | Chỉ vào lượt học sau khi kiểm eligibility và loại holdout |

Các tài liệu chính thức củng cố quyết định giữ workflow nhỏ:
[Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents)
phân biệt workflow định trước với agent tự quyết và khuyến nghị bắt đầu từ cách
đơn giản. Điều này phù hợp với batch editor có renderer/QC xác định.
[Claude citations](https://platform.claude.com/docs/en/build-with-claude/citations)
cung cấp trích dẫn gắn tài liệu; trích dẫn vẫn cần được kiểm tra có hỗ trợ claim,
không thay cho xác minh nguồn. [n8n human-in-the-loop tools](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools/)
cho thấy approval nên gắn với hành động cụ thể. Cutroom gắn approval với đúng
master/revision thay vì checkbox chung của một phiên agent.

Chưa thêm scheduler, publisher, metric tăng trưởng hay dịch vụ Claude trả phí.
Chưa có dữ liệu analytics mới để kết luận hiệu quả kinh doanh. Các giá trị
acceptance, thời gian sửa và chi phí mỗi phút được giữ null tới khi có quan sát.
