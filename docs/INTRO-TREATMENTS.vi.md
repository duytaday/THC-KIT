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

### Kết quả thực tế của hai điều kiện

Code commit`f6166f5`, source dev14. A ở59516/workspace`cutroom-source-context-001`;
B ở59517/workspace`cutroom-source-context-002`. Hai condition có cùng code/media/
model package hashes. Trong từng condition, base/tuned nhận cùng context và đúng
các train-only examples; receipt xác nhận worker CUDA, adapter tắt/bật đúng mode.

|Điều kiện|Rules|Base + RAG|V006 + cùng RAG|
|---|---|---|---|
|A: vùng mặt đã kiểm, reference guidance OFF|full export|full export|full export; panel còn lệch reference|
|B: cùng vùng mặt, guidance ON|full export|full export; vẫn chọn panel|intro bị guard từ chối; demo compiled valid; không xuất master thiếu intro|

Năm exports đều118,1s/3543frames,1080×1920/30, full decode PASS,
`h264_nvenc`, −16,08LUFS/−1,65dBTP. Voice WAV/SRT và PCM audio mix sau decode
cùng hash giữa cả năm. ASR thực tếCUDA/float16 trên RTX3070Ti Laptop8GB. Không
nghe hoặc ký master từ các kiểm tự động này. SFX isolated peak/onset proxy đạt
frame gate; alignment/audibility trên final mix vẫn cần nghe.

A rules SHA4f705c2f… giữ nguyên byte so dev13; base cedb25ec…; tuned5b08061c….
B rules vẫn4f705c2f…; base f8ee5660…. Raw tunedB đặt graphic rect bằng chính
protected face rect[.16,.29,.68,.44], nên validator chặn đúng. Rationale của model
còn suy diễn reference/voice; đó là output cần phê bình, không phải evidence thật.
Chưa chứng minh thêm notes giúp model tốt hơn. Không có train mới trong lượt này.

A/B nhập ở workspace riêng có UUID asset khác, nên proof context còn khác UUID
ngoài biến reference intent. Vì vậy đây là diagnostic input-contract, không phải
causal quality ablation sạch. `inference-input-comparison.json` ghi diff thực tế;
trước lượt train/eval sau cần ổn định role/source identity mà model nhận. Cùng
condition thì base/tuned vẫn có context và retrieval giống nhau.

Lỗi hạ tầng`ui-B-v001` được giữ: harness dùng lại workspace A và thêm cutaways lần
nữa; service từ chối overlap trước generation. `ui-B-v002` chạy cùng inputs/code
trong workspace mới. Không tính lỗi này thành lỗi model, không mở final cohort.
Gallery A có3arms; B có2arms và thiếu tuned, không coi là comparison hoàn chỉnh.

Kiểm decoded phone frames xác nhận tunedA dùng panel trắng lớn và lấn tóc ở
0,2s, thay vì nền ôm chữ như sampled reference0–2,25s. Có sheet78frame intro cho
rules/base/tunedA và baseB. Không suy ra nghe/full1×watch từ sheet. Headline hiện
chỉ nói “5 repo GitHub”, chưa mô tả rõ lợi ích edit video bằng AI; đây là thiếu
sót nội dung hook cần xử lý ở proposal, không chữa bằng thêm animation tùy ý.

Gói internal dev14 build từf6166f5/source_dirty=false,153files/17.659.588bytes,
ZIP SHA61fac7b677788b5ce871845f403fb573ad34701d411915b90ca61a409a2cbdc5.
EmbeddedPython3.12.10 render đúng backend package, prefix5s/150frames/NVENC/
decode PASS, SHA8e4f3f90…. Đây là scene-preview level nguồn−22,58LUFS/−9,86dBTP,
không phải master mix pass. GUI launcher/Windows sạch chưa chạy; grant của starter
cho public distribution chưa chốt. Bản dev13/weights/cut v035 giữ nguyên.

