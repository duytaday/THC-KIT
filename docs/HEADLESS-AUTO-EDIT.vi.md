# Dựng cả thư mục khi UI đóng

Chạy từ checkout THC-KIT với Python 3.11+, FFmpeg/FFprobe. Không cần LoRA hoặc UI. Codex/Claude chuyển yêu cầu tiếng Việt thành các lệnh dưới đây; `cli.py` nhận tham số có cấu trúc, không phải một chatbot độc lập.

```powershell
python app/cli.py auto-edit --workspace './Kênh Ali' --inputs './recordings' --scripts './scripts' --components './components' --preset './examples/headless/tutorial-calm.json' --out './outputs' --json
```

Dùng `--template './examples/headless/tutorial-template.json'` thay `--preset` để nhập template dạng dữ liệu. Thêm `--plan-only` để kiểm tra mapping và nguồn trước khi dựng. Thiếu script: dùng `--allow-transcribe` nếu local ASR đã cấu hình; nếu chưa, tập đó nhận `NEEDS_INPUT` và các tập khác tiếp tục. Script TXT/SRT do creator cung cấp chưa được coi là đã kiểm tra khớp tiếng nói.

## Chuẩn bị nguồn

Mọi tham số đường dẫn CLI tương đối với CWD. Đường dẫn trong manifest/catalog tương đối với **file JSON chứa nó**. Giữ recording, demo, ảnh, nhạc, B-roll và style reference đúng vai trò. Không tự cấp quyền dùng reference trong output hoặc training.

Ưu tiên `recordings/thc-manifest.json`:

```json
{"episodes":[
  {"id":"01","recording":"01.mp4","script":"../scripts/01.srt"},
  {"id":"02","recording":"02.mp4","script":"../scripts/02.srt"}
]}
```

Nếu không có manifest: dùng mapping đã xác nhận cùng hash nguồn, rồi ghép basename duy nhất bằng matcher hiện có. Hai `capture.mp4` ở hai thư mục không được ghép cùng một script theo phỏng đoán. Multi-take assembly/EDL chưa được CLI này hỗ trợ: chỉ định recording đã chọn rõ ràng; manifest còn `takes` bị giữ lại để creator xử lý, không âm thầm bỏ take.

`components/catalog.json` chứa các component đã được quan sát. Ví dụ schema demo (phải thay mốc và ROI bằng nguồn thật):

```json
{"components":[{
  "id":"export-demo","file":"capture.mp4","role":"screen_recording",
  "demonstrates":"export_video","runtime":"native",
  "rights":{"output":true,"analysis":true,"listen":false,"train":false},
  "permission_evidence":"Recording của creator; được phép dùng trong tập này",
  "anchors":{"offset":0,"target":0.5,"contact":1.2,"result":2,
    "target_roi":[80,180,240,70],"contact_point":[180,210],"result_roi":[80,300,540,90]},
  "framing":"control_result_cuts","result_hold_seconds":1
}]}
```

`source_sha256` tùy chọn ràng buộc metadata với đúng bytes; nên dùng cho catalog đã kiểm tra. Khi hash đổi, component bị loại thay vì tái dùng mốc cũ. Action hỗ trợ hiện tại: `export_video`, `add_subtitles`, `save`, `open_file`. Claims ngoài grammar này cần mapping scene/component rõ ràng và review, không được coi là engine đã hiểu hết ngữ nghĩa.

Các role khác: `broll`, `image`, `logo`, `music`. B-roll/ảnh dùng `tags` và `description` khớp câu đang nói; ảnh PNG/JPEG được render qua engine hiện có. Có thể giới hạn `creator`, `episodes`, khai báo `baked_camera`, `baked_sfx` để tránh chồng camera/click. Chỉ source có quyền output và runtime hợp lệ mới được chọn. Component runtime ngoài native vẫn cần cấu hình/import render; có trong catalog không có nghĩa đã chạy được.

## Quyết định dựng và review

Engine dùng rules + truy xuất preference local theo style/episode/beat; không gọi provider ngoài và không tự train. Hook, demo, CTA và các đoạn giải thích được gắn lại từ script hiện tại. Native component, transition hard-cut, SFX và nhạc từ preset được ghi trong receipt. Giữ nguyên trường `locked_fields`; chỉ các trục được phép mới có biến thể A/B/C. Preset khóa hết trục sẽ có ít biến thể thực sự khác nhau; không tạo bản trùng để giả đủ ba.

