# Talking Head Cutroom0.14 — nghiệm thu nội bộ12/11/2026

Internal candidate, chưa phải customer READY. Goal train/reference-fidelity
vẫn ACTIVE: cơ chế goal từ chối thay goal chưa hoàn tất; build được tiếp tục
theo yêu cầu mới, không đóng giả goal cũ đã xong.

## Gói và mở app

ZIP: `D:\.codex\workspaces\talking-head-support\releases\Talking Head Cutroom 0.14.0-rc4.zip`

- 17.584.235bytes,141files, Windows x64/CPython3.12.10 đi kèm.
- SHA256: `ad86a27869de80ed40f5f7f92fa304e4ca06497140b96aa2a1d2959bff299d10`.
- Source commit: `b99053dc74e7d0807c3f33640bddf523652d88f5`, clean khi build.
- Source tree SHA: `4f0c553d5da52f86ccdd426ebd3d8cc7fed5eb5bb1fd7e92fbfaa0f95051a58f`.

Hai lần build độc lập có cùng SHA ZIP. Allowlist và ZIP timestamps/thứ tự cố
định. Không có recording khách, reference, model, token, cache hoặc config máy
phát triển trong gói. Model/encoder được tải tùy chọn, lưu receipt riêng.
Windows từ chối tạo thư mục ở gốc D; gói nằm trong thư mục D ghi được ở trên.

Giải nén toàn bộ vào D, mở `Talking Head Cutroom.exe`; xem `START_HERE.md`
hoặc [quick start](CREATOR-QUICKSTART.vi.md). EXE/project nâng cấp đã được thử:
`D:\.codex\workspaces\talking-head-support\acceptance\Cutroom nâng cấp có dấu\Bản kiểm thử 0.14.0-rc4`.
Project test này dùng các source/model giữ ở workspace QA3; mang kèm các nguồn
trong recipe khi chuyển project. ZIP không chứa project riêng này.

## Có thể dùng ngay và giới hạn

UI: recording → **Make first cut**, niche tự do/để trống, optional TXT/SRT,
B-roll và style reference riêng. Có editable brief, source/edit map, uncertain
passages, trim đầu/cuối/restore, captions, motion, từng sound cue, music và logo.
Batch chỉ áp trường đã đổi, giữ scene khóa. B-roll tên thường được label/gắn
tay; gợi ý chỉ dựa từ chung trong mô tả, chưa là semantic vision hoàn chỉnh.

Mười story recipes là lựa chọn biên tập, không phải mười renderer đã nghiệm thu.
Hook score là heuristic theo availability, không dự báo hiệu quả khán giả.
Audition chỉ render4s host-first/proof-first, cùng audio; cần footage có result
anchor và hold đọc được. Thiếu proof giữ presenter. Recording-only giữ các take
phân vân; còn cần nghe, chọn take và sửa tên riêng ASR. Các model/style adapter
khác vẫn optional/experimental, không bắt người mới chọn model hoặc viết JSON.

## Test thật qua EXE/UI

| Case | Kết quả/phạm vi |
|---|---|
| Fresh EXE, đường dẫn khoảng trắng/dấu Việt | PASS trên máy hiện tại, embedded runtime, PATH/app-data test được tách |
| Thiếu encoder | Tải FFmpeg/ffprobe8.1.2 vào workspace/tools, SHA/features PASS; không system install |
| Thiếu model | Tải faster-whisper1.2.1, CTranslate2 4.9.0, small revision536b0662742c02347bc0e980a01041f333bce120; CPU load PASS |
|1.mp4 không script/B-roll | Xuất140,866667s/4226frames/1080×1920/30; CPU int8 ASR + libx264 |
| Sửa caption → kill đúng process test → reopen/resume | PASS; transcript còn, trạng thái Interrupted, master trước nguyên SHA |
| Script + clip02 + style + niche | Actual Recordly capture được chèn; style-only không có trong proof |
| Hai opening và chọn qua UI | Cùng packet audio/PTS; chỉ4s audition; choice được xuất vào master mới |
| Batch có SRT ngoài source | Bài lỗi Failed; bài khác vẫn xuất được |
| Native scene lock/reopen/upgrade | PASS, lock còn và không bị caption edit bài khác ghi đè |
| Chưa cài ASR, dùng SRT | EXE xuất fixture8s, không download; warning voice match UNVERIFIED |
| Offline ASR thật |16s audio từ take,50 từ/4,063s, CPU int8; Hub offline, HTTP(S)/ALL proxy trỏ cổng localhost đóng |
| Niche thứ hai | Context sản xuất dùng fixture tổng hợp; chưa có raw recording ngành khác |
| Windows sạch / full1× listening | Chưa kiểm; không có reviewer nghe trong runtime này |

