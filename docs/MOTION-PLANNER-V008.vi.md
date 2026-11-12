# V008 — intro nhiều thẻ và nguồn preview im lặng

Ngày 13/11/2026: Kaggle v008 đã **COMPLETE**, xác minh checkpoint và nạp lại
thật qua worker mới. Ba bản toàn tập đã xuất từ UI, cùng một bản intro full
và một bản sửa timing riêng. **Chưa chứng minh fine-tune dựng tốt hơn.**
Không bật mặc định sản phẩm hoặc ký master. Sau kiểm frame, cả năm bản thử
được ghi **REVISE** vì còn thiếu cảnh preview FFmpeg mà brief yêu cầu.

## Dữ liệu mới và provenance

Thêm16intro fixture nguyên gốc từ project native chỉnh được: hai style,
2/3/4/6nhãn, tĩnh hoặc trượt nhẹ theo mốc hình do project khai. Không gọi các
keyframe tự tạo là project gốc/reference motion đã quan sát. Không dùng ảnh,
audio hay corrections từ validation vào train. Tất cả fixture mới ở cùng group
`house-motion-fixtures`/train, không tính thành16creator độc lập.

Dataset cuối `58f891bd45e9b12f27d0f97da3b7f33d36e3dd6c189cd76379be384ea7fed788`:
48train/33validation/10regression;61observed-reference reconstructions,
20house fixtures,10acceptance expectations;0human gold. Có41labelled source IDs,
5conservative split groups; số family/creator độc lập chưa xác minh. Reference
gốc vẫn29files/28unique hashes.16source fixture mới không làm tăng số reference.

Train có34intro/14demo;19full-screen intros,17moving entrances. Đây là độ phủ
target native, không phải điểm fidelity. Lịch64bước cố định sẽ update42unique
rows,10/16fixture mới trực tiếp làm optimizer example; RAG chứa đủ48train rows.
Không khai mọi label đều được cập nhật trọng số trực tiếp.

Đã render/decode16fixture,144frames/cảnh, kiểm48sample ở phone width và giữ
source PTS/project JSON. Chữ/dấu đầy đủ ở trạng thái settled được xem, thẻ nằm
trên vùng captions, biến thể static/moving phân biệt rõ. Đây là agent experimental
inspection, chưa có normal-speed style/reading hoặc audibility approval. Preview
có nhãn STORYBOARD của renderer; không admit chúng vào usable library.

## Lỗi thực tế đã sửa trước upload

1. Fixture đầu im lặng bị `No measurable programme audio`. Giữ folder lỗi.
   Sửa riêng scene preview: chỉ chấp nhận measured integrated và true peak
   cùng−inf, xuất mức nullable/purpose`scene_preview_silent` và
   `master_loudness_verified=false`. Nguồn/mix đổi trạng thái silent bất ngờ
   bị từ chối; measurement process lỗi vẫn bị chặn. Full master dùng đường
   strict như cũ.16preview thật đều qua decode; gọi finish_audio trên cả16
   vẫn bị từ chối trước khi tạo master. Không thêm tone/voice giả để vượt gate.
2. Preflight đầu3094/3072tokens; rút rationale còn3085, vẫn bị chặn. Rút phần
   intent lặp lại nhưng giữ all-label/static/slide intent, quote, visible text,
   geometry, anchors và source clocks: cuối3066/3072. Giữ cả ba dataset/token
   reports; không truncate hoặc tăng context limit. Chưa có training job nào
   được tạo từ hai dataset over-budget.
3. Kaggle CLI upload với relative path lỗi ở local upload cache. Xác minh
   resource chưa sẵn sàng, dùng absolute path; dataset tạo private và báo ready.
   Không đổi quyền, nhận competition rules hoặc tạo lại job khi mất quan sát.

257 app tests PASS ở dev19. Metadata preview dùng “source audio”, vì audio nguồn có thể
im lặng hoặc không có presenter; không tự nhận mọi source đều có giọng nói.

## Kaggle thực tế và reload

Private dataset `duytruyenthong/talking-head-animation-spec-58f891bd45e9`,
kernel `duytruyenthong/talking-head-spec-training-58f891bd45e9`,version1.
10 flat training data/code files, không raw media. Version 1 đã COMPLETE.
Prompt9/retrieval3/Qwen pinned/optimizer/lr/sampling/64steps giữ nguyên như v007;
thay đổi experiment là16train examples mới. Initialization từ pinned base,
không resume adapter v007. Validation đã được xem là development; không là final.

Đã tải riêng adapter/receipts, không tải cache base 2,88 GB. Provenance xác nhận:

- 64 optimizer steps thật; 42 unique rows, gồm 10 fixture mới trực tiếp update.
- CUDA:0, một Tesla T4 được dùng trong môi trường có hai T4; peak 8.676.733.440 bytes.
- 75,350 giây optimizer training, không phải tổng thời gian job hoặc phút editor sửa.
- Weight update L2 = 2,526724815; validation loss 0,828360865 → 0,797591861.
- Adapter SHA256 `f4ded53f3e52fb00379a9ae1e4bd6cce3975539c5e1a6dea9138ad460f14a9fc`.

