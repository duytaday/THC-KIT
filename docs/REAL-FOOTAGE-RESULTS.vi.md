# Talking Head Cutroom — nghiệm thu skill footage thật, 11/11/2026

Đã mở rộng `.agents/skills/talking-head-edit/SKILL.md`, giữ `$talking-head-edit`.
Tài liệu dài nằm trong `references/real-footage-workflow.md` và `components.md`
của skill. Quy tắc ignore trước đây bỏ qua mọi thư mục `references`; đã thêm
ngoại lệ hẹp cho tài liệu skill, vẫn bỏ qua customer footage. Skill validator PASS.

Lời gọi được agent dùng để điều phối ca này:

> Dựng một video talking-head từ footage người dẫn, script và thư mục minh họa
> này. Đề xuất ba hook, chọn một hook có bằng chứng, dựng bản đầu đến CTA và chỉ
> ra các điểm cần tôi duyệt.

Đây là agent thực thi SKILL.md và dùng UI thật, không phải một API tự động
“chạy skill”. Chưa kiểm bằng một phiên Codex mới trên máy người mua. Input lấy
từ công việc hiện tại; media, nguồn tham chiếu, model và đường dẫn từng khách
không nằm trong skill phân phối.

## Thay đổi hoạt động

- Người dẫn/giọng thật là nền. AI illustrations nằm trong Optional lab, ngoài V1.
- 20 component được đặc tả; **9 variant render-test**, **0 component được ký
  duyệt editorial**. Không có tuyên bố 20/20 QC. Inventory hiện ngay trong UI.
- PiP dùng chính A-roll, giữ góc cố định trong cutaway. Auto tránh ROI nút,
  kết quả và caption; không có góc an toàn chuyển Full demo. Góc manual va chạm
  báo lỗi; không âm thầm thay override. Layout split generic chưa bật.
- Giữ motion intensity, cue mute/gain/offset và music độc lập. Chỉ đổi event
  nhãn ở revision mẫu; script, nhạc, proof và manual cues trước đó được giữ.
- Inventory có `--previous`: đối chiếu hash, không coi đổi tên/bản trùng là
  nguồn mới; không tự train hoặc tự bật preset.

## Các ca đã chạy

Local source snapshot có Git sạch được chạy bằng Python ngoài checkout, input
riêng và Chrome thật. Không mock import, render, FFmpeg, reproduction hay QC.
Ca đầu chạy trên snapshot `ce85ad2…`; bản runner sửa panel state và tài liệu skill
đã được đưa vào snapshot sạch `a8be85c…` để kiểm lại: cả3ca UI pass, không có lỗi
JavaScript, cả3 giữ NEEDS_REVIEW đúng điều kiện. Hai bản có cùng settings tái
hiện cùng hash MP4 giữa hai lượt test. Snapshot test local không
phải commit phát hành. Chi tiết private nằm trong `output/real-footage-acceptance/`.

| Ca | Kết quả thực tế |
|---|---|
| A-roll thật + Cutroom screen thật | 20,466667s; PiP top_right, giữ control/caption rõ; source contact1,7s và success3,833333s có cue riêng. Đây là prototype minh họa thao tác, **không phải demo tính năng Recordly** dù lời đang giới thiệu Recordly. |
| Bảo vệ toàn vùng hình đang hiển thị | Cùng component03 tự fallback04; không đổi font, music hay script. ROI bảo vệ do test cấu hình; không tuyên bố đã quay một bảng dữ liệu mới. |
| Thiếu take/thiếu proof, không B-roll | Giữ A-roll và tiếng gốc; CTA “mở file vừa xuất” là pickup nếu chưa thu, không sinh giọng hoặc chèn màn hình sai lời. |
| Tập “5 repo GitHub” hook→CTA | Giọng thật từ9 đoạn source đã có, 10 insert từ capture được giao, không dùng reference làm footage.118,1s/3.543frames. |
| Sửa lỗi đọc tên ở phone size | Version mới cùng job, thêm nhãn repo/model ở vùng trống; old master giữ nguyên. Các trường script/music/proof không đổi. |

Bản toàn tập đầu: SHA `040bd8e89ccb7595c581bce7891383455c6e587cb7488b5f98dd1caca1db8d1a`.
Bản sau sửa: SHA `aeac663df65e507e1c6714c6c6ace0bf1752ae0bbdabc4a5e511a93850c72626`.
Cả hai cùng118,1s,1080×1920,30fps,AAC48k. Bản sau: **−16,07LUFS,
−1,65dBTP**, fully decoded3.543frames; rerender recipe byte-identical.
GPU log: NVIDIA GeForce RTX3070TiLaptop8GB; encode h264_nvenc. Không chạy ASR
mới: dùng lại SRT/cut decisions, nên không gán thiết bị ASR mới cho lần này.