RC3 suite hoàn thành trong các lượt có resume; hai selector harness được sửa
bằng mở đúng panel/details. Lỗi test cũ giữ trong previous_test_failures; không
gọi đây là một lượt cold run liền mạch. RC4 kiểm riêng upgrade/caption repair và
render mới. Runtime/installer/renderer không đổi; creator căn cue được sửa.
121 app tests +51 QC tests +39 reference-lab tests PASS; skill validator PASS.

Logs local, ngoài Git/ZIP: `output/creator-release/packaged-rc3/results.json`,
`missing-model-rc3/results.json`, `optional-runtime-rc3/results.json`,
`caption-repair-rc4/results.json` dưới cùng thư mục creator-release.

## Hiệu năng, thiết bị và codec đo được

Máy: i9-12900H, RTX3070Ti Laptop8GB/driver572.42.

| Cùng recording140,866667s, packaged CPU path | Wall time | Export bytes |
|---|---:|---:|
| First cut, chưa có transcript cache |107,141s|146.631.749|
| Caption case edit sau interruption/resume |33,375s|156.896.484|

Revision chỉ mã hóa8,333333s đầu, giữ3976/4226video packet/PTS và toàn audio
packet/PTS. Cache work5,344s; vẫn QC toàn MP4. Đây là một clip/máy; first run có
ASR còn revision dùng cache, không phải kết luận tốc độ chung hoặc model tốt hơn.
RC4 có B-roll và sửa nhiều cue:66,234s, dùng transcript/reference cache nhưng
render hình đầy đủ. Cache chỉ hỗ trợ presenter đơn giản/edit sớm; còn lại fallback.
Đã bỏ full render thứ hai bắt buộc; QC exact master vẫn chạy. Rerender tái lập
chỉ bật bằng CUTROOM_VERIFY_REPRODUCTION=1.

