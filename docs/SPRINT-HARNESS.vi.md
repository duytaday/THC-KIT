# Harness sprint · Batch và bộ đăng bài

Profile `sprint` mở rộng `app/editing_replay.py` và dùng lại controller
`app/hillclimb.py`. Profile mặc định tiếp tục chạy T1–T8. Sprint so hai
checkout độc lập dưới cùng runtime, cùng fixture và cùng grader. Chỉ cấp
quyền đọc fixture development đã khai trong campaign. Giữ mọi bản cắt, turn
và bản xuất của một họ nguồn ở cùng split. Allowlist của ứng dụng không phải
cách ly quyền truy cập của hệ điều hành.

| Ca | Cách kiểm trên luồng sản phẩm |
|---|---|
| Batch resume | Public CLI dừng sau tập đầu. Tiến trình mới resume. So export ID, SHA-256 và số event EXPORTED của tập đầu. |
| Demo đủ nguồn | Hai capture có action và mốc riêng. So hash nguồn trong kế hoạch đã render, mốc kết quả và pickup. |
| Demo thiếu | Tập Save vẫn có draft và pickup. Kế hoạch xuất không gán phần minh họa làm screen proof. |
| Thumbnail | Qua API mà Outputs dùng, lưu hai thiết kế và tải hai ZIP. So từng member với manifest, đối chiếu MP4 và revision. |
| Bìa trong video | Xuất bìa mới qua queue. Decode MP4, so revision, hash, frame đầu, audio, SRT và QC. |
| Cache ZIP | Làm hỏng đúng file ZIP trong workspace thí nghiệm rồi tải lại. Kiểm hash các member và hash master. |
| Liên kết revision | Tải gói cũ và gói mới sau khi đổi bìa. So export ID, revision và ba hash. Thử manifest ghi nhầm revision trong fixture và yêu cầu HTTP 409, sau đó khôi phục manifest. |

Giữ cả thư mục `talking-head-qc` bên cạnh `app` ở mỗi checkout để CLI nạp được các hook QC.
Hai tree phải giống nhau trừ đúng `changed_path` trong thư mục `app`. Kiểm
diff trong file để đảm bảo chỉ đổi một quyết định. Thay grader cần freeze
campaign mới. Hòa hoặc critical regression giữ baseline. Kết quả cơ học không
đủ để promote model hay duyệt bản thật.

## Chạy trên D

