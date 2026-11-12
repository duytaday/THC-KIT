# Chọn intro và nhận diện model — dev13

Trong **Generate intro & demos**, chọn một editable planner, rồi **Intro layout**:
`Full screen` giữ mặc định cũ; `Keep presenter` tạo headline phía trên người dẫn.
Đây là lựa chọn của buyer, không được chấm thành một quyết định model học được.
Headline host chỉ dùng title của tập, không xếp cả danh sách repo lên mặt. Rules
Maverick dùng nền theo dòng, headline hiện tĩnh; không tự thêm entrance vào một
headline reference vốn đã hiện tại đầu interval. Demo, lời, captions và branding
giữ riêng. Legacy native mode chưa hỗ trợ host nên control bị disable ở mode đó.

Đổi treatment tạo proposal mới, chưa tự chèn. Các cảnh cũ đã khóa/chỉnh tay vẫn
giữ nguyên; disable intro cũ khi muốn chèn proposal thay thế. Demo không đổi được
tái sử dụng, không gọi model lại. Proposal snapshot cũng giữ đúng plan đã chỉnh,
không mô tả một spec khác với cảnh thực tế. Full/default key cũ vẫn tương thích;
sáu synthetic full-context cases cho spec giống hệt commit6615bd3.

## Lỗi cache đã sửa

`ArtifactStore.generate` trước đây luôn inference trước khi tra story key; key
chỉ có mode/context/style. Vì vậy import checkpoint mới có thể tốn inference rồi
vẫn nhận cảnh của checkpoint cũ. Key mới thêm checkpoint SHA + dataset fingerprint
cho base/RAG và tuned; đổi weights hoặc retrieval dataset tạo proposal mới. Cảnh
không đổi không cần inference. Nếu candidate đổi giữa lúc generate, batch bị từ
chối và cảnh cũ giữ nguyên. Existing locked scenes không bị thay thế tự động.

233app tests PASS: host/default routing, không infer lại demo đã sửa, giữ khóa/
history, invalid inputs, weights/RAG identity và candidate race. Tests model-cache
dùng fake identities trong unit fixtures; không gọi đó là lượt train thật. UI run
riêng dưới đây dùng v006 thật. Acceptance helper đọc generation outcome đã lưu
sau thao tác UI, tránh phụ thuộc response body bị Chrome inspector evict; không
resubmit khi lỗi quan sát. Kiểm filename import còn so source hash khi có metadata.

## Chạy toàn tập qua UI thật

Workspace riêng:`D:\.codex\workspaces\talking-head-support\cutroom-intro-routing-001`,
port59515. Cùng source/script,13cutaways, proof Recordly, logo và CTA của lượt trước;
chỉ chọn intro host. Không có train mới, không mở final cohort. V006 vẫn candidate.

|Arm|Intro|Demo|Full export|
|---|---|---|---|
|Rules|render host|render proof|118,1s/3543frames, full decode PASS|
|Base + RAG|validator từ chối vùng face|compiled valid; không render riêng|không xuất batch thiếu intro|
|V006 + cùng RAG|validator từ chối vùng face|compiled valid; không render riêng|không xuất batch thiếu intro|

Rules export`e0e326d477ee4340a6cf2886617e36e7`, SHA256
`4f705c2fa89637ed7b024a24505fe3059747f44fcf53e59473f7c1c82f4ffaf2`.
1080×1920/30, AAC48k,`h264_nvenc`; −16,08LUFS/−1,65dBTP.
Voice WAV a7e1880b… và SRT343b75cb… giữ đúng hash lượt v005. Intro cùng đoạn
nguồn/master0–2,6s: từ full-screen cards sang headline host; demo44,5–55,2s giữ
đồng hồ nguồn. Smoke5s/150frames trước full render có proof, NVENC/full decode;
SHA28536700… khớp lần trước. ASR thực tếCUDA/float16; local GPU RTX3070Ti Laptop8GB.

Hai model worker nạp đúng v006 b5c78d75… trên`cuda:0`; base adapter inactive,
tuned active. Current comparison **INCOMPLETE**, không phải ba master đạt. Gallery
có một bản để review, `arms_complete:false`, `promotion_eligible:false`. Human
first-cut acceptance, phút sửa và whole-master listening vẫn chưa đo.
Selected phone frames trên rules master:44,500s thấy Releases được viền;
45,967s ring chạm Releases, caption hiện “vào đây”;49,000s trang đích hiện
Recordly v1.4.0, caption không che title. Đây là kiểm ảnh, không phải kết quả
quiz người xem1× hoặc nghe lời. Không ghi human sign-off từ các frame này.

Gói internal dev13 được build từ918fae2/source_dirty=false:17.653.827bytes,
152files, ZIP SHA256
`5a7f6c075b4e3120b96ac591ae8aa875437d4be5667a7a92190b43af3123dcb7`.
EmbeddedPython3.12.10 thực thi chính renderer trong package, xuất prefix5s có
headline/caption:150frames/NVENC/full decode, SHA8e4f3f90…; giữ nguyên full master.
Prefix là scene-preview level nguồn (−22,58LUFS/−9,86dBTP), không phải master
mix pass. Native launcher/Windows sạch chưa thử; starter grant chưa chốt cho
public distribution. Package ở D:\.codex\workspaces\talking-head-support\releases;
receipt và tested JSON ở cạnh ZIP. App source UI mới ở59515; EXE cũ giữ nguyên.

