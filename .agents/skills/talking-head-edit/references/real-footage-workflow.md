# Dựng footage thật với Talking Head Cutroom

## Kích hoạt và chạy local

Skill nằm ở `.agents/skills/talking-head-edit/SKILL.md`, được phát hiện theo cấu
trúc skill của repo. Gọi `$talking-head-edit`, hoặc yêu cầu:

> Dựng một video talking-head từ footage người dẫn, script và thư mục minh họa
> này. Đề xuất ba hook, chọn một hook có bằng chứng, dựng bản đầu đến CTA và chỉ
> ra các điểm cần tôi duyệt.

Đọc AGENTS.md nếu checkout có file đó. Không tạo mặc định đường dẫn máy tác giả.
Python 3.11+, FFmpeg/ffprobe trên PATH; không cần API hay model để dựng local.
Từ **checkout root** chạy:

```powershell
python app/app.py --data "PATH_TO_LOCAL_WORKSPACE"
```

Hoặc `& '.\Start Talking Head Cutroom.ps1' -Python python`. Launcher cũ
`Start Cutroom.ps1` vẫn hoạt động. Chọn thư mục dữ liệu đủ dung lượng. Windows
trong phiên hiện tại dùng helper D-storage đã có; đó không phải điều kiện cho
mọi người mua. Bản EXE development không thay thế kiểm thử sạch Windows.

## Intake → hook → kịch bản

1. Kiểm kê nguồn thật: hash, duration, video/audio streams, transcript/SRT và
   quyền sử dụng. Nghe cả câu để chọn take tự nhiên; giữ tiếng cuối, qualifier,
   nhịp nghỉ. Plain script trong app chỉ ước lượng thời gian; SRT cho mốc cụm,
   không tự trở thành word alignment. Thiếu khả năng nghe: ghi rõ chưa kiểm.
2. Viết một câu khán giả làm được gì, map tới asset/timecode chứng minh. Nếu
   thiếu kết quả, giữ phần nói và ghi chính xác pickup cần quay.
3. Reference có ba vai trò độc lập: học phong cách, chèn vào video, train.
   Lưu clip/hash, timecode, nội dung quan sát và capability (xem/nghe, frame,
   storyboard, cover, caption hoặc tài liệu). Ghi chú nghiên cứu do người dùng
   cung cấp là nguồn đi kèm, không phải agent đã xem/nghe. Không suy nhịp cắt
   từ storyboard 10 giây/mẫu, âm nhạc từ ảnh, hay hiệu quả từ lượng hiệu ứng.
4. Style profile ghi từng quyết định với `observed`, `inferred_to_test` hoặc
   `house_rule`: nhịp từng phần, vai trò người dẫn, layout, caption, minh họa,
   motion, khoảng lặng, music/SFX và CTA. Tham số tự đề xuất là thử nghiệm.
5. Đề xuất **đúng ba hook**: A câu hỏi công việc, B kết quả thật cho xem sớm,
   C lựa chọn/dấu hiệu dễ hiểu sai. Mỗi hook có lời, title, frame đầu, thời
   điểm bằng chứng, asset ID. Trích câu đã thu kèm source timecode; câu mới
   chỉ là chữ trên hình trung thực hoặc `pickup_required`. Chọn một hook.
6. Chia cụm 2–3 câu. Bảng kế hoạch bắt buộc:

| Nhịp / timecode lời | Lời thật hoặc pickup | Cần hiểu | Hình cần thấy | Asset / source in-out | Target → action → result | Voice / music / SFX | Component + tham số | Thiếu / QA |
|---|---|---|---|---|---|---|---|---|

Ghi ID câu/beat và occurrence cho lời lặp. Tách `source time` của thao tác khỏi
`presenter source time` và `master time`. Cho thấy vị trí trước lời chỉ tay,
contact bám hành động thật, giữ kết quả đọc được. Nếu UI chậm hơn lời: vào sớm
hơn, kéo dài B-roll trong phần nói phù hợp hoặc giữ kết quả; không tăng tốc
đến mức không đọc được, không vẽ thành công thay nguồn. CTA chỉ hứa tài nguyên
và hành động có thật. Chưa có hệ thống gửi tài liệu thì không tự thêm lời hứa.

## Dựng qua UI hiện có

