# Thử nghiệm planner animation · 12/11/2026

Trạng thái giao khách: **chưa bật adapter**. JSON hợp lệ và log train không
chứng minh rằng một video tốt hơn. Phải so mù các **bản toàn tập** cùng nguồn,
renderer và mức nghe, kiểm đủ sáu gate, câu trả lời người xem và thời gian sửa
thực tế trên tập mới. Vlog “5 repo” hiện là bài phát triển/hồi quy.

## Chẩn đoán adapter cũ và decoder

Checkpoint cũ giữ nguyên:
`869444f8c7f28742e04287a8a346a40e202fe7689da5b3734a44e41f456a9818`.
Chạy bốn worker thật trên CUDA, cùng hai input intro/Recordly, cùng RAG, prompt,
seed và ngân sách 2.200 output tokens. Cả hai nhánh đều nạp checkpoint; nhánh
base tắt chính adapter đó. Không chèn kết quả rules khi model bị từ chối.

| Planner | Decoder | Intro | Recordly demo |
|---|---|---|---|
| Base + RAG | Unconstrained | Lead trước giới hạn nguồn | Evidence type sai |
| Fine-tuned + cùng RAG | Unconstrained | Chữ ngoài inventory | Native schema đạt, 0 compiler repairs |
| Base + RAG | `source_json_v1` | Va vào vùng face mặc định của input | Native schema đạt |
| Fine-tuned + cùng RAG | `source_json_v1` | Va vào vùng face mặc định của input | Native schema đạt |

Decoder chỉ lọc cú pháp và các lựa chọn gắn với input: nguyên văn text, anchor,
loại proof và contact/result cho click/chime. Nó giữ nguyên miền native spec,
không thay bằng template. Native validator vẫn kiểm hình học, chữ vừa thẻ,
vùng bảo vệ và hold. Thư viện không đảm bảo đầy đủ numeric bounds; không dùng
grammar làm thay thế validator hoặc QC. Intro bị chặn đúng, chưa có full master
mới từ thử nghiệm này. Không có bằng chứng fine-tuning cải thiện chất lượng.
Vùng face này là giả định template, **chưa đo trên source**. Frame gốc0,5s cho
thấy khoảng trống phía trên đầu; không gọi native rejection là một lỗi che mặt
đã nhìn thấy trong MP4. Host-layout cần xác định vùng mặt thật trước khi dùng
kết quả collision làm điểm chất lượng.

Runtime tùy chọn: `lm-format-enforcer==0.11.3`, cài riêng trên D, không nâng
dependency của app chính. Request/receipt lưu decoder, SHA prompt/schema/code,
output thô, native error và compiler repairs. Worker báo decoder khác yêu cầu
thì từ chối. Mặc định vẫn `unconstrained`.

