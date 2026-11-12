# Đồng bộ input bố cục · dev18

Sau diagnostic v007, đã sửa producer thay vì train lại cùng dữ liệu. Hàm chung
`motion_learning.declared_layout_context` được dùng bởi storyboard UI và exporter
reference. Chỉ khôi phục `layout_requirement` từ intent canonical đã khai:
“Intro toàn màn hình:” → full; “Giữ người dẫn…” / “Giữ nguyên người nói;” → host.
Không đọc target, reference target hoặc RAG để suy trường này. Intent chưa rõ
giữ nguyên; yêu cầu explicit mâu thuẫn intent thì từ chối để sửa, không ghi đè.
Giữ text, source quote, anchors, frames và protected regions.

Dataset export mới là version5, lưu từng normalization. Checker version5 chặn
input còn thiếu bố cục đã khai; version4 vẫn đọc được. Prompt2–9, retrieval3,
native validator/compiler và model weights không đổi. Đây là sửa input contract,
không biến các quyết định của target thành feature hay bỏ guard để tăng điểm.

## Evidence dữ liệu và quyết định train

Xuất mới từ annotations v007, dataset SHA
`d730708da98666e422b3be68b3b53466634f51f0b335e623dda0bc3ccafd7244`.
32train/33validation/10regression giữ nguyên source groups.18normalizations đều
ở validation:14full,4host. **Train.jsonl, test.jsonl và RAG trùng byte với v007.**
Không push một lượt Kaggle/clone checkpoint mới cho dữ liệu train không đổi.
Checkpoint dùng vẫn v007 đã train thật, SHA
`cc75c7e5b47961a8763ef249a49539e2c654d004f782e013008ac493ee4fbbd4`.
Muốn train tiếp có ích cần thêm/sửa train examples đã kiểm hoặc đổi hypothesis
có ngân sách riêng. Các reference validation/correction hiện tại không vào RAG.

**255 app tests PASS**: normalizer không sửa đầu vào, không suy target/layout
cho demo hoặc intent mơ hồ, từ chối conflict, export trước validate target và
backward compatibility version4/version5. Không tính test trước thành lần chạy mới.

## So cố định trên bốn intro đã xem

Protocol freeze trước inference. Chỉ đổi input `layout_requirement=full` theo
intent sẵn có; không đổi lời, ảnh, source span hoặc target. Bốn case từ diagnostic
cũ là development, không được gọi unseen mới. Model arms có cùng base/adapter,
prompt9/RAG3, decoder `source_json_v1`, worker và native guards. Fresh CUDA runs:
base `b863817c42d549398cab844e14056955`/32,547s;
tuned `c4cd0496a7f44d09b86c2a88f586c8bd`/33,297s.

| Nhánh | Trước: native / không repair | Sau: native / không repair |
|---|---|---|
|Base +RAG|1/4 /1/4|1/4 /0/4|
|Tuned +cùngRAG|1/4 /1/4|4/4 /2/4|

Sau sửa, cả4 lấy `house-title-states-v001` có input layout full, thay cho host
example. Đây là tác động lên input/retrieval và một so weights trong điều kiện
đó, không phải một lượt fine-tune mới hoặc bằng chứng whole-video gain.
Compiler tuned rút hold90→89 và39→38 trên hai scene để vừa source; không di
chuyển anchor. Base còn ba lỗi font/khung chữ; không fallback bằng rules.

Đã xuất5preview được validator chấp nhận (1base,4tuned), NVENC/full decode PASS.
Các cảnh đều là headline static, không tạo thêm entrance hoặc chứng minh đã học
animation mượt.4/4native chưa đủ: tuned hai scene nhiều mục chỉ giữ text đầu,
và base scene đạt cũng bỏ một mục. Giữ các v001 ở trạng thái REVISE cho phạm vi
tái dựng đã khai; không tự biến inventory coverage thành guard chung cho mọi
kiểu edit, vì brief có thể chỉ chọn nhấn một ý.

## Sửa tay v002, giữ v001 và tách khỏi train

Hai tuned scenes được sửa riêng theo nhãn native tái dựng cũ đã có source PTS.
Giữ source interval, context, model provenance và audio gốc; khôi phục các mục
thiếu cùng geometry tương ứng. Đây là **agent experimental correction**, không
phải output model mới hoặc quyết định người dùng. Không đưa corrections này vào
train/RAG; source group vẫn validation/development.

| Case | Source / master trước → sau | Thay đổi |
|---|---|---|
|fullref-25-00|source4,5–8,0; master0–3,5 giữ nguyên|Thêm “Mình không biết code”, “Bắt đầu từ đâu?” thành ba thẻ|
|fullref-27-16|source2,5–5,5; master0–3,0 giữ nguyên|Thêm “skills cho Claude trên GitHub” thành thẻ thứ hai|

v002 SHA lần lượt:
`ce6b07c8ddf7753659d7f5eecc9b2a752e7eec5268939f3be937e969317f2c09`;
`c10d1b4e7a20145c4473c7ba09c675f7e7a04a9716eccce5655239072f6070f3`.
105/90frames, full decode PASS; v001 hashes được kiểm lại giữ nguyên.
Đã xem thumbnails270px của cả4tuned v001 và2v002: phần chữ thêm có đủ dấu,
tách thẻ và không chạm caption status. Chỉ là still inspection; chưa đủ normal
speed reading/animation hoặc nghe. Không admit clip vào usable library.

## Phạm vi còn lại

Master khách vẫn NEEDS_REVIEW, model promotion INCONCLUSIVE. Còn cần tậpB mới
độc lập, đầy đủ demo/kết quả thật, phone1×watch/listen, hook/payoff/quiz và phút
sửa thực tế.4intro validation không thay whole-video benchmark hoặc xác nhận
style giống reference hoàn toàn. Recordly capture FFmpeg chưa có; giữ handoff
chọn đúng cửa sổ theo hướng dẫn trước, không tự ghi nguồn Facebook.

Evidence private: `output/reference-training/layout-input-v001/`: dataset v5,
protocol/results, worker requests/stdout/stderr, render-results, agent-repairs,
scene JSON/timelines/MP4/QC và test logs. Files nguồn/cut/checkpoint cũ giữ riêng.

Gói nội bộ dev18 được build từ commit sạch
`f75c0517b871ff36a6a157dc5b0b8dd3bbbc3452`:
153files/17.662.324bytes, ZIP SHA256
`9c1a798646968de99cff36d0775081a68d23b412c7658402fd002e78cc1605f7`.
Embedded Python3.12.10 render prefix5s/150frames/NVENC/full decode PASS.
SHA prefix `0f1392c83f2835e5df3def9a4d9aeda5cce32f1de7f5ae290a3c9faa846dae31`
trùng smoke dev17; actual UI contexts và prompt2–9 cũng qua kiểm bằng dữ liệu
recipe master thật. Prefix giữ original scene level −22,58LUFS/−9,86dBTP,
không là một whole-master loudness pass. GUI launcher/Windows sạch NOT_RUN;
starter distribution grant chưa xác nhận, chỉ là internal candidate.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
python -m unittest discover -s app -p 'test_*.py'
python app/reference_motion.py export D:\annotations.json --out D:\NEW-dataset-v5
# Không overwrite dataset cũ. Import model v007 không đổi weights/default.
python app/app.py --data D:\NEW-Cutroom-workspace --no-browser
```