Workspace → Import recordings → chọn một recording → Script → nhập **script
của take đó**. Import references riêng; Use for pacing không tự chèn footage.
Muốn minh họa: Show in video, rồi Cutaways đặt source in, duration, presenter
time/cue/occurrence. Nhập observed target/contact/result và source-pixel ROIs
nếu có. Không biết contact thì để trống, không lấy điểm bắt đầu insert làm click.

Full demo giữ giọng thật. Presenter PiP lấy từ cùng A-roll; Auto chọn một góc
ổn định cho cả cutaway, tránh control/result/caption. Không có góc an toàn thì
fallback Full demo, ghi quyết định trong plan. Góc editor chọn bị va chạm phải
báo lỗi, không âm thầm sửa override. Không bật layout chưa render-test.

Generate intro & demos tạo scene có source passage, editable plan và version.
Chỉ insert sau preview; sample-script không khớp lời thật vẫn là storyboard.
Style cho motion intensity, cue mute/gain/offset độc lập với Music Off/Auto/My
track. Batch chỉ áp dụng touched fields; không thay script/cue/scene riêng khi
chỉ thay profile. New take cần căn lại script và inserts.

Render selected từ UI tạo revision mới, frozen render recipe, project.json,
timeline, SRT, cue sheet, ba audio stems, MP4, reproduction report và QC. Exports
giữ lịch sử. Không đổi file cũ để chữa lỗi; feedback map version đã xem → beat
→ source time → master time mới. Cắt trước cue phải dời hình và âm cùng nhau.

## Nghiệm thu hai trường hợp bằng nguồn của người mua

**Có A-roll + thao tác thật:** dựng từ hook đến CTA; đo exact MP4, full decode,
count ±1 frame, LUFS −16±2/TP≤−1, sharp cue ±1 frame. Xem ở phone size/1×.
Nghe **toàn bộ** mix, đặc biệt tên, số, phủ định, cuối chữ và CTA; ghi câu nào
khó nghe, khoảng nào chỉ mới xem. Listening capability không được giả lập.

**Thiếu take hoặc proof:** render phần đủ nguồn, giữ người dẫn ở câu thiếu
minh họa, hoặc để lời mới thành title/storyboard. Ghi pickup cụ thể cùng mốc.
Ví dụ badge `For review` chưa chứng minh đã mở MP4; quay Recordly cảnh mở đúng
file vừa xuất, giữ playback đủ nhận ra. NEEDS_REVIEW nếu thiếu bằng chứng;
REVISE nếu đã thấy lỗi. Không dùng clip SFX-only để duyệt lời/nhạc dưới giọng.

Chạy lại các test cốt lõi, không cần customer media:

```powershell
python -m unittest discover -s app -p "test_*.py"
python -m unittest discover -s talking-head-qc/tools -p "test_*.py"
```

Ca render UI có nguồn riêng được mô tả ở `app/buyer_acceptance.py --help`.
Chạy trên checkout nguồn sạch, runtime và input ở ngoài repo. Test này không
phải bộ nghe tự động và không tự cấp READY. Skill được thực thi bởi agent đọc
SKILL.md và dùng editor thật; không có API “gọi skill” giả.

## Reference bổ sung liên tục

Khi người dùng thêm reference, kiểm kê tăng dần:

```powershell
python app/cli.py inventory "REFERENCE_DIRECTORY" --previous "OLD-inventory.json" --out "NEW-inventory.json"
```

Bỏ `--previous` ở lần đầu. Để chuẩn bị nhãn học riêng, dùng
`python app/learning_inventory.py REFERENCE_DIRECTORY --out NEW_RUN_DIRECTORY`.
Giữ inventory cũ và đối chiếu
hash/family trước khi trích moment; không đếm bản trùng thành video mới.
Một badge/title/motion mới cần source timecode, observation capability,
quyền và preview thử trên A-roll người dùng. Không tự import cả thư mục vào
batch, không tự train hay tự bật preset vì có file mới. Dữ liệu train/retrieval
và test vẫn tách nguồn; giữ các quyết định editor xác nhận riêng với suy luận.

V1 ưu tiên nguồn thật, rule kiểm được, local render và QC. Kho B-roll tự động,
ảnh tìm tự động, proactive cutting và train lớn là backlog; generative pilot
đã có vẫn là lab tùy chọn, không đưa raw recording lên cloud trong lượt dựng.