Chạy với model/runtime đã cấu hình:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$env:CUTROOM_ANIMATION_DECODER='source_json_v1'
$env:CUTROOM_ANIMATION_DECODER_SITE='D:\.codex\workspaces\talking-head-support\runtimes\cutroom-structured-decoding-0113'
# CUTROOM_ANIMATION_PYTHON và CUTROOM_ANIMATION_BASE trỏ runtime/base pinned hiện có.
python app/app.py --data D:\Cutroom-experiment --no-browser
```

Bằng chứng private: `output/reference-training/constrained-v001/paired-worker-001`.

## Vì sao đổi dữ liệu trước khi train thêm

Train cũ có 14 intro nhưng **0 intro toàn màn hình**. Chúng chủ yếu là một title
giữ nguyên trên host; không thể coi việc train nhiều bước hơn là học được montage,
calendar flip hay nhiều lớp chuyển động.

Đã xem decoded sheets 0–45s của bốn reference dài, thêm một số frame lớn để
đối chiếu chữ. Những mốc ảnh hưởng các nhãn mới gồm:

| Reference ID | Timecode nguồn | Điều quan sát và phần native đang học |
|---|---|---|
| `8OYWaTK-wRU` | 00:04.5–00:10.8 | Nhiều thẻ câu hỏi chuyển thành đầu việc; hierarchy text |
| `8OYWaTK-wRU` | 00:14.5–00:26.4 | Lộ trình rồi ba ví dụ ứng dụng; chia cụm/giữ kết quả |
| `mM0YzxgeyJQ` | 00:01.5–00:03.7 | “hơn 1000 giờ” vào vị trí; entrance ước lượng |
| `mM0YzxgeyJQ` | 00:11.4–00:21.9 | Nhóm thumbnail/quảng cáo/Shorts rồi card khóa học |
| `ObhrJogXI7w` | 00:02.5–00:15.6 | End-state số 100.000 → 100 → 7; chỉ học chữ/end-state |
| `xOt-IeTRTsQ` | 00:03.5–00:04.8 | Title “Claude 2.0”; entrance ước lượng |
| `xOt-IeTRTsQ` | 00:11.4–00:23.5 | Nhóm tác vụ → browser → duyệt trên điện thoại; text/flow |

Đây là **tái dựng thử nghiệm bằng chữ dọc**, không phải project editor gốc.
Ảnh, icon, texture, counter, calendar rotation và chuyển cảnh gốc chưa được
native spec tái hiện. Không gắn nhãn SFX chưa nghe. Ba entrance ước lượng không
đủ để tuyên bố model đã học chuyển động mượt. Nhãn host-only cũ của reference27
không được sao chép: frame kiểm tra có thẻ tên. Nguồn ảnh gốc không upload.

## Lượt Kaggle mới

Dataset `812ebb85c0340346cad512e620cbab7973ec20921e4d832aa6432566f2b1cb5d`:

| Split | Số nhãn | Nội dung |
|---|---:|---|
| Train |34|29 text/flow adaptations +2 host holds +2 name badges +1 fixture |
| Validation |22|Cả nhóm Facebook, giữ nguyên group/hash |
| Test |10|Một source vlog5 repo; phát triển/hồi quy, không phải unseen quality |

Train có 14 intro toàn màn hình, 4 layout host, 1 demo fixture, **3 moving
entrances** và 1 audio-supervised fixture. Không có human gold. Creator độc lập
chưa xác minh. Preference chính vẫn Maverick; nhóm mới dạy lựa chọn intro toàn
màn hình theo reference explainer, không chứng minh đúng phong cách Maverick.

Nhóm YouTube trước là validation nay được retire sang train. Nhóm Facebook trước
đã vào adapter cũ, vì vậy validation mới chỉ dùng cho **model train từ pinned
base mới**, không resume adapter cũ. Không so trực tiếp loss hai corpus để nhận
là tiến bộ. Manifest và receipt ghi lineage, cả source group lẫn hash được giữ
cùng split; RAG chỉ lấy train. Prompt4 phân biệt visual anchor với lời đã nghe.

Private kernel:
[talking-head-spec-training-812ebb85c034](https://www.kaggle.com/code/duytruyenthong/talking-head-spec-training-812ebb85c034).
Đã gửi version1 với **64 optimizer steps** định trước. Kết quả thực phải đọc từ
receipt sau khi kernel hoàn tất; không coi submission là train xong.

Lượt này đã **COMPLETE**: 64 bước trên `cuda:0` TeslaT4,81,247s train,
L2 update2,004883; validation loss1,134313 →1,127462. Checkpoint:
`8903380f0766344c13327479441e344ae6e2d2c1c45f8afc25c934dfdfea4988`.
Worker local nạp đúng bytes. Cả hai arm unconstrained đều trả thêm dữ liệu sau
JSON intro; demo đạt native schema. Với grammar, base intro lọt một replacement
không có anchor, tuned intro va vào vùng captions; cả hai demo đạt. Đây là
kết quả thất bại được giữ, không phải full-video gain.

Code trainer được gửi vẫn có field `style` hardcode từ cấu hình cũ. Source hiện
đã sửa để đếm style từ rows thật. Import không viết lại receipt đã tải: nó suy ra
`training_style_counts` từ RAG và báo warning nếu field cũ không khớp. Các nhãn
train lượt này đều `balanced`; không dùng field cũ để quảng cáo Maverick fidelity.

## Sửa nguyên nhân trước lượt kế tiếp

Đã sửa hai lỗi được kiểm lại bằng test:

- LMFE0.11.3 có thể cho item đầu tiên vào array `maxItems=0`. Một shim chỉ dành
  phiên bản pinned bỏ parser của item bất khả thi; vẫn cho `[]`, whitespace và
  replacement có anchor thật về sau. Không sửa package đã cài, không nới native
  validator. Các inventory trống không thể sinh object nhờ lỗ hổng array này.
- 31 nhãn mới đã đưa giới hạn tái dựng vào `missing`, khiến Cutroom hiểu nhầm
  thành thiếu pickup của khách. Đã chuyển chúng về metadata/observations;
  `missing` chỉ dành cho input thực sự bắt buộc. Không đổi source interval hay
  nâng nhãn agent thành human gold.

RAG version2 ưu tiên số text, proof và style từ **input** sau role/intent; không
đọc target để xếp hạng. Scene sáu mục có thể lấy ví dụ sáu mục thay vì kéo dài
khoảng cách của ví dụ ba mục. Checkpoint cũ giữ retriever1/prompt cũ. Prompt5
làm rõ annotation limitations khác missing footage.

Dataset sửa:
`54d56526fac398357e44acf926ae0ab5389bb4bdba04c74ecf5eaa722960388b`.
66 examples, tối đa2.638tokens; không truncate target/source để qua giới hạn.
Private kernel:
[talking-head-spec-training-54d56526fac3](https://www.kaggle.com/code/duytruyenthong/talking-head-spec-training-54d56526fac3)
đã **COMPLETE**:64bước fresh base,71,000s trên một TeslaT4, L2 update1,817095.
Loss1,117627 →1,103849. Checkpoint:
`7a6e28b447a68ae752609e1bef205e2c124cddb5895b88dfce611075c95828d7`.
Receipt ghi đúng `balanced:34`, prompt5/retrieval2. Các adapter cũ vẫn giữ.
Raw Kaggle schema diagnostic vẫn intro0/2 ở cả hai arm; demo tuned1/2,
base0/2. Giảm loss chưa chứng minh video tốt hơn.

## Lượt UI đầu trong workspace002 · lịch sử

Source checkout mang version `0.14.0-dev5`; bundle RC4 cũ không thay đổi.
Job `bf203ce717c6455d9ae584f29986aa92`, workspace
`D:\.codex\workspaces\talking-head-support\cutroom-motion-model-002`.

Đã import source/captures/SRT qua UI, tạo scene rules, thêm CTA im lặng135frames,
xuất smoke5s trước master và giải mã. Smoke150frames1080×1920/30/AAC dùng
**h264_nvenc** thật. ASR118,1s dùng laptop CUDA/float16; không thay SRT đã có
bằng draft ASR. RTX3070Ti Laptop8GB/driver572.42.

Rules full export `259694940c3346d7b99471acf53832ea`:
SHA `081b1b816158b8a860fb83dc91b8eb2d3714de80211afdef68191220f2ce0aed`.
118,1s/3543frames1080×1920/30, h264_nvenc,−16,08LUFS/−1,65dBTP.
Byte-identical với bản rules repair trước đó; không gọi nó là nâng cấp sáng tạo.
Đã nhìn frame phone360px tại1,5s (đủ tên),49,2s (Recordlyv1.4.0/không che title)
và108,5s (CTA nguyên cụm). Đây là frame inspection, chưa xem/nghe toàn tập1×.

Harness từng lấy `folder` từ public snapshot, nhưng API chủ động giấu path đó.
Đã sửa sang download preview qua route của app, kiểm SHA rồi xuất smoke; resume
thành công. Source/config/media hashes được cố định và package không được đổi
giữa hai model arms. Source-only rules không cần import model. Sự cố runtime
được ghi PIPELINE_FAILED; chỉ native model rejection mới là MODEL_REJECTED.

Hồ sơ private: `output/reference-training/reference-spec-v003/ui-full-v001`.
Đây là snapshot giữa lượt chạy. Kết quả chốt và các lỗi phát hiện sau đó nằm
ở phần cuối tài liệu; không lấy spec hoặc rules fallback làm model master.

## Kiểm thử và điều còn thiếu

132 app tests đã chạy với optional decoder thật, 51 QC tests và 39 reference-lab
tests: **222 PASS** tại lần kiểm này. Đây là guardrails code, không phải điểm phim.
Lệnh unittest theo package `app.test_*` và hai đường dẫn test đoán ban đầu không
đúng; đã sửa sang `discover -s app`, `-s talking-head-qc/tools` và
`-s talking-head-qc/reference-lab`, chạy lại thành công.

Tại snapshot này vẫn cần full model exports hợp lệ, kiểm đủ từng demo/branding,
full watching/listening1×, câu trả lời người xem, repair session và tập raw mới. First-pass
acceptance, phút sửa/phút thành phẩm và style preference tiếp tục **N/A**. Reviewer
không nghe được để audibility UNVERIFIED. Chỉ clip có kiểm hình/watermark thật
mới vào thư viện usable; chữ vector nguyên gốc không tự chứng nhận master READY.

RC4 đã đóng gói trước đó và v035 được giữ nguyên; thử nghiệm source mới không
có nghĩa EXE RC4 đã chứa các thay đổi vừa viết.

## Kết quả chốt · exact master và lỗi giữ lại

Workspace local `D:\.codex\workspaces\talking-head-support\cutroom-motion-model-003`,
source version `0.14.0-dev5`. Đã tạo ba prototype toàn tập qua UI ở lượt
`ui-full-v002`; cả ba giải mã đủ nhưng kiểm hình sau đó tìm được lỗi thật:

- Cả ba thiếu CTA tại01:48,500 dù cue yêu cầu01:46,533–01:51,033.
- Bản base tại00:49,200 chỉ có presenter, thiếu kết quả Recordly. Spec tự báo
  `missing:["recordly"]` dù proof đã cấp. UI từ chối chèn scene đúng; harness cũ
  đã bỏ qua response lỗi và vẫn Queue. Đây không phải thiếu footage phải quay lại.
- So ba arm khi ấy không hợp lệ: proof và prompt-scene coverage không khớp.
  Benchmark đã trả `eligible:false`, không cấp điểm cải thiện.

Đã lưu review **negative-only**, hash-bound từ decoded still frames, cho ba
master cũ. Chỉ ghi khoảng frame đã thấy, không khai đã phát toàn tập, không nghe,
không `approved_by`. QC kiểm lại phải là **REVISE**. Các MP4, model, scene và QC
history cũ đều giữ. Chi tiết ở `ui-full-v003/confirmed-defects.json`.

Nguyên nhân CTA là cuộc đua lưu UI: harness thao tác tiếp khi Save chưa xong,
khiến profile vẫn `baseline`, nơi manual graphic bị tắt. Đã sửa cả hai lớp:

- UI theo dõi revision của edit. Response Save cũ không clear/refresh mất edit
  mới phát sinh. Thử chặn request thật: profile focus được lưu với music−20;
  edit music−19 trong lúc chờ vẫn nằm trên form và chưa lưu; Save tiếp lưu đúng
  focus/−19. Receipt `ui-save-race/results.json`: PASS, không sửa job benchmark.
- Harness đợi response Save/Insert, kiểm HTTP, đọc lại settings và tập scene đã
  chèn. Scene bắt buộc ở NEEDS_INPUT ghi MODEL_REJECTED; không xuất thiếu demo.

Lượt sửa `ui-full-v003` tạo hai master mới; base bị từ chối như trên, không có
rules fallback và không có master base mới để tính là thành công.

| Arm | Export ID | MP4 SHA256 | QC |
|---|---|---|---|
|rules|`57fc590130e943a2aebcc2fd9e008427`|`081b1b816158b8a860fb83dc91b8eb2d3714de80211afdef68191220f2ce0aed`|NEEDS_REVIEW|
|fine_tuned|`37b922f5c81f4b6e9f5e6eef6d2682d1`|`c6206e1aa387ec05eec5368e1a3909ee92ac5c3720fc66c5ca5a58eebc1be05c`|NEEDS_REVIEW|

Mỗi thư mục export chứa `edit.mp4`, `captions.srt`, `render-project.json`,
`timeline.json`, `cue-sheet.json`, các stem và `qc.json`. Đây là project chỉnh
được với path nguồn local, chưa phải gói tự chứa để chuyển máy.

Cả hai:118,1s,1080×1920/30fps,**3543 frame đã decode**, h264_nvenc/AAC48k,
**−16,08LUFS/−1,65dBTP**. Voice WAV cùng SHA
`a7e1880b5c1f69f39f69040aa92cdd4fee653f69b9728f77819841ce6a6273e5`;
SRT cùng SHA `343b75cb21ba82f6071ded7a2f6266e8564a621e6200b4f239f1b81f06760957`.
Music off để cô lập quyết định planner. GPU local **RTX3070Ti Laptop8GB**,
ASR receipt **CUDA/float16**, train Kaggle **TeslaT4**. Smoke5s trước master
đã dùng h264_nvenc thật, đủ150frames, giải mã thành công; đường dẫn/encoder log
có trong `encoder_smoke` của results. Bundle RC4 trước đây dùng CPU fallback vì
encoder binary khác; không gán encoder của lượt source này cho EXE đó.

| Điểm kiểm hình | Trước → sau | Quan sát giới hạn |
|---|---|---|
| CTA | v00201:48,500 → v00301:48,500 | Chữ chính xác đã hiện trên cả rules/tuned; cue106,533–111,033s, không retime voice/SRT |
| Recordly result | rules/tuned00:49,200 →00:49,200 | Thấy Releases / Recordlyv1.4.0, captions ở dưới cửa sổ |
| Base Recordly | v00200:49,200 → không có master mới | Giữ lỗi thiếu scene và MODEL_REJECTED, không tính presenter là demo |
| Intro | 00:00–00:02,600 | Rules có6 thẻ với keyframe thay đổi; tuned có6 thẻ nhưng0 entrance chuyển động |

Đã nhìn frame phone360px của master mới. Không coi ảnh tĩnh là đã xem/nghe
trọn1× hoặc đã đo độ mượt. Rules mới có cùng bytes với prototype rules đã sửa
ở workspace002; tuned cũng vậy. Việc render tái lập được không phải chất lượng
sáng tạo tăng lên. Full-screen intro là yêu cầu khai báo chung của brief, không
phải thành tích riêng của fine-tuning.

Click gán frame1379 (00:45,966667, proof01,476s), chime1470 (00:49,000,
proof04,500s). Peak stem riêng lệch0frame. Trên decoded mix, click correlation
khoảng0,232 và chime có nhiều peak cạnh tranh; crosscheck **UNVERIFIED**. Không
đổi tolerance hoặc tăng gain chỉ để qua checker. Cần reviewer nghe cue lẫn cả
lời, nhất là CTA/cutaway/cuối chữ. Không có full listening do agent thực hiện.

## Trang review và điều kiện dùng model

Trang so mù local của **hai bản sửa**: `/benchmarks/f28c81d730a84378836a35e61e5b5256/index.html` trên
`http://127.0.0.1:59505`. Ba bản lỗi cũ ở benchmark
`53d132f4eeed47d3a93c6792d5aad95c` được giữ để audit.