Hai worker mới chạy base tắt adapter và tuned bật adapter, cùng RAG 48 train rows,
prompt 9/retrieval 3/decoder và pinned base. Raw regression trên Kaggle:
base intro 0/2, demo 0/2; tuned intro 0/2, demo 1/2. Đây là regression đã dùng,
không phải tập B mới hay điểm fidelity.

## Diagnostic và ba bản toàn tập

Diagnostic cố định gồm 8 input từ 4 source validation, không trùng train theo
hash, nhưng đã là development set. Creator độc lập chưa xác minh.

| Arm | Intro native / 4 | Intro raw / 4 | Demo native / 4 | Demo raw / 4 |
|---|---:|---:|---:|---:|
| Rules | 4 | 4 | 4 | 4 |
| Base + cùng RAG | 2 | 0 | 2 | 2 |
| Tuned + cùng RAG | 2 | 2 | 1 | 1 |

Hai intro base qua compiler repair, không tính là raw success. Raw model giữ
đủ declared texts trong 8 case, nhưng còn lỗi che captions hoặc thiếu thời gian
cho trạng thái cuối. Rules demo native 4/4 nhưng thiếu các text trạng thái sau
trong cả 4 case. Native pass, coverage và fidelity là các phép kiểm riêng.
Không dùng các lỗi vừa quan sát để train tiếp rồi gọi cùng set này là unseen.

Normal UI tại `http://127.0.0.1:59520` đã import package, giữ locked Recordly demo,
branding, giọng/SRT và 13 cutaways; xuất rules/base/tuned, không page error.
Ba bản có 3543 frames, 118,1 giây, 1080×1920, 30 fps, H.264 NVENC/AAC 48 kHz;
full decode pass; −16,08 LUFS / −1,65 dBTP. ASR thật dùng CUDA/float16.

| Bản | Export ID | MP4 SHA256 |
|---|---|---|
| Rules | bbbe94d8589d454dadd7d3303501742f | c4d10342a1f6219f2faf416db5227e68798d70b048e98bccdf29f86033637ba0 |
| Base | 79ffa885e96f4b7e8185aafb6d98ec27 | 3f16526606fbe5f695f79776159c61bf5efa34c9e22f681d2e414c0921833abc |
| Tuned | 5b01ad05312448c89989b64d48bc8ac7 | 3f16526606fbe5f695f79776159c61bf5efa34c9e22f681d2e414c0921833abc |

Base và tuned **cùng MP4 hash**: lượt train/load là thật nhưng chưa có picture/audio
gain riêng. Buyer quiz được tạo qua UI, đảo/ẩn arm, answer keys không public;
chưa có reviewer trả lời, first-pass acceptance và phút sửa/phút thành phẩm là null.
Gallery local: `/benchmarks/aa521560eb674a5283bab22981530992/index.html`.

## Intro full và sửa tay có giới hạn

Thử nghiệm riêng đổi host intro thành full intro, giữ nguồn/giọng/SRT/mix/demo.
Model giữ cả sáu text: headline và năm repo, nhưng entrance chỉ dài một frame.
Decoded frame 0 trống, frame 1 mờ/dịch, frame 2 đã settled: chưa đạt mục tiêu
animation mượt của brief.

Sửa timing qua Advanced JSON của UI: keyframe cuối từng thẻ từ 1 frame thành
6/8/10/12/14/16 frames, hold bù để giữ tổng scene [00:00,00:02.600). Giữ anchors,
geometry, text, font, màu, SFX chưa khai báo, provenance và locked demo. History v001
giữ nguyên; v002 là manual override, correction `editor_confirmed=false`, không
đưa vào train/RAG hay gọi là model gain.

| Trước/sau | Export ID | MP4 SHA256 |
|---|---|---|
| Full intro raw | 7e2b8b6d5688456dab302aca6d2def68 | 957e1442c65fceac1a6e35d157ab770d59b4c9421a7c087c14aa0b4dddd87c65 |
| Full intro timing v002 | 8451be1f3cf748858e9df8779e84cad8 | 510db2b73a92b6116b7e6eca1c3b415953da75438eaaab88a3edeca4cc207401 |

Kiểm PCM decode cả năm MP4: cùng SHA `4c5d9a7670a9…`; voice/music/SFX stems,
SRT và ASS dialogue cùng hash. Sample phone-width cho thấy intermediate poses mới,
đủ tên repo và mặt trở lại ở 2,600 giây. Đây là kiểm frame, không phải full 1×
viewing/listening hay duyệt mỹ thuật. Hai hook [0,3) thật có receipt/decode riêng.