Thiếu demo: ghi đúng câu cần quay, giữ presenter và gắn nhãn minh họa trong draft, dựng phần còn lại rồi tiếp tục tập sau. Auto selection dùng `reviewer_kind=auto`; không trở thành nhãn SFT hay lượt xem/nghe của người thật. Cảnh runtime/safe-area không render được được báo trong decisions.

Mỗi master dùng chung Workspace → planner → renderer → sáu QC gate với UI. Mặc định decode/identity/QC; render đối chứng lần hai chỉ khi bật `CUTROOM_VERIFY_REPRODUCTION=1`. Các source, hash, revision, preset, component, lý do chọn/loại và pickup nằm trong JSON kết quả, workspace và `receipt.json` cạnh output. Master đang chờ xem/nghe toàn bộ ở 1× luôn `NEEDS_REVIEW`. Full decode và fixture pixel pass không thay thế review đó.

## Dừng, chạy tiếp và sửa một tập

```powershell
# Lần đầu: dừng có kiểm soát sau tập đầu, dùng để xác minh checkpoint
python app/cli.py auto-edit --workspace './Kênh Ali' --inputs './recordings' --scripts './scripts' --components './components' --preset './examples/headless/tutorial-calm.json' --out './outputs' --stop-after 1 --json
python app/cli.py status --workspace './Kênh Ali' --run RUN_ID --json
python app/cli.py resume --workspace './Kênh Ali' --run RUN_ID --json

# episode-02-patch.json: {"when_quote":"Add subtitles","music_delta_db":-3}
python app/cli.py revise --workspace './Kênh Ali' --run RUN_ID --episode 02 --patch './episode-02-patch.json' --json
python app/cli.py resume --workspace './Kênh Ali' --run RUN_ID --json
```

Scoped music cần một câu duy nhất có timing SRT trong tập. Envelope được map qua EDL sang master clock, trước ducking. Không đổi gain cơ sở của preset. Đổi lựa chọn scene bằng patch `{"round":"ROUND_ID","choice":"B"}`; đây là directive của terminal, không phải xác nhận đã xem/nghe. Retry cùng patch chỉ tạo một logical change, kể cả sau export; dùng `--request-id` mới nếu cố ý muốn áp dụng cùng delta lần nữa. ID đã dùng với payload khác bị từ chối. `resume` chỉ reuse tập có fingerprint và master hash còn khớp; dependency đổi tạo revision mới. Bản cũ vẫn còn. Nghiệm thu dừng sau tập hoàn tất không chứng minh khôi phục chính xác frame đang encode khi máy mất điện.

JSON stdout phục vụ agent, progress JSONL trên stderr và `auto-runs/RUN_ID/progress.jsonl`. CLI thường ghi `.thc-workspace.json` tại CWD để lần sau tìm đúng workspace; `--no-remember` tắt việc đó.

## UI dùng chung dữ liệu

```powershell
python app/app.py --data './Kênh Ali'
```

- **Files**: thêm và gán nguồn, script, demo/B-roll/reference.
- **Library**: nhập/chọn preset, template JSON, component cá nhân và xem runtime. Component JSON `format=thc-component/1` tham chiếu `asset` đã thêm trong Files; `role`, `name`, `tags`, `output_permission=true`, `permission_evidence` là dữ liệu, không chạy code. Screen demo còn cần action + anchors như catalog.
- **Outputs**: master, phiên bản, lý do chọn nguồn, pickup và link A/B/C từng scene sau batch. Công cụ reference/style nâng cao nằm trong Library.

App và CLI dùng cùng OS lock. Khi UI đang mở, CLI gửi thao tác về API loopback của **đúng workspace**; không mở writer thứ hai. Đóng UI không mất lịch sử. Không sửa `workspace.json` thủ công khi một writer đang dùng nó.

## Giới hạn đã công bố

Nghiệm thu ba tập dùng giọng tổng hợp và màn hình test có nhãn, kiểm tra source correspondence, âm thanh A/B/C, checkpoint/resume và phân biệt trạng thái. Chưa chứng minh chất lượng sáng tạo trên ba episode thật hoặc tự hiểu mọi claim. Không có LoRA mới được train/promote; prompt-prefix hash ổn định không phải provider prompt-cache hit. Bản cài đặt đóng gói mới chưa được phát hành.
