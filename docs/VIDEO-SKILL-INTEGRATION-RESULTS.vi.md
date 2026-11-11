# Kết quả tích hợp skill, model worker và thư viện animation

Ngày kiểm thử local:12/11/2026 (Asia/Saigon). Đây là kết quả phát triển có log;
các MP4 thật bên dưới **NEEDS_REVIEW**, chưa có người nghe toàn master và ký duyệt.
Goal học độ trung thành theo reference tiếp tục ACTIVE.

## Prompt đã tinh chỉnh và thực thi

Kiểm upstream, license, dependencies và checkout hiện có trước khi cài. Pin
phiên bản; giữ `$talking-head-edit` làm entrypoint, một timeline giữ voice thật,
phụ đề, proof, manual locks và QC. Thêm catalog để tìm năng lực, HTML renderer
cho animation và các style workflow tùy chọn qua adapter Windows. Mọi cache,
project và preview mới ở D. Dùng footage thật tiếng Việt để thử; giữ cut cũ,
sửa lỗi đã xác nhận trong phiên bản mới, đo file xuất thật và báo khả năng nào
chưa kiểm. Không lấy cài skill hoặc train/load thành công làm bằng chứng dựng tốt.

## Đã triển khai

- Catalog469 mục từ `awesome-claude-video-skills` thành skill tìm kiếm local.
  Không chạy/cài469 dự án; nhãn security của catalog giữ là nhận định upstream.
- Bốn skill HyperFrames chính thức, pin0.9.33; renderer mới có receipt, full
  decode và output mới. Legacy workflow giữ0.8.52 để tránh đổi runtime chưa thử.
- Mười một skill Claude editing được cài vào D cùng bản gốc và source pin.
  Cầu nối Windows hỗ trợ sáu workflow gốc, local ASR, tiếng Việt đủ dấu,
  frame count, original voice, brand accent và caption corrections có bằng chứng.
  `trial-reels` giữ đủ ba output; preview có giọng được chuẩn hóa−16LUFS±2.
  Đây là CLI outputs có voice/caption riêng, chưa là11 batch presets mới; không
  chồng lên một bản voice/caption nữa. Native-spec path mới là luồng UI đã thử.
  Hiện mới **split-screen và trial-reels** đã render trên footage này. Bốn
  workflow còn lại và năm photographic templates chưa có runtime/editorial
  acceptance; cutout/model/media overrides còn cần test riêng.
- UI hiện có thêm ASR local, import adapter spec, lựa chọn rules/base+RAG/tuned,
  native scene JSON, cue/motion controls, lock và thư viện animation. Generate
  làm model/render ngoài workspace lock, kiểm revision trước khi ghi proposal.
- Animation library giữ native templates và reference excerpts riêng; clip mới
  cần kiểm watermark **và crop/baked content**. Illustration không được khai
  báo làm product proof cho tập mới. Nhập clip đã sửa hash sẽ mất hiệu lực review.
- Cấu hình EXE local lưu đường dẫn worker/model tùy chọn để mở lại không phụ
  thuộc shell đã dùng lúc phát triển. Core UI vẫn chạy khi không cài Torch/model.

Pins và lệnh từng adapter: `talking-head-qc/integrations/video-skill-set.md`.
Quyết định kiến trúc: `docs/ARCHITECTURE-RESEARCH.vi.md`.
Flow, nguồn ảnh hưởng và source/master clocks: `docs/REFERENCE-FLOW-ANALYSIS.vi.md`.

## Các file xuất thật

Các đường dẫn dưới đây tương đối với checkout; media/private models không đưa
lên Git. File voice thật đều1080×1920/30fps, H.264 NVENC + AAC48kHz, full decode
thành công. GPU local **NVIDIA GeForce RTX3070Ti Laptop8GB**, driver572.42;
ASR thực tế **faster-whisper large-v3-turbo / CUDA float16**. Log encoder trên
MP4 ghi `Lavc62.28.101 h264_nvenc`.