Từ checkout trên D, nạp runtime dự án. Dùng một thư mục thư viện trống để lượt
test chỉ dùng tài sản khai báo. Dùng cùng QC skill local cho hai arm.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py = $env:THC_PYTHON
$env:THC_ASSET_LIBRARY = 'D:\thc-eval\empty-library'
$env:CUTROOM_QC_SKILL = 'D:\path\to\ffmpeg-skill'
& $py app/hillclimb.py freeze D:\thc-eval\campaign.json --out D:\thc-eval\trial
& $py app/hillclimb.py start D:\thc-eval\trial\trial.json --id zip-integrity-001 --hypothesis 'Recover corrupt ZIP' --variable 'Cache validation'
& $py app/hillclimb.py run D:\thc-eval\trial\trial.json --id zip-integrity-001 --cost 0
& $py app/hillclimb.py status D:\thc-eval\trial\trial.json
```

`replay_config` trỏ tới JSON với `profile: "sprint"`, `manifest`, `catalog` và
`preset` là đường dẫn tuyệt đối. Manifest theo [schema headless](HEADLESS-AUTO-EDIT.vi.md)
có ba tập `01`, `02`, `03` và mỗi tập có `technical_fixture: true`, recording
và script. Catalog theo thứ tự Export và Add subtitles, cả hai đánh dấu
`technical_fixture: true`, có hash, quyền và mốc action/result. Tập 03 nói về
Save và thiếu capture. Dùng fixture tự tạo, giữ video và audio khách hàng ngoài
profile này. Preset gồm tất cả trường lock muốn kiểm.

Campaign dùng `scope: "development"`, `baseline` và `challenger` là đường
dẫn `app` của hai checkout, `changed_path` là đường dẫn tương đối trong app.
Khai `grader`, `cost_unit`, `budget.max_cost`, `budget.max_wall_seconds` và
`cases`. Ghi SHA-256 của mọi recording, script, capture, manifest, catalog và
preset trong `cases[].media_sha256`. Không nhập manifest validation/sealed vào
sprint optimizer. Dùng một thư mục mới mỗi campaign. Controller nhận lại kết
quả hoàn tất có cùng snapshot sau gián đoạn. Nếu receipt chưa hoàn tất, kiểm
process và log hiện có trước khi chạy thử ở thư mục khác.

Kết quả mỗi arm gồm `frozen-inputs.json`, `results.json`, lệnh CLI, trace HTTP,
workspace, QC và MP4 cũ/mới. Điểm sprint là số ca cơ học đạt chia tổng số ca.
Giữ thời gian chạy máy riêng với thời gian creator sửa tay.

## Kết quả v004 ngày 21/11/2026

Vòng `zip-cache-integrity-001` dùng baseline `3be2c3c`, cùng bộ input và grader `e3f8abfd85241d0984052531f31c9e4680154b2b7120c397b0e5caa8ea2d13b1`. Challenger chỉ đổi cách xác minh ZIP cache trong publish.py.

| Ca | Baseline | Challenger |
|---|---|---|
| batch_resume | PASS | PASS |
| assigned_proof | PASS | PASS |
| missing_demo | PASS | PASS |
| thumbnail_revision | PASS | PASS |
| cached_bundle_integrity | FAIL | PASS |
| cover_revision | PASS | PASS |

Baseline chạy 85.16 giây. Challenger chạy 85.69 giây. Kết quả controller là `gain` với critical regression = `false`. Chi phí API 0 USD. Không có reviewer nghe/xem toàn bản hay dữ liệu độc lập để chấm chất lượng dựng.

Public CLI dừng có kiểm soát sau tập đầu rồi tiếp tục bằng tiến trình mới. Tập Save thiếu capture vẫn xuất draft và pickup. Hai gói thumbnail trong mỗi arm giữ đúng hash MP4. Bản có bìa mang revision và hash mới, giữ PCM và SRT của bản trước.

Các lượt trước được giữ riêng. v002 phát hiện grader đọc nhầm plan đã lược đường dẫn. v003 phát hiện đường dẫn libass của challenger dài hơn giới hạn Windows quan sát được. v004 dùng đường dẫn D ngắn và tên thư mục arm dài bằng nhau, đồng thời kiểm đủ A/B/C ở cả hai arm.

Hồi quy app 441 ca, 428 đạt, 13 skip. Cả hai checkout thử dùng fixture tổng hợp. Giữ `NEEDS_REVIEW` cho master và giữ nguyên model đang dùng.

## Kết quả kiểm revision ngày 21/11/2026

Vòng `posting-revision-binding-001` so baseline `8f9ce9d` với challenger chỉ đổi `app/publish.py`.
Dùng cùng ba episode tổng hợp, cùng FFmpeg với `libx264` và cùng grader.

| Ca | Baseline | Challenger |
|---|---|---|
| `batch_resume` | PASS | PASS |
| `assigned_proof` | PASS | PASS |
| `missing_demo` | PASS | PASS |
| `thumbnail_revision` | PASS | PASS |
| `cached_bundle_integrity` | PASS | PASS |
| `cover_revision` | PASS | PASS |
| `posting_revision_binding` | FAIL | PASS |

Baseline 80.95 giây. Challenger 78.12 giây. Chi phí API 0 USD.
Cả hai tải được bộ cũ và mới sau khi đổi bìa. Với manifest thử nghiệm ghi sai revision,
baseline trả HTTP 200 và challenger trả HTTP 409. Bộ sau khi đổi thumbnail giữ nguyên hash MP4.
Bìa trong video tạo revision mới, giữ PCM, SRT và thời lượng. Tập thiếu demo Save giữ draft và pickup.
Bộ regression ứng dụng chạy 446 ca, 433 đạt và 13 skip.

Controller ghi `gain`, không có critical regression. Master fixture giữ `NEEDS_REVIEW`.
Không có lượt duyệt nghe/xem thật và không thăng cấp model.
[Receipt kiểm tra và hash](evidence/sprint-posting-revision-v001.json).

## Kết quả kiểm frame thumbnail

Vòng `posting-design-binding-003` chạy cùng ba fixture development, cùng
FFmpeg `libx264` và cùng grader. Challenger chỉ thêm kiểm tra mã định danh
gói từ thiết kế thumbnail và caption đã lưu trong `app/publish.py`. Ca mới
đổi `source_frame` trong manifest của gói cũ, giữ nguyên revision và hash của
MP4, caption và thumbnail. Baseline trả HTTP 200. Challenger trả HTTP 409.
Cả hai arm vẫn từ chối manifest sai revision.

| Arm | Ca đạt | Thời gian máy |
|---|---:|---:|
| Baseline | 6/7 | 92.20 giây |
| Challenger | 7/7 | 77.67 giây |

Cả hai resume batch bằng tiến trình mới và dùng lại export ID cùng SHA-256
của tập đầu. Tập Save giữ draft và pickup. Đổi thumbnail giữ nguyên MP4 và
revision. Đổi bìa tạo revision và MP4 mới, giữ bản cũ, PCM và SRT. Hai gói
cũ và mới đều tải được sau khi đổi bìa. Controller ghi `gain`, critical
regression bằng `false`, chi phí API 0 USD. Unit tests đạt 434/447,
skip 13. Đây là kiểm thử cơ học trên fixture tổng hợp. Trạng thái QC
vẫn là `NEEDS_REVIEW` và quyết định chất lượng model vẫn là `INCONCLUSIVE`.

[Biên bản và hash](evidence/sprint-posting-design-v001.json).