Source pilot trước đã dùng large-v3-turbo/CUDA float16 và h264_nvenc thành công.
Test CPU package cố ý ép CPU. Smoke5s thật có captions/logo đã thử h264_nvenc
trên FFmpeg8.1.2; log yêu cầu NVENC13.1/driver610+, máy hỗ trợ13.0/572.42.
Pipeline chuyển riêng encode sang libx264, decode đủ150frames. Không ghi nhận
NVENC thành công trên binary đó. [FFmpeg](https://ffmpeg.org/download.html) dẫn
tới [Gyan builds](https://www.gyan.dev/ffmpeg/builds/); binary pin URL/SHA và
license/receipt local. [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## MP4, timeline và trước/sau

Workspace QA4 ở đường dẫn trên, export`016207c4b1694e1a8ce44279d6346fa4`:
`workspace/exports/016207c4b1694e1a8ce44279d6346fa4/edit.mp4`.
SRT, project.json, render-project.json, timeline.json, cue-sheet, stems và qc.json
cùng thư mục. Editable UI project: workspace/workspace.json.

- 140,866667s,4226frames,1080×1920/30, H.264 **libx264**, AAC48kHz, full decode PASS.
- −16,05LUFS integrated,−1,67dBTP.
- SHA: `619ce5ab8ea7b5cc4c588a4c73536ae8b68a402dfaa50b6156df630398fbbecf`.
- Status **NEEDS_REVIEW**. Vẫn là first-cut fixture, chưa thay vlog v035 hoàn thiện.

| Trước → sau, source/master clock giữ nguyên | Sửa |
|---|---|
|00:50,30 →00:50,30 · speech-a6c642ed2225ad11 · source49,05–50,85|record league → Recordly; hai token giữ chung span gốc|
|00:55,30 →00:55,30 · source51,69–55,55|CTI → CTA theo sửa trực tiếp của user|
|01:02,13–01:05,95, timestamp giữ nguyên|Recordly lần hai|
|01:13,03–01:15,57, timestamp giữ nguyên|Recordly lần ba|

405 từ ngoài bốn cue giữ text/word timing,0mismatch. Audio packet/PTS nguyên vẹn.
Cut trước ghi REVISE trong bản copy nâng cấp; source workspace/cut cũ giữ nguyên.
v035 vẫn SHA`ca15d2c90348ddfa33d46e2504516075689179f31e5c1d3729deffb745603c09`.

Đã xem frame360px của exact RC4 master tại1,50;50,30;55,30;59,50s: tên Recordly/
CTA sửa đúng hình, Releases/result title tách khỏi caption. Quan sát frame tĩnh
không thay xem/nghe1×. B-roll54–64,50s dùng source0–10,50; result5,50 là mẫu trạng
thái ổn định, không khai frame thành công đầu tiên hoặc dùng đặt chime. Nhánh
test tắt motion/SFX/music. Audition cùng audio không là chứng cứ hiệu quả opening.

## Hooks và skill entrypoint

Import: workspace.import_asset probe/hash/role/owner. Voice-first: creator.prepare
và speech/cache. Plan: planner.build, creator.apply, artifacts.apply, openings.apply.
Pre-render: qc_bridge.prepare_export + qc_hook.preflight và frozen dependencies.
Post-render: dependency check + qc_hook.inspect_and_save, decode/frames/levels/sáu
gate. Revision tăng version, từ chối approval cũ, cue-local alignment/cache có
fallback. Release: qc_bridge.approve + release_receipt, chỉ người đã xem/nghe.
Feedback: video_benchmark chỉ nhận pairs đúng split và đã duyệt cho learning.

talking-head-edit vẫn entrypoint; cutroom-reference/motion/cue-mix/master-review
phục vụ một timeline. Catalog và renderer adapters tùy chọn có prerequisites/
phạm vi kiểm riêng. Hai worker local, JSON atomic, cache hash; không thêm service
chung. [Production contract](TALKING-HEAD-PRODUCTION-CONTRACT.vi.md).

## Còn chặn release chất lượng

1. Nghe/chọn take0–11s; so lời host cộng đồng13–16s; FFmpeg25–31s; Recordly54–69s;
   Remotion76–92s; fal/Runway93–124s; CTA126–140s. ASR còn sai chữ/names. Các khoảng
   này là danh sách cần duyệt, không phải đã xác nhận lời đúng. Toàn master chưa
   được người có khả năng nghe kiểm1×; sáu gate chưa đủ bằng chứng.
2. Chưa có raw tập khác ngành và held-out episodes đủ độc lập. Fixture context
   không chứng minh chất lượng nội dung ngành đó.
3. Kaggle đã train192steps/TeslaT4, checkpoint SHA869444f8c7f28742e04287a8a346a40e202fe7689da5b3734a44e41f456a9818.
   Validation loss2,073036→2,618295; cả hai model arms còn reject intro trong app,
   chưa có đủ ba master toàn tập để so. Candidate experimental, chưa promote.
4. First-pass acceptance và phút sửa tay/phút video còn N/A: chưa có review/
   timer của editor.33,375s là thời gian máy. Chưa có viewer quiz/style winner.
5. Grant starter trong THIRD_PARTY.txt chưa xác nhận: gói nội bộ, owner quyết
   định publication. Python/distlib/font/checker có notices; example tự tạo,
   không có speech thật. Chưa nghiệm thu máy Windows sạch.

[Benchmark toàn tập](FULL-VIDEO-BENCHMARK.vi.md): tập đã sửa rồi train/RAG là
regression. Promotion dùng tập mới, cùng source/renderer/mức nghe, đủ QC, viewer
answers và thời gian sửa thật — đúng tiêu chí user vừa xác nhận.

## Lệnh

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
$py='C:\Users\Acer\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $py -X utf8 -m unittest discover -s app -p 'test_*.py'
& $py -X utf8 -m unittest discover -s talking-head-qc\tools -p 'test_*.py'
& $py -X utf8 -m unittest discover -s talking-head-qc\reference-lab -p 'test_*.py'
# Chọn out mới; starter chỉ cung cấp runtime/launcher/notices, không lấy media.
& $py -X utf8 app\build_release.py --starter $starter --qc-skill $qcSkill --out $newVersion
# Harness dùng Playwright/Chrome bên ngoài gói, media riêng truyền bằng đối số.
& $py -X utf8 app\release_acceptance.py --help
& $py -X utf8 app\caption_revision_acceptance.py --help
& $py -X utf8 app\optional_runtime_acceptance.py --help
```

Người dùng EXE không cần Python dev hoặc harness. Receipt local lưu exact file,
SHA/source/timeline và phạm vi kiểm để reviewer tiếp tục đúng version.