Quiz được chuẩn bị trước review từ proof thật: mục Releases và trang kết quả
Recordlyv1.4.0, kèm source/master timecode. Public JSON không chứa key/evidence;
hai route private trả404. UI desktop ghi360px, viewport phone390 ghi294px;
2× thử nghiệm được form ghi đúng2×. Chỉ Prepare, không Save review. Người review
thật hiện **0**; không tạo câu trả lời, preference hay phút sửa giả.

Protocol2 cố định source, brief, branding, script/EDL/proof, toàn bộ renderer và
encoder, prompt/decoder/worker thật. Hash MP4 bị thay hoặc brief đổi sau export
đều bị chặn. Hai bản sửa để reviewer so thử; thiếu base hợp lệ nên **chưa đủ bài
so mù ba arm**. Tập này là development/regression; không phải unseen test.

155 app tests với decoder thật +53QC +39reference-lab = **247 PASS**; hai JS
syntax checks, UI quiz/privacy và UI concurrent-save cũng PASS. Test code và
full decode không thay sáu gate editorial. Logs giữ trên D tại folder v003.

Khi ghi hai khoảng frame đã xem rời nhau, đã phát hiện `covered()` tiếp tục xét
khoảng phía sau dù khoảng cần kiểm phía trước đã được bao phủ. Nó làm mất lỗi
B sớm của bản base. Đã sửa để trả về ngay khi đủ khoảng mục tiêu; khoảng trống
và danh sách rỗng vẫn không chứng minh đã xem. Hai regression tests bảo đảm
lỗi đã quan sát được giữ và đoạn chưa xem không thành PASS. QC chạy lại ghi
cả A và B là lỗi trên đúng master base cũ; không khai xem/nghe toàn tập.