Evidence chi tiết:`output/reference-training/source-context-v001/actual-results.json`,
`inference-input-comparison.json`, `infrastructure-failure.json`, hai UI results và
`packaged-smoke.json`. Chưa admit clip mới vào usable library; model quality vẫn
INCONCLUSIVE. Fresh episode B thật, blind whole-video reviews và phút sửa vẫn thiếu.

### Dev15 — lỗi Save của spec không có SFX

Thử sửa tunedA qua control Text background phát hiện nút Save không gửi request:
spec hợp lệ có thể bỏ trường SFX, nhưng handler gọi thẳng `spec.sfx.filter`.
Dev15 dùng mảng rỗng cho trường optional bị thiếu. Regression thực thi chính
save-handler với cả spec thiếu SFX và spec có click, xác nhận gửi đúng một request
và giữ model receipt. **243app tests PASS**, có grammar runtime thật; node syntax
check PASS. A/B giữ nguyên revision dev14, không resume/regrade bằng code mới.

Thao tác UI sau sửa tạo scene v002 thật. Harness đầu tiên báo lỗi vì so byte spec
không tính normalization từ absent SFX sang mảng rỗng; không mất dữ liệu hay tạo
scene v003. Đã kiểm diff thực tế rồi tiếp tục từ v002 để queue export riêng. Ngoài
box_style panel→lines và normalization mảng SFX rỗng, source context/spec/model
receipt được giữ. Bản sửa là agent manual repair, không phải kết quả raw model
và chưa là nhãn human-approved. Các script lỗi và v001 được giữ cạnh evidence.

Master sau sửa:`3ecf405c140b4d1cbd62e3b61ad255d9`, SHA256
`854cd1ba64d85c621a3a6211512b5261290260046dc3aff216bc59ed69b30ddc`.
Trước:`d5cde4519b344c6e9ab3c3d961009543`/SHA5b08061c…. Timecode nguồn/master
đoạn sửa giữ nguyên0–2,6s →0–2,6s. Full decode3543frames/118,1s, NVENC,
−16,08LUFS/−1,65dBTP. Voice WAV, SRT và decoded PCM mix giữ hash. Cả năm export
thử trước giữ byte; chưa gọi bản sửa là model gain hoặc READY.

Đã xem sheet78frame của v002 và selected phone frames:0,2s nền ôm headline,
45,967s contact trên Releases/caption “vào đây”,49s thấy Recordly v1.4.0,
108s CTA “5 repo github edit videos”. Đây là visual-frame observations; không
thay cho quiz ở1× hoặc full listening. Headline/meaning hook, toàn bộ caption,
audibility và proof còn thiếu của FFmpeg/Runway vẫn cần xử lý trước giao khách.
`manual-repair-verified.json` ghi đúng phạm vi kiểm, không cấp editorial sign-off.

Internal dev15 build từf2058b2/source_dirty=false,153files/17.659.583bytes,
ZIP SHA4a86dd3c63ef2c46d7ec05e76d46ff9601d7af204e08bd38f57988bf85aa97fa.
Embedded runtime thực thi package renderer trên prefix5s của bản đã sửa:
150frames/NVENC/full decode PASS, SHAd1ab19b1…. Audio là scene-preview original
level, không gọi đó là master loudness pass. Receipt:`packaged-dev15-smoke.json`;
GUI launcher/Windows sạch và human watch/listen vẫn NOT_RUN. Dev14 giữ nguyên.

Chạy lại từ **workspace mới cho mỗi condition**, không thêm lại cutaways vào A:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python app/app.py --data D:\Cutroom-new-condition --port 59518 --no-browser
# Terminal khác, cùng cấu hình runtime model/ASR và PYTHONPATH Playwright đã cài:
python app/full_video_acceptance.py --url http://127.0.0.1:59518 --config output/reference-training/source-context-v001/config-A.json --out D:\Cutroom-new-condition-results
```

Giữ f6166f5/dev14 để kiểm lại raw A/B; f2058b2/dev15 cho sửa scene thiếu SFX.
Không dùng các correction từ development5repo làm test unseen ở lượt train sau.
