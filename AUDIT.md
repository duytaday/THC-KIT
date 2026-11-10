# Audit kiến trúc và mã nguồn

Ngày 2026-11-10. Phạm vi gồm toàn bộ 13 file được Git theo dõi tại commit 7bce3f0, ba script Python, prompt, skill, template, quy tắc Git và luồng gọi ffmpeg-skill. Thư viện cài riêng của Recordly, ShotCraft và ffmpeg-skill nằm ngoài codebase này.

Người dùng xác nhận mỗi máy chạy riêng, checker đi trước và người duyệt cuối quyết định giao khách.

## Đánh giá

Nên giữ ba trách nhiệm hiện tại gồm nhập bản capture, kiểm tra một revision và smoke test tích hợp. Chúng có đầu vào và kết quả dễ kiểm tra. Điểm yếu chính là điều kiện kết luận READY và hướng dẫn bị gắn với lịch sử cài đặt một máy.

Số lượng khách hàng yêu cầu kiểm thử và quy trình duyệt nhất quán. Nó chưa tạo nhu cầu cho server điều phối, hàng đợi, database hoặc hệ thống tài khoản trong một kit chạy local.

## Phát hiện và thay đổi

| Mức | Phát hiện trước sửa | Thay đổi |
|---|---|---|
| Cao | Phản hồi upstream có thể khai ok=true nhưng vẫn chứa FAIL. Schema hàng kiểm tra chưa được xác minh. | FAIL luôn chặn READY. Hàng thiếu tên hoặc status không hợp lệ làm checker trả BLOCKED. |
| Cao | Một timestamp bất kỳ đủ hợp thức hóa PASS. 99:59 có thể được dùng cho video hai giây. Warning chỉ cần một chuỗi. | Yêu cầu ít nhất một timestamp trong thời lượng render cho PASS và warning. Hỗ trợ giờ và phần giây thập phân. |
| Cao | Chưa ghi trách nhiệm người duyệt cuối, agent có thể hoàn tất form và nhận READY. | Form có approved_by. Thiếu tên giữ NEEDS_REVIEW. Hướng dẫn yêu cầu người duyệt cuối xem master và tự ghi tên. |
| Vừa | SRT chấp nhận cue lặp/sai thứ tự và overlap 1 ms trái với profile công bố. | Kiểm tra index 1..N và chặn overlap. |
| Vừa | Thời gian beat chuyển chuỗi và bool thành số, required IDs có thể trùng. | Bắt buộc số hữu hạn và ID duy nhất. Duration bounds cũng phải là số. |
| Vừa | JSON có BOM trên Windows dễ thất bại. Tool gọi ngoài có thể treo vô hạn. | Đọc JSON bằng utf-8-sig. Timeout 60 giây cho import probe và 1800 giây cho từng bước QC. Lỗi QC trả JSON BLOCKED. |
| Vừa | Tên job của importer phụ thuộc quy tắc từng OS, probe nhận duration không hữu hạn. | Chặn tên thiết bị Windows, ký tự phân cách, đường thoát khỏi thư mục B-roll và duration không hữu hạn. Chuẩn hóa tên take và trả lỗi CLI gọn. |
| Vừa | README giả định đường dẫn Python riêng máy và giữ blocker Recordly đã lỗi thời. | Hướng dẫn chọn interpreter/skill root tại setup. Bỏ trạng thái cài đặt của một máy khỏi tài liệu vận hành. |
| Vừa | Brief và reference của khách hàng có thể bị thêm vào Git, ignore video chỉ phủ một cấp. | Ignore toàn bộ briefs/ và references/, bên cạnh input/ và output/. |
| Thấp | Log smoke tĩnh, báo cáo sự cố cũ và checklist cá nhân lẫn trong sản phẩm. | Xóa hai file báo cáo cũ. Bỏ theo dõi checklist và giữ bản local. |

## Những phần giữ lại

- Giữ SETUP-PROMPT.md vì chứa sáu tiêu chí editorial và hướng dẫn sửa theo timestamp. Skill trỏ đến các tiêu chí này.
- Giữ brief và reference templates đã cung cấp. Những ghi chú Facebook là quan sát từ tài liệu đầu vào, chưa được audit này xác minh lại.
- Giữ hash của năm artifact, timeline beat và phiên bản output vì chúng gắn review với đúng nội dung được duyệt.
- Giữ Recordly và ShotCraft như công cụ tùy chọn được cài riêng. Chúng phục vụ capture và motion insert khi brief cần.
- Giữ smoke test có FFmpeg thật. Các test hồi quy mới kiểm tra lỗi có thể gây duyệt nhầm.

## Kiểm chứng

Python 3.12.14, ffmpeg-skill 3.2.3 và FFmpeg/ffprobe 8.1.1 trên Windows.

- 15 test hồi quy PASS. Bao gồm hợp đồng exit 3 và JSON BLOCKED khi thiếu dependency, settings sai hoặc tool timeout.
- Smoke test thực thi qua CLI và upstream checker PASS cả năm case, overall exit 0. READY của fixture dùng evidence và người duyệt giả lập được ghi rõ.
- Import tích hợp trên MP4 fixture PASS. Kiểm tra hash, metadata, duplicate, bảy tên job không an toàn và cleanup sau media hỏng.
- git diff --check PASS. Ignore rules phủ brief, reference lồng thư mục và checklist local.
- Chưa chạy trên Python 3.10 hoặc Linux/macOS. Chưa có master hội thoại thật được agent xem/nghe trọn trong audit này. Người dùng xác nhận Recordly hoạt động trên máy.

## Giới hạn còn lại

approved_by là trường văn bản và timestamp là kiểm tra cú pháp. Người sửa JSON có thể tự điền chúng. Chúng không xác thực danh tính hoặc chứng minh nội dung quan sát đúng. Người duyệt cuối chịu trách nhiệm so sánh brief, nguồn và master.

Kit này có hợp đồng video có audio và SRT đồng bộ. Các job không có audio hoặc có quy cách caption khác cần xác định lại hợp đồng trước khi dùng gate.

Mỗi revision chỉ nên có một tiến trình ghi QC. Các file và lần kiểm tra hash đầu/cuối chưa tạo thành một giao dịch có khóa. Nếu sau này một máy cần nhiều worker cùng ghi một revision thì phải xử lý yêu cầu đồng thời đó trước khi triển khai.

Một checkout cho mỗi khách hàng giảm việc trộn asset và báo cáo. Git ignore không mã hóa, phân quyền hay sao lưu dữ liệu. Các file đã theo dõi và lịch sử Git vẫn giữ nội dung trước khi bị xóa. Người vận hành phải kiểm tra staged diff và lưu bản sao dữ liệu local.

Toolchain bên ngoài thay đổi có thể ảnh hưởng detector. Pin phiên bản đã kiểm thử và chạy lại smoke test sau thay đổi môi trường. Bản audit này chưa xác minh năng lực vận hành thực tế cho hàng trăm khách hàng.
