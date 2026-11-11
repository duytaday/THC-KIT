# Lượt planner chuyển động v004

Trạng thái: **thử nghiệm, chưa bật cho khách**. Lượt trước có JSON hợp lệ nhưng
các thẻ của model đứng yên. Lượt này sửa khả năng biểu diễn, dữ liệu và cách lấy
mẫu trước khi kết luận phải train nhiều hơn. Chưa có phán quyết style hoặc nghe
master của một reviewer có audio. Vlog5repo vẫn là development/regression.

## Những thay đổi đã kiểm được

- Native keyframe thêm `rotation` tùy chọn, −45..45độ, mặc định0. Thẻ, chữ và
  gạch nhấn dùng chung tâm; góc cuối phải về0 để chữ đứng yên khi đọc. Triển khai
  theo [ASS rotation/origin](https://aegisub.org/docs/latest/ass_tags/).
- Validator kiểm vùng bao xoay theo kích thước pixel1080×1920 ở từng frame.
  Marker target/contact/result không được xoay hoặc trôi khỏi ROI thật. Decoder
  chỉ cho rotation0 trên các marker này; kiểm native vẫn là bắt buộc.
- UI có Entrance tilt. Đổi thời lượng căn lại toàn bộ keyframe theo tỷ lệ,
  giữ thứ tự frame và hướng/độ overshoot; không chỉ kéo key cuối qua key giữa.
  Mute/gain của từng sound và music giữ riêng. Scene đã khóa không bị ghi đè.
- Render lại riêng motion rows của intro rules cũ cho **913 dòng ASS giống hệt**
  khi rotation thiếu/mặc định0. Đây là kiểm tương thích intro đã nêu, không phải
  chứng nhận toàn bộ project cũ hay full listening.
- Benchmark nhận scene animation đã sửa tay là revision, kể cả nó nằm trong
  MP4 đầu tiên của workspace; không tính nhầm thành đề xuất model được giữ ngay.

Smoke qua UI dùng5giây footage thật từ selected camera cut của1.mp4, có captions
và animation. Control đổi keys0/4/9 thành0/8/18, góc−8/5/0 thành−12/7,5/0,
giữ script và scene khóa khi tạo lại storyboard. Export:
`729470203b8849faa10daaba3ce11663`, SHA
`67de87cdd2567294a676611c225126e2d4af9207962466478addfc529c01dc40`.
Đã decode đủ150frames, h264_nvenc,1080×1920/30. Đã nhìn frame phone360px;
**NEEDS_REVIEW**, chưa xem/nghe trọn1×. Đây là test control bằng rules/manual,
không phải bằng chứng fine-tuned model đã sinh được chuyển động đó.

## Dữ liệu gắn với source clock

Một số contact sheet cũ ghi PTS sau `fps`, trong khi ảnh được chọn có thể nằm
giữa các mốc đó. Bộ tạo sheet nay dùng `select`, giữ PTS gốc, ghi danh sách từng
frame thật và SHA ảnh vào sidecar. Test trên source30fps so trực tiếp với
`ffprobe`: sample ở0,100 và0,367s, không gán lại thành đồng hồ0/0,25. Không
đọc timestamp sau lấy mẫu thành frame tiếp xúc chính xác của footage gốc.

Đã kiểm các source7/11 bằng sheet có source PTS. Phần ảnh hưởng nhãn mới:

| Source | Khoảng nguồn | Phần học và giới hạn |
|---|---|---|
| reference7 |00:00,600–00:01,533;00:04,700–00:05,667;00:06,200–00:07,167|Enter/spin/settle của ChatGPT, Perplexity, ElevenLabs được chiếu thành native text badge; không học lại pixel logo hoặc xác nhận âm thanh|
| reference11 |00:00–00:03,600|Wikipedia → Google → Perplexity xuất hiện ở ba slot; fade ước lượng|
| reference11 |00:03,700–00:06,667|Grok → Claude → ChatGPT; sửa onset và điểm reset từ source clock|
| reference11 |00:07,200–00:10,700|Canva → Claude → Meta Muse; giữ trạng thái cuối trong đúng cửa sổ|
| reference11 |00:14,800–00:18,800|Runway → HeyGen → Higgsfield; last reveal dài hơn hai reveal đầu|

Keyframe gốc không có. Các đường đi/góc/easing trên text là **ước lượng tái
dựng**, chưa phải original editor gold hoặc full visual match. Tên được quan
sát trên hình; không gọi mốc này là từ đã nghe. Không label SFX chưa nghe.

Ba mẫu Claude/Lovable/Codex đang đề xuất từ source7 bị loại: thời gian logo
settle ngắn không đủ làm chữ đọc được với font/hold tối thiểu của native.
Không bịa thêm source hold để đủ schema. Các headline tĩnh đúng nguồn được giữ,
không biến mọi nhãn mang tên Maverick thành animation.

Hai fixture6thẻ tiếng Việt (quy trình sản xuất/chăm sóc khách hàng) là đồ họa
house nguyên gốc. Chúng dạy contract bố cục/settlement, **không tính là motion
reference gốc**. Không dùng lời/pixel của5repo để tạo chúng. Bản dữ liệu tạm
`818d775c...` giữ để audit, chưa upload; chỉ bản so lại dưới đây được gửi.

## Lượt Kaggle

Dataset `8fa585d3445f075ca807b3ab8a49a9ffdb81de8ff5999ab06e8205a3de683d06`:
32train/33validation/10test. Train có9moving entrances;7là native projections
từ reference,2là house fixtures. Human gold0; raw media upload0. Các con số là
số nhãn, không phải số bản quay hay creator độc lập.

Facebook collection trước là validation nay được retire sang train. YouTube
collection trước ở train được giữ ngoài optimizer/RAG cho lượt **fresh base**
này; nó vẫn là corpus đã biết qua lịch sử phát triển, không phải unseen quality
test. Không resume adapter cũ. Source hash và conservative collection group đi
cùng split; creator independence chưa xác minh. Manifest ghi toàn bộ lineage.

Prompt6/retrieval3 ưu tiên role, proof, yêu cầu bố cục và style từ input trước
word overlap. Không dùng target để truy xuất. Checkpoint cũ giữ prompt/retriever
của receipt cũ. Corpus/mẫu tối đa3014tokens, dưới3072, không truncate.

Train định trước192 optimizer steps, lấy luân phiên5loại quyết định. Lịch ghi
ID mỗi mẫu và chỉ ghi vào applied IDs khi optimizer thực sự bước; skip gradient
không làm mất mẫu. Một proof fixture được lặp38lần không trở thành38nhãn hay
38nguồn độc lập. Receipt giữ class counts, schedule và update thật.

Private kernel:
[talking-head-spec-training-8fa585d3445f](https://www.kaggle.com/code/duytruyenthong/talking-head-spec-training-8fa585d3445f).
Kernel version1 đã **COMPLETE**, receipt ghi192 optimizer steps áp dụng,
applied IDs khớp schedule, CUDA0,252,911s train và delta weights L2=4,547723.
Hai TeslaT4 có sẵn nhưng chỉ dùng device0; peak8.895.260.672bytes. Checkpoint:
`36aee981d7a33c8c6ea1ea0115a2f195f73484617fd2eb4e60368216548fae54`.
Hash từng file adapter tải về khớp receipt; style counts31maverick_fast/1balanced.

Validation loss **0,820162 →1,258959, xấu hơn**. Không gọi lượt này tốt hơn hoặc
giải thích nguyên nhân như một kết luận đã đo. Raw schema diagnostic: cả hai arm
intro0/2; base demo0/2, tuned demo1/2. Chẩn đoán này chưa có grammar/compile của
luồng UI và không phải whole-video quality score. Adapter tiếp tục production
ineligible; cần kiểm render thật trước khi quyết định bước tiếp.

Đã đợi đúng kernel RUNNING tới terminal, không restart khi API output chưa có
file. Sau terminal đã dừng riêng lượt download cache base2,88GB dư thừa và lấy
adapter/package/report bằng `kernels output --file-pattern`, cùng kernel đó.
Không train lại, không gọi việc dừng download là model failure. Bằng chứng ở
`poll-003/talking-head-motion-spec`; bản tạm download trước vẫn riêng trên D.

## Sửa proof trước lượt toàn tập mới

Kiểm mid-frame của12 cutaway ở360px tìm được artifact trên bản thử rules/tuned
cũ:01:00,833, cảnh Remotion còn lộ omnibox đang nhập URL fal. Trang
phía dưới vẫn là Remotion; không ghi sai rằng nó đã điều hướng thành công.
Đã lưu partial negative review vào hai master cũ và giữ nguyên MP4/history.

Asset sửa dùng đoạn sạch0–1,3s của chính bản Recordly đã có, giữ frame nguồn
1,266667s cho đủ2,8s; không quay mới hoặc bịa giao diện. NVENC/decode84frames.
SHA `7abda19211d3bb94df04cc0020bb32e9db014767727bcad1ed911213f239edd2`.
Mốc01:00,833 →01:00,833, beat `remotion-github`; voice/caption không dịch.

Cấu hình toàn tập mới còn thêm logo cộng đồng9,24–12,12s bằng UI, giống nhau
ở ba arm. File trên D khớp đúng SHA asset user đã đưa trên E:
`e6052ebaed68c68bdb66cc5dc1b0bed7e4ed648a740b9fde9642ca83e87c7e02`.
Những sửa nguồn/branding chung không được tính là thành tích của fine-tuning.

## Kiểm thử UI và sửa compiler chung

Lượt `ui-full-v001` xuất được rules; base báo thiếu `contact` dù anchor nguồn
đã được cấp; tuned đặt key đầu ở frame1 của scene thay vì frame0 của object.
Hai model arm bị từ chối và không bị thay bằng rules. Raw output, lỗi và master
rules được giữ lại; đây là thất bại đầu vào/contract, không phải chất lượng đạt.

Compiler nay bỏ một missing note chỉ khi nó khớp chính xác tên anchor thật có
source PTS hoặc repo đã được cấp trong proof `real_screen`; các pickup khác
vẫn giữ. Đồng hồ keyframe chỉ được đổi khi key đầu khớp chính xác onset đã cấp
của object: trừ cùng một offset khỏi tất cả keys, giữ nguyên khoảng cách/pose
và source anchor. Clock mơ hồ vẫn bị từ chối. Raw schema error, semantic flags
và từng repair được ghi riêng. Không quy thành tích sửa compiler cho model.

Asset đã ghi rõ là illustration/reference excerpt không được gắn lại thành
proof thao tác thật. Context version3 tạo scene mới, giữ scene/version cũ.
Harness khóa hash implementation để không ghép arm trước/sau sửa code.

Đã chạy **266 test đạt**:174 app (có optional decoder),53 QC,39 reference lab.
Lượt đầu chạy app thiếu optional decoder có11 skip; lượt xác nhận đã nạp đúng
runtime và chạy đủ174, gồm kiểm chặn non-proof trước cả legacy/model generation.
Đây là kiểm kỹ thuật, không thay phần nghe/duyệt style.

## Nghiệm thu toàn tập

Lượt `ui-full-v002` đã hoàn tất qua UI bình thường, không có page error hoặc
rules fallback. Cả ba master dài118,1s,1080×1920/30fps, decode đủ3543frames,
audio−16,08LUFS/−1,65dBTP, encoder thực tế `h264_nvenc`. SHA voice WAV và SRT
giống nhau ở cả ba arm; playback loudness chênh0LU. Controls so sánh đều khớp.

| Arm | Export ID | SHA-256 MP4 |
|---|---|---|
| rules |bc4fcd9baaa84f06af7f570744c193de|81ca744415630eff989515c68444252960ec310f111f24cb42bfc7a975f92680|
| base + RAG |b384fcefe47f448f814033de0001aa1b|a9cad732791549559ed6f2002bdf975f1c06bb1a29b0efda9b204294a67068bd|
| tuned + cùng RAG |684c796a19e8451db93c2418a58f942f|d46136c8a12b142e83c28aea4a0e4bd0b44f21023b4f22f9ad72deabc65bb7b3|

File từng arm nằm ở
`D:\.codex\workspaces\talking-head-support\cutroom-motion-model-004\exports\<ID>`:
`edit.mp4`, `captions.srt`, `project.json`, `render-project.json`, `timeline.json`,
`cue-sheet.json`, `qc.json`, `qc.md`, fonts và dependency receipts. Project này
tham chiếu selected camera cut; mapping cắt về1.mp4 gốc vẫn ở
`output/5-repo-ai/cut-list-v005.json`. Không gọi lượt này là chọn lại take mới.

Base tạo6 entrance1frame, không có góc xoay. Tuned tạo6 entrance9/12/15/18/21/24
frames, góc±3độ về0. Đã nhìn decoded stills ở360px: thẻ/chữ cùng xoay, chữ Việt
không vỡ ở các frame đã kiểm. RAG của hai model arm giống nhau, có house geometry
6thẻ. Chưa xem motion trọn1× hoặc chấm độ giống reference; không gọi đây là style
gain đã chứng minh. Hai trong bốn model scene cần compiler như ghi ở trên.

Cả ba vẫn **NEEDS_REVIEW**. Intro rules có slide ở00:00,033; model intro hiện
không có SFX. Click ở00:45,967, result/chime ở00:49,000. Isolated SFX peaks khớp
frame đã gán; tương quan click/chime trong decoded final mix chưa đủ tin cậy nên
để UNVERIFIED, không suy thành đã nghe. Hai model worker thực sự chạy CUDA;
base tắt adapter, tuned bật đúng checkpoint36aee…ae54.

Đã kiểm các frame logo00:10,500, Remotion01:00,833, CTA01:48,500; cảnh Remotion
sạch và CTA đúng “5 repo github edit videos”. Giá fal có số và đơn vị per second
trên frame01:30,433; Runway có trường promptImage ở01:40,133. Đây là quan sát
ảnh, chưa xác nhận độ đọc/khớp lời tại tốc độ thường hoặc kết quả một lượt chạy.

Benchmark có2 câu trắc nghiệm hình và1 câu mở về chữ bị che. Đáp án được lập từ
frame nguồn, ghi agent visual-only, không đưa vào public review; hai file private
bị HTTP404. Đã kiểm UI390px: player tập thực tế294px, không tự play hoặc submit
review. Form đầu tiên đo nhầm video reference đang đóng là0px; bản xác nhận
`phone-layout-verification.json` ghi selector đúng và giữ receipt đầu để audit.

Mở bài so mù trên máy đang chạy:
[Review ba master](http://127.0.0.1:59507/benchmarks/60e844118b9b458a8f9cbe7926cf645b/index.html).
Hiện0 full review,0 unseen review, first-pass acceptance và repair minutes/minute
đều `null`; `model_improvement=null`, `promotion_eligible=false`.

Planner vẫn có pickup flags cho4 repo khác ngoài Recordly, trong khi các
cutaway thủ công của chúng đã được cung cấp và có trong master. Cần nối rõ từng
claim/action/result tới nguồn và duyệt nội dung; không kết luận rằng4 nguồn ấy
đều chưa có, cũng không dùng Recordly thay proof của cả5 repo. Bản thử này tập
trung planner, music tắt; chưa bao gồm toàn bộ treatment10–20s/SFX của v035.

GPU máy: **NVIDIA GeForce RTX3070Ti Laptop GPU8GB**, driver572.42. ASR thực tế
`cuda / float16` với faster-whisper turbo; log encode và smoke150frames xác nhận
NVENC. Ba bản `.recordly` mới trỏ media trên D, giữ project cũ; đây là repath
project đã có, không phải quay lại demo. Hardware/encoder/runtime logs đều trên D.

Vẫn cần vlog raw mới + script/branding, và reviewer có khả năng xem/nghe để đo
first-pass acceptance, câu trả lời viewer, repair time và style preference.
Không có số đo mới thì model gain để N/A. Không đưa clip chưa kiểm watermark/
layout vào thư viện usable. Source đang ở0.14.0-dev6; chưa build EXE thay RC4.

Bằng chứng local: `output/reference-training/reference-spec-v004`; launcher
`start_local.ps1` mở workspace004 trên `http://127.0.0.1:59507`. Các bản và
checkpoint trước được giữ; thư mục nguồn/cache/output của lượt này đều trên D.

## Lệnh trên máy đang kiểm thử

Chạy từ checkout root. Launcher bên dưới là file riêng của lượt thử, chứa
đường dẫn runtime/base/decoder trên D, không chứa token. Server59507 hiện đã
chạy; chỉ dùng launcher khi cần khởi động lại và không có render đang chạy.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$kitModelPython='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-animation-model\Scripts\python.exe'
$kitPython='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-structured-decoding-0113'
& $kitModelPython -m unittest discover -s app -p 'test_*.py'
& $kitPython -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
& $kitPython -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py'
node --check app/ui/app.js

powershell.exe -NoProfile -File output/reference-training/reference-spec-v004/start_local.ps1
```

Trong terminal khác, dùng thư mục output chưa tồn tại để không ghi đè:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$kitPython='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:PYTHONPATH='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-test'
& $kitPython -X utf8 app/full_video_acceptance.py --url http://127.0.0.1:59507 --config output/reference-training/reference-spec-v004/ui-config.json --out output/reference-training/reference-spec-v004/ui-new-comparison
```

Các lệnh này dùng media/model riêng đã có trên D. Source0.14.0-dev6 đã kiểm
trực tiếp; chưa có EXE mới của lượt này. Không gán kết quả source này cho RC4.
