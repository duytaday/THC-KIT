# THC-KIT: thư viện B-roll và train local

Baseline audit: `9d5db7c358e1609e478219de65d8d92dffa8c3e6`, remote `duytaday/THC-KIT`.
Đây là phần mở rộng của CLI, Workspace, Library, renderer và QC hiện có.
Không có renderer, dịch vụ cloud hay giao diện dựng thứ hai.

## Luồng đang chạy

`assets discover → collect → review-batch → index/embed → headless auto-edit → native render → six-gate QC`.

- Commons API và Internet Archive public API cung cấp file nguồn/provenance. HTTP client kiểm URL/redirect, rate limit, Retry-After theo host qua cả lần khởi động lại, partial Range/ETag và ngân sách đĩa.
- File qua MIME magic, ffprobe, decode video đầy đủ, SHA-256, temporal fingerprint có mirror/crop, source-family dedup rồi mới vào originals theo hash. Audio stock không được đưa vào mix.
- Proxy, thumbnail, contact sheet và embedding là derivatives; không tăng quota nguồn. Original không được sửa bởi pipeline.
- `verified` là đã decode; `edit_ready` là đã qua kiểm nội dung mẫu; `retrievable` còn loại sealed/test. `human_approved` và `training_example_ready` là các fact riêng.
- Kiểm nội dung hiện dùng batch contact sheet do agent xem; chưa có classifier thị giác tự động đã benchmark. Đây là thư viện để dựng draft, không phải sign-off master.
- Library UI tìm bằng tiếng Việt, phát proxy và thêm vào bản quay đã chọn. Cutaways hiện có dùng asset đó. API thay insert giữ câu nói, phụ đề, timeline và cue gain/mute; stock không thể thay proof thật đã gắn.
- Headless giữ ưu tiên component/manual override hiện có. Khi một beat explain chưa có nguồn phù hợp, B1 tìm stock và xuất typed EditPlan. Beat yêu cầu proof giữ luồng Recordly/pickup. Không lấy stock làm kết quả thao tác phần mềm.
- Mọi preview/master mới vẫn cần nghiệm thu theo đúng revision/hash. Đổi ảnh không tự duyệt lời nói, caption hay SFX.

## Vị trí dữ liệu của máy này

`D:\.codex\workspaces\talking-head-support\asset-library-v001`

Trong đó có `assets.sqlite3`, `manifest.jsonl`, `progress.json`, `originals/`, `derived/`, `partial/`, `quarantine/`, cache, `datasets/` và `models/`.
Footage, labels, RAG và checkpoint không nằm trong Git. Đổi vị trí bằng `THC_ASSET_LIBRARY` hoặc `assets --library <path>`; tham số global đặt trước subcommand.