Adapter vẫn experimental, production_eligible=false, jobs mới dùng rules.
Fine-tuning giảm loss nhưng chưa cho motion tốt hơn: corpus chỉ có3 moving
entrance labels, đa số là balanced/static; chưa có giám sát đủ cho Maverick
fast. Không thêm clip nào thành thư viện usable/approved chỉ từ spec hợp lệ.

Cần trước khi dùng cho khách:

- Kiểm toàn tập ở1× với người xem/nghe được: cả5 demo đã hứa, thời điểm vào/ra,
  captions tiếng Việt, âm cuối, mix và CTA; ghi exact hash và timecode.
- Đối chiếu branding/brief hoàn chỉnh: prototype chỉ thử planner intro/Recordly
  trên camera cut/captures hiện có; chưa mang đủ logo cộng đồng, animation10–20s
  và sound design của v035. Bốn placeholder repo chưa liên kết không chứng minh
  bốn footage thật bị thiếu; cần kiểm correspondence với các cutaway đã có.
- Thu feedback và repair timer thật. First-pass acceptance, câu trả lời viewer,
  phút sửa/phút và model gain hiện **N/A**; không bật tự động từ loss/log load.
- Một vlog raw khác cùng script/branding để khóa nguồn mới ngoài train và RAG.
  Nguồn hiện chỉ có1.mp4; đang chờ đường dẫn mới. Bản sửa của5repo có thể vào
  regression, không được tự đổi thành unseen.
- Bố cục host cần vùng mặt đo trên source; box mặc định chưa đủ để chấm mặt bị
  che. Muốn học chuyển động phải bổ sung nhãn keyframe/timecode có kiểm chứng,
  không chỉ train lại các thẻ tĩnh thêm bước.

v035 giữ nguyên SHA
`ca15d2c90348ddfa33d46e2504516075689179f31e5c1d3729deffb745603c09`.
Source được cập nhật; chưa build EXE/ZIP thay RC4. Launcher riêng của máy hiện
ở `output/reference-training/reference-spec-v003/start_local.ps1`; chạy từ repo
với `.\talking-head-qc\tools\use_d_storage.ps1` trước. Harness toàn tập:
`python app/full_video_acceptance.py --url http://127.0.0.1:59505 --config CONFIG.json --out NEW_RUN`.
Optional decoder dùng `CUTROOM_ANIMATION_DECODER=source_json_v1` và site pinned
0.11.3 trên D; mặc định ngoài launcher vẫn unconstrained.