## QC còn thiếu và lỗi kit đã sửa

- **REVISE 00:34.733–00:37.333:** exact frame 00:35.500 vẫn là trang GitHub;
  brief cần Recordly quay preview thật có chuyển người dẫn → màn hình. Đã ghi
  timecoded revision cho cả năm master qua UI, reviewer ghi rõ chỉ kiểm frame;
  mọi watch/listen checkbox và attestation để trống. Không thay byte MP4 cũ.
- Recordly vẫn chọn Facebook. Computer Use không activate được HUD sau một
  lần recovery; chưa Record. User được hướng dẫn chọn đúng cửa sổ FFmpeg preview.
- 00:45.967 contact Releases, 00:49.000 Recordly v1.4.0 được thấy trên decoded
  frames. Isolated SFX peak đúng frame; crosscheck trong final mix vẫn UNVERIFIED,
  cần nghe. 01:30.500 có giá và đơn vị; 01:41.000 có `promptImage`; thời gian đọc
  ở tốc độ thường và nội dung đầy đủ cần reviewer. Không tự thêm yêu cầu Runway
  trả clip khi lời thu chỉ yêu cầu thay ảnh/chạy lại.
- Full mix, tiếng cuối/cut, độ tự nhiên, caption ±150 ms, style giống reference,
  intro hierarchy và first-pass/repair-time chưa được người có audio duyệt.
- Không admit fixture STORYBOARD hoặc master này vào usable animation library.
  Chưa có tập B mới; không promote model.

Trong kiểm tra reuse phát hiện valid native spec có thể bỏ field SFX, nhưng
library adapter truy cập bắt buộc gây KeyError. Dev20 sửa iteration dùng optional
field; giữ khác biệt “chưa khai âm thanh” với “mute []”, rebind text/anchor và giữ
template nguồn. Test có cả hai nhánh, **258 app tests PASS**. Không đổi renderer,
checkpoint hay ba arm đã freeze. Source UI của trial vẫn là dev19; package mới
có receipt riêng, không tự coi giao diện đang mở đã được thay.

### Gói dev20 đã thử bằng runtime bên trong gói

Build từ commit `be1eb3a4e4976275a3f167e11049564075eb0e37`, source sạch,
153 files / 17.662.500 bytes. ZIP SHA256
`92dccceb68d7d2bea6224a2417c9f23f74d6326273916daf8643608a74f8f5c5`.

- Embedded CPython 3.12.10 render thật prefix có lời/subtitles 5 giây:
  150 frames, NVENC, full decode PASS; SHA `0f1392c83f2835e5df3def9a4d9aeda5cce32f1de7f5ae290a3c9faa846dae31`,
  bằng các prefix trước. Mức −22,58 LUFS/−9,86 dBTP là original-level scene preview,
  không phải master mix pass. Master nguồn không đổi.
- Preview im lặng thật 4,8 giây / 144 frames PASS; measured levels null,
  `master_loudness_verified=false`; strict master vẫn từ chối và không tạo file.
- Rebind chính intro sáu text vừa dựng qua module library của gói PASS:
  đổi anchors, giữ text, giữ SFX chưa khai báo và template gốc. Đây là test riêng,
  không phải episode mới hoặc admission vào library dùng cho khách.
- Chưa chạy native GUI launcher/Windows sạch. Starter redistribution grant chưa
  chốt; đây là internal candidate. Không thay GUI đang chạy.

Known UI limitation: save bằng Controls hiện có thể chuyển SFX chưa khai báo thành
`[]`. Lượt sửa intro này dùng Advanced JSON và xác nhận field vẫn vắng mặt, nên
không bị ảnh hưởng. Cần sửa và test luồng Controls trước khi coi reuse/edit audio
đã hoàn tất; không suy từ test adapter rằng UI cũng giữ đúng trạng thái.

Evidence private trên D:`output/reference-training/reference-spec-v008/`:
protocol, authored fixtures/project/timelines, inspections, recovery, token
curation v001–v003, dataset-v003, preflight, Kaggle logs và preparation.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
kaggle kernels status duytruyenthong/talking-head-spec-training-58f891bd45e9
python -m unittest discover -s app -p 'test_*.py'
```

Trên máy này dùng Python runtime đã cài thay cho alias `python` nếu alias không có
interpreter. Lệnh launch source (không thay GUI/EXE đang mở):

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$taskPython='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $taskPython -X utf8 -m unittest discover -s app -p 'test_*.py'
& $taskPython -X utf8 app\app.py --help
```

Còn cần capture preview FFmpeg, tập B hoàn chỉnh, người có khả năng nghe xem toàn
master 1×, câu trả lời hook/proof và phút sửa thực. Không release/promote vì loss
giảm hoặc native validity tăng. Xem `SESSION-UNDERSTANDING.md` cho checkpoint
hiểu biết đang chờ; không suy ra user mastery từ các test ở trên.
