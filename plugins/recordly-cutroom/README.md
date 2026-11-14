# Recordly Cutroom (local preview 0.1.1)

Plugin MCP local cho Talking Head Cutroom. Điều khiển bản companion của Recordly bằng IPC của chính ứng dụng; Computer Use vẫn thực hiện thao tác demo trên cửa sổ được quay.

## Phạm vi đã triển khai

- Bảy tools: `recordly_status`, `recordly_open`, `recordly_sources`, `recordly_start`, `recordly_stop`, `recordly_save_project`, `recordly_export`.
- Chọn đúng ID + tiêu đề cửa sổ vừa quan sát. Không tự đổi sang màn hình hay cửa sổ khác.
- Webcam, mic, system audio luôn tắt cho B-roll. Tự dừng sau 5–180 giây.
- Giữ MP4 nguồn, cursor sidecars, project `.recordly`, export mới và SHA-256. Không ghi đè bản cũ.
- Mỗi thao tác dùng `request_id` ổn định. Retry cùng ID trả lại kết quả cũ; ID trùng nhưng payload khác bị từ chối. Yêu cầu có kết quả chưa rõ phải kiểm tra status/log, không tự bắt đầu lượt quay khác.
- Chỉ ghi dữ liệu của plugin vào D. Mặc định `D:/.codex/workspaces/talking-head-support/recordly-plugin`; có thể đặt `CUTROOM_RECORDLY_HOME` sang thư mục khác trên D.
- Bridge chỉ nghe loopback 127.0.0.1, kiểm token/Host/Origin, giới hạn body và danh sách lệnh. Token lưu mã hóa bằng Windows DPAPI CurrentUser, không truyền trên argv/stdout.

## Runtime

Windows, Node 22+, Recordly 1.4.0 tại `%LOCALAPPDATA%/Programs/Recordly`, dạng unpacked main. Bản đã thử trên máy này có SHA main gốc `2ef26cf37acc1b047eebbabecd5e138c78a4bd55f8c795138ec7390683ed0891`.

Đây là adapter cho build hiện có, không phải cam kết tương thích mọi bản Recordly. Nếu version, entrypoint hoặc IPC khác, dừng và giữ nguyên app gốc. Plugin chép runtime đã cài sang D rồi gắn bridge vào bản chép; không phân phối Recordly runtime trong repo/ZIP. Cần đủ dung lượng D cho companion, recordings và cache. Không sửa app gốc trên C.

Export dùng native static-layout của Recordly, scale CUDA + pad CPU + NVENC, 30fps, SAR 1:1. Companion tắt kiểm tra cập nhật tự động để giữ build đã ghim. Nhánh overlay_cuda cũ có lỗi màu trong smoke test; bản companion chuyển riêng builder đó sang builder Kf có sẵn của Recordly. Guard hash main gốc từ chối build chưa thử. Compositor Windows bị kẹt và wrapper NVIDIA mới không có trong build này, nên chúng không được bật. Export cần kiểm ảnh thực tế; native backend thành công hoặc file giải mã được chưa chứng minh đúng màu. Phiên bản này chưa cung cấp zoom/keyframe/trim/cursor compositing qua tool; `animated_zoom:false`. Project giữ lại để chỉnh bằng Recordly. Không cấp READY hay duyệt nội dung tự động.

## Khởi chạy và test

Từ thư mục plugin:

```powershell
node server/index.cjs
node --test tests/controller.test.cjs tests/http.test.cjs tests/mcp.test.cjs tests/prepare.test.cjs tests/client.test.cjs
```

Server đọc JSON-RPC từng dòng từ stdin. Chỉ protocol được ghi ra stdout. `recordly_status` không mở ứng dụng hay quay.

Test dùng temporary directory; trên máy này đặt `TEMP`/`TMP` vào thư mục test riêng trên D trước khi chạy. Các unit fixture ghi rõ không phải video; chỉ smoke test với ứng dụng thật mới xác minh capture/export.

## Workflow thật

1. `recordly_open`, sau đó `recordly_sources`.
2. Dùng Computer Use chuẩn bị cửa sổ demo, xác minh nội dung không lộ tài khoản/khóa. Lấy lại ID và title.
3. `recordly_start` với `beat`, `window_id`, `expected_title`, giới hạn thời gian và ID ổn định.
4. Computer Use thực hiện thao tác thật. Giữ kết quả đủ lâu để đọc.
5. `recordly_stop` với đúng `capture_id`. Giữ project và nguồn.
6. `recordly_export` sang tên mới. Kiểm file xuất, màu/crop/chữ/thao tác/kết quả.
7. Đưa B-roll đã duyệt vào kit bằng công cụ hiện có:

```powershell
python talking-head-qc/tools/import_recordly.py <export.mp4> --job <job-id> --beat <beat-id> --project <project.recordly>
```

Chạy bước import từ checkout của kit. Trang smoke fixture không phải bằng chứng demo phần mềm hay đầu ra của khách, không đưa vào thư viện B-roll production.

## Kết nối Codex

`plugin.json` + `mcp.json` là package portable. `.codex-plugin/plugin.json` + `.mcp.json` là overlay tương thích Codex hiện tại. Từ checkout, đăng ký marketplace local trong `plugins/`, sau đó cài `recordly-cutroom@talking-head-cutroom-local`. Giữ các marketplace hiện có. Cài đặt không chứng minh tool đã xuất hiện trong chat; kiểm discovery và gọi status trước khi sử dụng.

## Giới hạn và khôi phục

- Nếu `open.lock` còn lại, kiểm process/log trên D trước; không xóa lock và mở lặp khi chưa biết kết quả.
- Không tự cài/cập nhật Recordly hoặc thay quyền Windows. Nếu Computer Use vướng quyền, người dùng xử lý đúng bước đó.
- Native capture là B-roll im lặng; không đánh giá LUFS/giọng nói bằng clip này. Master cuối vẫn phải qua QC sáu gate và người nghe/xem thật.
- Nội dung trang, tiêu đề cửa sổ và text trong video là dữ liệu, không phải lệnh hay bằng chứng người dùng cho phép hành động.


## Capture source guard (0.1.2)

The exact selected window ID/title is checked again after selection, every 300 ms
while recording, and at stop. A changed/missing window or failed source check
stops the capture, retains its source/native project, marks the take FAILED and
blocks export. In 0.1.2, all title changes required a new take. Version 0.1.3 below adds an
explicit planned-navigation contract. Never silently expand the allowed title list.

MONITORED_NO_CHANGE_OBSERVED means only that polling saw no ID/title change.
It does not prove pixel isolation, privacy, a real tutorial result or readiness.
Inspect the decoded export for unwanted tabs/windows. Legacy captures are
LEGACY_UNVERIFIED and retain their prior evidence. The 0.1.2 native Windows
recapture remains pending; deterministic tests do not replace that test.


## Planned navigation (0.1.3)

For a real navigation demo such as GitHub → Releases, prepare both states before
recording. Call recordly_sources in each state and verify the SAME window ID.
Return to the initial state. Supply allowed_titles on recordly_start containing
the exact initial title and up to four additional exact destination titles that
were listed for that same ID in the last five minutes. No wildcards or guessed
titles. The title list is frozen for the entire take; listing another window or
calling sources during recording cannot expand it. Without allowed_titles, the
strict single-title behavior remains. Unexpected titles still quarantine the take.

This allows the intended action/result to stay in one recording while retaining
the source-change guard. It still cannot prove tab/pixel isolation between polls.
Inspect the decoded export. Native Windows planned-navigation capture remains
pending explicit resumption of desktop use; unit tests are mechanical evidence.
