# Goal — học cách dựng intro/demo theo reference

Snapshot mới: v007 đã train/reload thật; dev17 thêm promise theo tập và giữ
reference guidance đã duyệt. Dataset hiện dùng32train/33validation/10regression,
không thay lịch sử216nhãn bên dưới. Lượt chẩn đoán8component/4validation sources
có lỗi captions/hold; chưa đủ whole-video hoặc independent creator evidence.
Xem [diagnostic v001](VALIDATION-DIAGNOSTIC-V001.vi.md) và
[intro promise](INTRO-PROMISE-V001.vi.md). Goal vẫn chưa hoàn tất; không promote.

Goal đang ACTIVE theo yêu cầu user. Với vlog dọc5repo, user chọn phong cách
MaverickGPT: nhịp gọn, chữ nhấn và nhiều chuyển cảnh có mục đích. Tutorial dài
có thể dùng profile khác; không ép tất cả reference vào cùng một nhịp.

User chốt ưu tiên: **rules, workflow và hooks dùng lại cho các video khác**.
v035 là baseline/ca nghiệm thu, không phải template hard-code cho mọi tập.
Mọi text, asset, cue và hold phải lấy từ project hiện tại. Tách preset phong
cách khỏi nội dung và nguồn chứng minh của từng video.

“Giống hoàn toàn” được diễn giải thành độ trung thành có bằng chứng về opening,
bố cục, hierarchy chữ, chuyển động, điểm vào/ra, hold kết quả, phụ đề và sound.
Không hứa khớp100% trước kiểm định hoặc sao chép người dẫn, voice/branding.

## Prompt thực thi đã tinh chỉnh

Mở rộng đúng luồng Cutroom hiện có. Tạo một adapter ngôn ngữ chung cho intro
và demo, xuất scene JSON có thể sửa/render: component, text/asset, layout,
keyframe/easing, cue theo lời hoặc thao tác thật, hold và âm thanh. Không coi
tên preset là đặc tả animation. Renderer kiểm schema/giới hạn/vùng bảo vệ;
không thực thi code do model viết. Giữ A-roll/voice thật và mọi scene đã khóa.

Lấy transcript có timestamp từ footage; script là đối chiếu ý định/tên riêng.
Thiếu câu hoặc thao tác/kết quả: ghi pickup tại đúng nguồn, dựng tiếp phần đủ.
Reference chỉ đưa vào train/RAG theo quyền và source groups đã ghi; không đưa
tập nghiệm thu vào train hoặc retrieval. Keyframe suy từ MP4 phải đánh dấu ước
lượng. Nhãn agent thử nghiệm tách riêng nhãn người duyệt; không tự nâng thành
ground truth người dùng. Báo số thực tế, không mặc định đã đủ50video.

Train thật trên Kaggle, hash checkpoint, nạp lại bằng worker mới từ app. So
rules/base+RAG/fine-tuned+cùngRAG trên cùng footage/renderer/mức nghe. Đo riêng
intro/demo: render success, first-pass acceptance, phút sửa/phút thành phẩm,
đúng lời/proof, che mặt/nút/result, chữ Việt phone-size và SFX±1frame. Chỉ chèn
clip qua kiểm tra watermark, topology/layout và nguồn; chưa có full1×listening
thì master NEEDS_REVIEW. Giữ mọi model/cut cũ và lặp sửa theo lỗi xác nhận.

## Mốc phải đạt

- [x] User chọn MaverickGPT cho vlog hiện tại.
- [x] Giữ v035 làm baseline: file thực tế `5 repo github cho ae edit video.mp4`,
  SHAca15d2c90348ddfa33d46e2504516075689179f31e5c1d3729deffb745603c09.
- [x] Kiểm luồng hiện có: storyboard→artifact versions→edit.render→reproduction→QC.
- [x] Schema animation + native renderer, cue theo nguồn, protected regions;
  compiler giữ riêng raw validation error và mọi sửa hold/ROI.
- [x] ASR local có word timestamps/occurrence, CUDA thực tế và source-bound cache;
  đây là alignment draft, không chứng nhận đã nghe hoặc chọn take tự nhiên.
- [x] Dataset spec-conformance có split/group checks và train-only RAG;
 216 nhãn agent thử nghiệm,0 nhãn human,0 reference-timecoded gold.
- [x] Hai run Kaggle thật (128 và256 bước riêng biệt); candidate256 bước được
  import và reload bằng worker mới từ app, không bật mặc định production.
- [ ] Nhãn keyframe/flow gắn reference timecode thật, độc lập creator và được
  editor xác nhận. Ba flow đã được khảo sát, chưa trở thành gold training data.
- [ ] Intro và nhiều demo độc lập; sửa/regenerate/khóa từng scene.
- [ ] Hai bài thử khác nội dung, baseline3arms và báo cáo metrics không giả.
- [ ] User xác nhận fidelity theo mục tiêu; actual master viewing/listening.

Goal chưa hoàn tất chỉ vì loss giảm, checkpoint load được hoặc preview render
không lỗi. Các clip CogVideoX cũ bị watermark/sai thẻ không trở thành dữ liệu
nghiệm thu đạt; giữ riêng cho regression. Training spec mới không được gọi là
train tiếp cùng adapter video-diffusion vì hai nhiệm vụ/kiến trúc khác nhau.

Kết quả cụ thể: `docs/VIDEO-SKILL-INTEGRATION-RESULTS.vi.md`;
flow/provenance và pickup: `docs/REFERENCE-FLOW-ANALYSIS.vi.md`.