Trước khi chạy trên máy này:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py = $env:THC_PYTHON
$modelPy = $env:THC_MODEL_PYTHON
& $py app/cli.py assets status
& $py app/cli.py assets discover --pages 1 --per-query 50
& $py app/cli.py assets discover --queries D:\path\scene-queries.json --pages 1 --per-query 50
& $py app/cli.py assets --agent-model ACTUAL_CALLING_MODEL discover --provider archive --queries D:\path\archive-scenes.json --pages 1 --per-query 10
& $py app/cli.py assets --agent-model ACTUAL_CALLING_MODEL collect --provider archive --target 1000 --max-attempts 20
& $py app/cli.py assets collect --target 1000 --max-attempts 100 --budget-gb 40 --reserve-gb 30
```

`--target` là mục tiêu số nguồn retrievable; không dừng chỉ vì đủ file technical-unique trong khi phần lớn bị loại nội dung. `--max-attempts` chặn lượng công việc mỗi batch. File chưa kiểm nội dung không tự thành B-roll đạt. `complete` chỉ true khi đủ số nguồn retrievable. Batch có thể kết thúc với `complete:false`; đọc các số riêng, không lấy discovered/indexed làm số clip giao được.
Lặp lại cùng collect command để resume; file đã verify không bị tải lại. Collector lease ngăn discover/collect/review/dedup cùng ghi vào một thư viện. Quarantine được giữ, không tự xóa footage.

Decoder v3 kiểm toàn bộ video một lần bằng FFmpeg `-xerror`, đồng thời lấy mẫu nhỏ cho fingerprint/windows; không decode toàn bộ hai lần. Timeout được ghi DEFERRED và giữ bytes hoàn chỉnh để thử lại local, khác với file hỏng bị quarantine. Kiểm tra live đã khôi phục một nguồn timeout, giữ nguyên hash và thời điểm tải, không gọi HTTP lại.

```powershell
& $py app/cli.py assets review-batch D:\path\batch-review.json --evidence D:\path\contact-sheet.jpg
& $py app/cli.py assets dedup-audit --upgrade-fingerprints
& $py app/cli.py assets embed --python $modelPy --device cpu
& $py app/cli.py assets search 'bàn phím và lập trình' --limit 5
& $py app/cli.py assets catalog --out D:\path\stock-catalog.json
```

Review document nhận hash nguồn và evidence, lý do, category và quyết định agent. Không chấp nhận biến đường này thành nhãn human. Audit nâng fingerprint được checkpoint từng asset, giữ nguyên originals. Catalog dùng được với `auto-edit --components`; nguồn/offset/window vẫn được kiểm lại.

File `scene-queries.json` tùy chọn có dạng `{"office":["office interior"],"ecommerce":["shopping cart conveyor"]}`. Tối đa200 query, category phải thuộc thư viện, mỗi query1–200 ký tự. CLI dùng lại cùng cursor/idempotency như bộ query mặc định; dùng cảnh cụ thể thay vì mở rộng query chung để chạy theo quota.

Archive giữ một original phù hợp trên mỗi item; bản MP4/WebM hoặc resolution khác trong cùng item không tăng quota. Bỏ item bị hạn chế truy cập, file derivative và khai báo NC/ND không phù hợp luồng dựng thương mại. Ưu tiên original1080p trong giới hạn thời lượng/dung lượng; giữ native dimensions đo lại. Cursor Archive tách khỏi Commons. Tham số agent-model chỉ nhận dạng caller trong User-Agent, không chọn hay gọi một model cloud. AI caller điền model thực tế theo [hướng dẫn bot của Archive](https://archive.org/developers/bots.html).

Khi rule metadata thay đổi, collector chỉ xét lại các nguồn chưa tải bị loại theo metadata; giữ nguyên những quyết định loại theo hình đã xem. Agent visual review tiếp tục là bước riêng sau decode, không tự thành human approval.

Chạy UI hiện có:

```powershell
& $py app/app.py --data D:\path\creator-workspace --no-browser --port 59518
```

Mở `http://127.0.0.1:59518/library.html`. Khi có nhiều bản quay, dùng selector trước khi thêm stock. Cùng request ID chỉ thực hiện một hành động; stale revision trả Conflict, không đổi số revision rồi ghi đè draft cũ.

## Hai track text LoRA, không phải model sinh footage

- A: context của lời nói/candidate pool/locked style → typed EditPlan, source/timeline clock và crop/cue references được validate.
- B: context hiện tại → source-bound MotionSpec qua compiler hiện có; text/anchor/ROI lấy từ nguồn hiện tại.
- C: chưa có recipe sinh pixel video local đã kiểm chứng; registry ghi NOT_IMPLEMENTED. Không gọi A/B là video-generation training.

Pilot A dùng context do agent tác giả hóa, không phải creator-approved edit decisions. Pilot B dùng lại train/development reconstruction cũ có nhãn agent. Không có human preference hay dữ liệu trước/sau được creator duyệt mới trong lượt này.

Partition sealed của pilot A chỉ kiểm cơ chế cách ly: raw stock đã được agent kiểm nội dung trước khi chia. Nó không phải tập whole-episode độc lập chưa từng xem. Điểm retrieval trong dataset pilot được đóng băng trước bản sửa mô tả nội dung hiện tại; không dùng chúng để chứng minh RAG live mới tốt hơn.