Năm SFX nhãn có peak stem đúng anchor0frame. Đối chiếu trong mix AAC có voice
trùng nhau cho correlation thấp: **UNVERIFIED**, không gọi là pass đồng bộ mix.
Không có khả năng nghe đầu vào trong phiên agent; chưa nghe toàn bộ master.
Đã xem các frame giải mã ở kích thước270/360px, không thay bằng chứng playback1×.

## Trước/sau và điểm cần người duyệt

| Master trước → sau | Kiểm / thay đổi |
|---|---|
| 00:00,10 → giữ nguyên | Title promise xuất hiện trước3s, người dẫn và lời thật giữ nguyên. |
| 00:20,33 → giữ nguyên | Nhãn FFmpeg Skill dễ đọc; cần nghe voice xuyên cutaway34,73–37,33. |
| 00:39,33 → giữ nguyên | Nhãn Recordly; xem target44,53, contact và đích Releases đến57,53. Không gán cue click mới khi chưa đo nguồn. |
| 00:59,40 → giữ nguyên | Nhãn Remotion; xem đổi field/preview62,70–71,30 và kiểm tên mới. |
| 01:23,60 → giữ nguyên | Thêm “fal · Kling3.0Pro” ở vùng trống vì header capture nhỏ/cụt; giá88,40–92,40 vẫn từ capture, gồm đơn vị. Không phải giá hiện tại đã tra cứu. |
| 01:35,03 → giữ nguyên | Nhãn “Runway · promptImage”; chỉ chứng minh vị trí input, không có clip trả về của một lượt chạy mới. |
| 01:45,10 → giữ nguyên | CTA “5 repo github edit videos” giữ9s; kiểm lời và việc gửi link thực sự có người thực hiện. |
| Toàn master | Nghe1×, tiếng cuối câu/cut, tên repo, phủ định, caption±150ms, mức SFX/music; xem mọi thao tác ở phone size bình thường. |

Style profile, đúng3 hook và audiovisual plan9beat + source-cut map đã lưu riêng
trong `output/real-footage-acceptance/episode-plan-v001`. Các ghi chú này được
hoàn thiện từ settings đã chạy; không giả là toàn bộ kế hoạch đã được ghi trước
lần render đầu. Reference3clip được xem ở các frame30/90/180, timecode tính theo
fps thật trong sources.json; chỉ kết luận về bố cục/title nhìn thấy, không suy
cadence, retention, nhạc hoặc lời. Nghiên cứu công khai trong prompt là tài liệu
người dùng cung cấp, chưa được agent xác minh playback/audio trong lượt này.

## Chạy lại

```powershell
python app/app.py --data "LOCAL_WORKSPACE"
python app/buyer_acceptance.py --cases "PRIVATE_CASES.json" --out "NEW_TEST_RUN" --browser "CHROME_EXE"
python -m unittest discover -s app -p "test_*.py"
python -m unittest discover -s talking-head-qc/tools -p "test_*.py"
python -m unittest discover -s talking-head-qc/reference-lab -p "test_*.py"
python app/cli.py inventory "REFERENCE_DIRECTORY" --previous "OLD.json" --out "NEW.json"
```

Playwright/browser là dependency của acceptance test, không của app. Schema
private cases được mô tả trong `--help`. Không có fixture video khách trong repo.
Unit checks:41app +46QC +39reference-lab PASS; node syntax và diff whitespace PASS.

EXE development mới: `output/cutroom-release/Talking-Head-Cutroom-Windows-dev-v006/`
với tên `Talking Head Cutroom.exe`. Đã mở bản này bằng runtime đi kèm và kiểm
UI thật:7sources (3active/4archived),11exports;9exports cũ giữ nguyên hash,
2bản trước/sau mới có trong cùng workspace. Đã sao lưu workspace metadata trước
khi thêm chúng. Thumbnail và video byte-range HTTP206; viewport390/1280/1440
không tràn ngang,0JavaScript errors. Source ZIP có skill cùng2reference docs,
không chứa video/weights/Recordly project của khách.

**Release: NEEDS_REVIEW.** Bản mẫu có voice thật nhưng không có lượt nghe/xem
đủ bằng chứng trên exact master. Không điền tên reviewer hay READY thay người
duyệt. Đây là preview nghiệm thu workflow, chưa thay thế bản animation đã dựng
trước đó. Split02, transition slide/zoom-blur generic16, rounded PiP và inset10
vẫn là backlog. Máy Windows sạch chưa được kiểm; không quảng cáo đã chứng nhận.