| Preview | Kết quả đo | Phạm vi và file |
|---|---|---|
| HTML intro HyperFrames0.9.33 |5s/150frames; silent intermediate; SHA`bb24557d6f05d555c7a27c9d66618a665c706249bcb117345cbdb68682a20565`| `output/skill-integration/hyperframes-0933-v002/intro.mp4`; project HTML cạnh file, font/GSAP/logo local; check lint/runtime/layout không lỗi, contrast53/53. Chưa căn với giọng mở bài. |
| Split-screen đã sửa |5,666667s/170frames;−16,01LUFS/−1,9dBTP; SHA`c1a62ee162278a6515d8c83e5a536cd403586736b7c1fd6a86e04deddcaf3f25`| `output/skill-integration/split-screen-pilot-v004/edit.mp4`; editable `.work/comp_main/index.html`, `spec.json`, `words.json`, `integration.json`. Screenshot tĩnh để thử bố cục, không có click/result thật trong clip này. |
| Ba trial layouts |Mỗi file5,666667s/170frames; cùng nguồn/audio; cả ba−16,01LUFS/−1,9dBTP| `output/skill-integration/trial-reels-pilot-v002/edit-1.mp4`, `edit-2.mp4`, `edit-3.mp4`; SHA/measurements riêng trong `integration.json`. Hai mẫu chữ/header và một mẫu khung; không phải so sánh mù ba model arms. |
| Native intro + demo trong master UI |20,466667s/614frames;−16,26LUFS/−1,7dBTP; SHA`26dd9c4ccc319a5d5bc3c6f7247674583ca9c743d5beebd3bb38d80cf87adf9d`| Workspace `D:/.codex/workspaces/talking-head-support/cutroom-motion-model-001`, export`ca907cb91a844fc8ab3f2f441eec5803/edit.mp4`; recipe, captions, cue sheet, stems, repeatability và six-gate QC cùng folder. Xuất từ normal batch UI. |

Master UI mới có cùng bytes với export`0a4ad9f216c547d3911d1b8e5fda6a4c` trước
đó. Đây là lần kiểm lại bằng checker đã sửa, không phải một cut mới sửa tiếng.
UI đã cập nhật đúng NEEDS_REVIEW. Không di chuyển chime đang đúng isolated cue.
v035118,1s của user giữ nguyên SHA
`ca15d2c90348ddfa33d46e2504516075689179f31e5c1d3729deffb745603c09`.

## Before/after và lỗi đã sửa

| Bản trước / timestamp | Bản sau / timestamp | Thay đổi và bằng chứng |
|---|---|---|
| Split-screenv00200:03,9–00:04,6 ghi CTI |v003/v004 cùng timestamp, tương ứng source khoảng00:06,04| Sửa thành CTA theo câu trả lời trực tiếp của user; giữ word times. Đã kiểm frame grid, chưa nghe. |
| Split-screenv00200:00–00:05,67, phần Releases bị crop |v003/v004 cùng range| Đổi screenshot detail cho thấy Releases48 và Recordlyv1.4.0. Vẫn là illustration tĩnh. |
| Split-screenv003−24,76LUFS/−10,67dBTP |v004−16,01LUFS/−1,9dBTP| Bổ sung loudness finish; video không thêm lời/giọng giả. File cũ giữ nguyên; chưa xác minh intelligibility bằng nghe. |
| Trialv00100:00–00:05,67 title rơi thành từng ký tự, header trống |Trialv002 cùng range| Pilot input dùng sai kiểu `v1.title` và sai tên `v2.headline`; sửa input, thêm pre-render validation và kiểm decoded grids. Giữ cả ba filev001. |
| Reference excerptv00100:00,067–00:00,667 mất mép trên thẻ |Excerptv002 cùng source range| Crop mới[1080,1036,0,884], giữ bản lỗi REVISE. Kiểm45 decoded frames; bản mới được thêm làm illustration, chưa là preset native hoặc product proof. |

## Hai pilot Kaggle spec đã hoàn tất

Hai run khác nhau, không cộng thành384 bước continuation. Cả hai train từ base
Qwen2.5-1.5B cùng revision pin. Corpus có29file/28hash/27families; nhưng các
pilot này train **fixtures do agent viết/rules distillation**:0 reference media
đưa vào loss,0 nhãn human và0 timecoded gold. Đây chưa là train video generator
hay chứng minh animation giống hoàn toàn reference.

| Run private | Nhãn agent / split | Kết quả thật |
|---|---|---|
| `duytruyenthong/talking-head-spec-training-c5275675676e` |108:72train/16val/20test|128 optimizer steps; val loss0,051601→0,006115; adapter SHA`4d5d666e74230ed7f109434709c48af45b30b7f23cb45acc04b59aa79cf10e4c`. Bốn fixture test: base0/4, tuned4/4. Khi áp dụng app thật, model chép tên/anchor ví dụ RAG: bị từ chối, không thế rules để báo thành công. |
| `duytruyenthong/talking-head-spec-training-1cf7830faad9` |216:144train/32val/40test|256 optimizer steps, CUDA/TeslaT4; val loss0,023063→0,006263; adapter SHA`3d06499512edff7ce4e8e98bb347e4cf26217ceab958f63c1828e04e68b7208d`. Bốn fixture test: base3/4, tuned4/4. Candidate import từ ZIP và worker mới của app nạp đúng weights. |