## Hai giả định cần xử lý trước khi train tiếp

1. `motion_storyboard.context` đang dùng vùng face cố định[.1,.15,.8,.4]. Model
   base tạo thẻ y=.110937..223437; tuned y=.125..25. Lỗi validator chứng minh
   giao với **vùng khai báo**, chưa chứng minh che mặt thật. Đã xem sheet78frame
   nguồn0–2,6s, PTS0..2,567; vùng trống phía trên đầu khác giả định. Cần protection
   gắn source/hash/interval/framing và bằng chứng quan sát. Không nới guard chỉ để
   pass model, không coi một ROI là đúng cho mọi take.
2. Reference được chọn là reference-1/a10c694f…; analyzer có cut candidates và
   timing profile, không tự xác nhận typography/overlay/SFX. Các facts ấy hiện
   nằm trong proposal reference_evidence, chưa được truyền vào model context.
   Context chỉ có style label/intent tổng quát. Cần nối facts đã kiểm và nguồn
   của chúng tới planner; không chép target ẩn hay reference pixels thành proof.

Diagnostic sampler đầu chỉ lấy52frame vì time bucket30fps gặp MKV time-base1ms.
Đã đọc vượt boundary cho decoder và select mọi PTS thuộc[0,2,6), tạo sheet78frame
riêng; file cũ giữ nguyên, không gọi52frame là toàn bộ. Đây là xem frames, không
phải xác nhận watch/listen1×. Không có clip nào được admit vào usable library.

Evidence:`output/reference-training/intro-routing-v001/`: protocol trước sửa,
default-full compatibility, tests, frozen UI config/implementation, actual results,
model runs và sheet/PTS sidecars. `ui-full-v001` giữ cả hai rejection, không dùng
rules fallback để giả model pass. Rules master **NEEDS_REVIEW**, quality
**INCONCLUSIVE**; bản v035 và model/cut trước được giữ.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python app/app.py --data D:\Cutroom-new-workspace --no-browser
python app/full_video_acceptance.py --url http://127.0.0.1:PORT --config D:\routing-config.json --out D:\NEW-routing-run
```

Config có `intro_layout: "host"` hoặc `"full"`; API `/api/artifacts/generate`
nhận cùng field. Không sửa frozen source/implementation rồi resume cùng trial.
Giữ6615bd3/dev12 và v006 weights để rollback; không auto-promote model từ các
kiểm thử này. Fresh episode B và capable human review vẫn cần trước release claim.

## Dev14 — quan sát gắn với nguồn

Generate intro & demos có phần Checked source observations. Vùng mặt được ghi
cho một asset/hash, source interval và kiểu fit trên canvas1080×1920. UI cho xem
video cùng hình chữ nhật; người quan sát phải ghi mình đã kiểm gì. Không có face
detector hoặc suy luận nghe trong bước này. Không cung cấp quan sát thì guard giả
định cũ vẫn được dùng; không được gọi guard đó là vị trí mặt đã đo.

Quan sát đã lưu chỉ áp dụng intro host của take ấy. Thay byte nguồn, fit, kéo
scene vượt interval đã kiểm hoặc thêm punch-in giao với scene sẽ bị từ chối.
Muốn đổi vùng phải kiểm lại qua Generate, không sửa metadata vùng mặt bên trong
scene editor để qua guard. Retry nội dung y hệt không tạo thêm history; thay đổi
thật giữ bản quan sát trước. Cảnh/model/master cũ không bị tự thay.

Reference guidance đưa tối đa ba measured candidates cùng visual notes đã ghi
vào intent của planner, có hash/source interval và nhãn audio UNVERIFIED. Không
đưa tên người duyệt làm đặc trưng model. Các notes là dữ liệu tham khảo, không
là proof của tập hiện tại, không tự đổi câu nói hoặc sao chép ảnh/chữ reference.
Reference bytes cũng nằm trong dependencies của frozen recipe/QC. Đổi reference
sau khi tạo cảnh cần kiểm lại. Buyer có thể tắt guidance mà không xóa notes cũ.

Điều kiện thử đã ghi trước ở `output/reference-training/source-context-v001/`:
A thay vùng giả định bằng quan sát nguồn, reference guidance OFF; B giữ nguyên
vùng đó và bật guidance, thêm notes từ reference-1 ở sampled0–2,25s. Cùng v006,
prompt8 và retrieval3, không retrain hay mở final cohort. Hai điều kiện là debug
trên development5repo, không phải hai lượt benchmark unseen. Notes do agent đã
thấy proposals tạo, không blind/human gold; audio và full1×master còn chờ review.
242app tests PASS gồm grammar runtime thật trước khi freeze implementation.