```powershell
& $py app/cli.py assets dataset --track A --out D:\path\datasets\planner-v001
& $py app/cli.py assets dataset --track B --source D:\path\existing-motion-dataset --out D:\path\datasets\motion-v001
& $py app/cli.py assets model-prepare D:\path\datasets\planner-v001 --steps 4 --max-tokens 1536
& $py app/cli.py assets model-train RUN_ID --python $modelPy --stop-after 2
& $py app/cli.py assets model-train RUN_ID --python $modelPy --resume
& $py app/cli.py assets model-evaluate RUN_ID --python $modelPy --limit 10
& $py app/cli.py assets models
```

Trainer chỉ mở manifest allowlist train/development, kiểm hash và group leakage, không tự tìm các file JSONL khác. Final được ghi ngoài package, không dùng trong retrieval/optimizer. Alias mới kế thừa split theo creator/family/hash; phát hiện duplicate xuyên split làm invalidate dataset và loại cluster khỏi RAG. Đây là isolation ở ứng dụng local, không phải sandbox chống người có quyền sửa file.

Base Qwen2.5-1.5B-Instruct được pin revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, local-only, safetensors, không remote code. Config, dataset hash, tokenizer, dependency versions, code snapshot, optimizer/RNG và checkpoints được giữ. Resume completed run là replay; không train đè adapter cũ.

Có tối đa ba recipe mỗi cycle. Development eval không đọc final, không biến autopick thành human preference. Prompt prefix/hash, embedding cache và render cache được báo riêng; không có provider prompt-cache hit hay cross-adapter KV reuse được suy ra.

## Nghiệm thu và rollback

B0 là rules; B1 thêm RAG; B2 dùng cùng candidate pool và LoRA. Kết quả scene validator/agent-label match chỉ là diagnostic, không phải benchmark whole-video. Harness ghi rõ khi chưa render, chưa nghe full mix, chưa đo first-pass acceptance hoặc phút sửa/phút thành phẩm.

Promotion bị chặn khi còn development regression, báo cáo đổi hash hoặc thiếu so mù whole-episode/human review. B1 đang được giữ. Hook dùng scoped candidate của A chỉ sau approval và local runtime cấu hình; track B hiện mới là candidate/inference/compiler experiment, chưa chứng minh rollout tự động vào native motion cho khách.

Rollback scoped, không xóa checkpoint:

```powershell
& $py app/cli.py assets models
& $py app/cli.py assets model-rollback --track A --base-revision REGISTRY_REVISION --creator CREATOR --style STYLE
```

State human-approved là khai báo của operator local kèm evidence, không phải định danh người duyệt được xác thực. Không điền hộ dữ liệu xem/nghe hay thời gian sửa.

## Phạm vi nguồn

Hai provider có đường tải thật là Commons public TimedMediaHandler API và Internet Archive. Pilot Archive đã tải/decode ba original1080p qua cùng ingestion; receipt riêng ghi rõ nội dung được agent kiểm hình, chưa có human approval. Giữ license/source/creator và không tự suy training rights từ URL công khai. Nguồn tham khảo: [Commons reuse](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia), [Commons API](https://www.mediawiki.org/wiki/Extension:TimedMediaHandler/API), [Archive Metadata API](https://archive.org/developers/md-read.html).

Không có key Pexels/Pixabay được cấu hình trong môi trường hoặc MoneyPrinterTurbo của máy này. Không scrape Mixkit để mass-download vì [User Terms](https://mixkit.co/terms/) cấm cách đó. Không thêm luồng xin phép/email. Nguồn không dùng được được ghi nhận và bỏ qua; tiếp tục nguồn công khai phù hợp.

## Kiểm thử

```powershell
& $py -m unittest discover -s app -p 'test_*.py'
```

Unit/contract tests mô phỏng HTTP, split, quota, CAS/idempotency và proof guard. Live evidence gồm file public tải thật/decode/hash, neural embedding local, CUDA optimizer/checkpoint/resume/tensor load, Chrome Library UI và export native 5 giây. Người duyệt chưa xem/nghe toàn tập; không có READY, human preference hoặc model-quality improvement được xác nhận.

Các phần còn thiếu để release mục tiêu đầy đủ: đủ 1.000 nguồn relevant/retrievable, supervision quyết định dựng được creator duyệt, sửa regression B2, benchmark whole-episode độc lập có render/listening, rollout motion B và recipe C nếu thực sự cần sinh footage.