App thật có hai proposal tuned, raw output đều cần compiler xử lý: intro hold60
vượt budget52; demo ROI lấy từ fixture. Compiler ghi raw error + before/after,
bind ROI theo source hiện tại, không sửa text/anchor bịa. Hai scene sau compile
đã render qua UI vào master. Không báo raw model đạt2/2 hoặc chất lượng hơn.
Các fixture scores không thay đánh giá trên tập độc lập chưa dùng làm mẫu.

`first_pass_acceptance=null`, `repair_minutes_per_output_minute=null`:
chưa có lượt duyệt/editor timing đủ để đo. Production adapter vẫn không auto
bật làm default. Nhãn flow khảo sát mới giữ agent-experimental/estimated.

## Kiểm thử và smoke thực tế

-82 app tests,51 QC-tool tests,39 reference-lab tests: **172 PASS**.
  `node --check app/ui/app.js` và `git diff --check` qua.16 skill folders qua
  validator, gồm catalog +4 HyperFrames +11 Claude editing. Đây là kiểm schema
  cài skill, không phải16 workflow được editorial approval.
- `smoke_test.py`:v001 phát hiện quiet audio/caption quá range;v002 qua kỹ thuật
  nhưng NEEDS_REVIEW; bỏ required beat bị REVISE, đổi brief mất review cũ.
- `final_qc_smoke.py` lầnv001 thất bại kỳ vọng READY vì periodic tone có nhiều
  correlation peaks. Giữ nguyên run/log này. Checker xử lý đúng là UNVERIFIED.
  Đổi positive fixture sang chirp có mốc duy nhất, giữ tolerance1frame.
- Full smokev002: original và trim hợp lệ READY **chỉ trong synthetic fixture**;
  che proof/sai critical caption/audio không retime REVISE; thiếu nghe/stale
  review NEEDS_REVIEW. Trim15frames dời click42→27,wipe78→63,chime123→108;
  control trước trim giữ frame3. Kết quả ở
  `output/skill-integration/final-qc-smoke-v002/results.json`.
- EXEdevv011/v012 mở workspace D, HTTP200,2 editable scenes/4 library entries,
  candidate256 bước, không JavaScript error, MP4 Range request206. Model/runtime
  paths nằm trong local launcher-config. v012 còn được mở với shell không truyền
  UTF8 flags: ASR CUDAfloat16 trả tiếng Việt đúng mã, script đã sửa giữ nguyên.
  Worker ép UTF8 và cache model mặc định trên D. Chưa kiểm clean Windows chưa cài gì.

Lệnh kiểm lại từ checkout:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python -m unittest discover -s talking-head-qc/tools -p 'test_*.py'
python -m unittest discover -s talking-head-qc/reference-lab -p 'test_*.py'
node --check app/ui/app.js
python talking-head-qc/tools/smoke_test.py --skill-root PATH_TO_FFMPEG_SKILL
python talking-head-qc/tools/final_qc_smoke.py --out NEW_FOLDER --skill-root PATH_TO_FFMPEG_SKILL
python app/app.py --data YOUR_LOCAL_WORKSPACE
```

## Release còn chờ gì

Reviewer có audio phải nghe toàn exact master1×, xem ở phone size và ghi evidence
cho cả sáu gate, kiểm sync theo decoded MP4. Agent hiện chỉ có ASR/frame inspection;
chưa nghe, chưa chứng nhận full normal-speed viewing hoặc quyết định bố cục cuối.
Click master00:07,033/frame211 và result00:10,067/frame302 có isolated peak0frame;
final mix có voice che/correlation cạnh tranh nên audibility/alignment còn chờ nghe.
Demo zoom Recordly ở lời00:16,35–00:18,49 cần capture bổ sung; toàn vlog vẫn cần
đủ proof riêng của cả năm repo. Mẫu intro5s cần căn lại với câu mở thật.

Đánh giá reference fidelity, blind unseen-episode3arms, metric sửa tay và user
chốt style còn mở. Không đưa các sample layouts, decorative REC badge hoặc ảnh
kết quả từ reference thành bằng chứng một capture/lượt chạy mới đã thành công.
