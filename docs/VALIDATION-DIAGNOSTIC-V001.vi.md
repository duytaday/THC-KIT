# Chẩn đoán v007 trên source validation

Lượt này chạy mới sau dev17, dùng checkpoint v007 đã train thật trên Kaggle.
Không train thêm, không cập nhật RAG, không thay renderer/guard hoặc mặc định
sản phẩm. Đây là một lượt **development validation bổ sung**, không nằm trong
hai loss looks ban đầu của v007 và không được gọi là sealed final test.

## Protocol và phạm vi

Freeze trước inference: lấy record đầu tiên theo thứ tự JSONL cho mỗi cặp
`(source SHA, intro/demo)`. Kết quả8cụm từ4source khác train/RAG, nhưng chỉ có
1collection group bảo thủ; creator/family độc lập chưa xác minh. Cả8input có
style `balanced`; train có31Maverick/1balanced. Không dùng kết quả này để kết
luận chất lượng toàn bộ phong cách Maverick.

Giới hạn hợp đồng input đã phát hiện sau run:8validation inputs legacy đều
không có `layout_requirement`. Intro có intent “toàn màn hình” bằng văn bản,
nhưng retrieval3 lấy `motion-ref11-0`/`motion-ref11-1`, đều là host examples.
UI hiện tại luôn cung cấp lựa chọn full/host cho intro. Vì vậy đây không phải
một replay chứng minh current UI làm hỏng8cảnh, cũng không phải phép tách causal
riêng của weights. Đồng bộ input producer cho round kế tiếp phải dựa vào lựa
chọn/intent có sẵn, không lấy target label làm feature rồi báo model tự suy ra.

Ba nhánh cùng source contexts: rules; base tắt adapter +RAG; bật v007 +cùngRAG.
Model arms dùng prompt9, retrieval3, `source_json_v1`, cùng base/adapter bytes
và worker. So request receipts xác nhận tất cả các trường đó giống nhau.
RAG32rows chỉ từ train, source hashes của8case không giao với train/RAG.

Adapter SHA256:
`cc75c7e5b47961a8763ef249a49539e2c654d004f782e013008ac493ee4fbbd4`.
Hai fresh-process runs trên CUDA RTX3070Ti Laptop:
base `790a14f7257143b7aad4e8bc22cf8838` /110,266s;
tuned `a524f2249b83483b9a84b92fe091efcc` /112,265s.
Thời gian máy không phải thời gian editor sửa. Mỗi nhánh đúng1batch/8rows,
greedy seed3407, không retry để chọn output đẹp hơn.

## Kết quả mới

| Nhánh | Intro native đạt | Demo native đạt | Trong số đạt có compiler repair |
|---|---:|---:|---:|
|Rules|4/4|4/4|0|
|Base +RAG|1/4|2/4|0|
|V007 +cùngRAG|1/4|1/4|1demo|

Demo tuned đạt sau compiler repair có hai `hold_frames`156→135 để vừa nguồn;
không di chuyển word/action anchor. Giữ nguyên raw JSON và repair receipt,
không tính scene đó thành output thô đạt. Guard chặn5base và6tuned; không có
rules fallback được chèn vào kết quả model.

- Base:3case chạm vùng captions,2case thiếu12frames cuối để đọc.
- Tuned:6case chạm vùng captions. Có case chép đúng rect captions vào thẻ.
- Cả hai model vẫn cần cải thiện hình học nguồn và dự trù thời gian hold.
  Validation loss giảm không giải quyết được những lỗi này.

Phân tích **post-hoc**, đề xuất sau khi thấy lỗi base, so với nhãn agent chưa
được editor xác nhận: base khớp layout label0/4intro và0/4demo; tuned1/4intro,
4/4demo. Base lặp initial text ở3intro; tuned không lặp ở8case này. Các con số
đó mô tả sự đồng ý với nhãn thử nghiệm, không phải điểm fidelity do người duyệt.
Không dùng chúng làm metric promotion được đăng ký từ trước.

Rules đạt native nhưng chỉ dùng chữ đầu trong4demo, nên không bao phủ toàn bộ
inventory; layout demo cũng khác nhãn. Inventory có thể là lựa chọn hoặc danh
sách bắt buộc tùy brief, vì vậy không tự nâng omission diagnostic thành lỗi
validator chung. Cần diễn đạt rõ ý định/required content trong dữ liệu và duyệt
kết quả, thay vì coi8/8 native là8video đúng hoặc để checker tự ký chất lượng.

## Preview theo lựa chọn đã freeze

Chọn trước khi đọc kết quả model: intro `fullref-25-00`, source4,5–8,0s;
demo `fullref-25-01`, source8,0–10,8s. Dùng source thật có hash xác minh và
renderer native của app. Cả hai model từ chối hai case này, giữ failure records.
Chỉ rules tạo hai preview:

| Case | Frames | SHA256 |
|---|---:|---|
|Intro|105|78ff2971b7342219f372911682569f80ceff44cb598e3e1263bb631ba392eaaf|
|Demo|84|956d654612d189265fcb60859f73733a8c2326165be8f0af132fc6b83e87ccbf|

Cả hai NVENC/full decode PASS. Đã xem thumbnail270px: intro đủ ba câu tiếng
Việt trên nền phẳng; demo có một thẻ Excel và footage tham chiếu bên dưới.
Giữ label STORYBOARD/CẦN THU/CĂN LỜI. Chưa kiểm moving frames toàn cảnh hay
nghe audio; không gọi là bản giao hoặc software-result proof. Không admit clip
nào vào usable animation library, không đưa reference pixels vào gói sản phẩm.

## Quyết định và bước tiếp

Giữ adapter thử nghiệm, model gain **INCONCLUSIVE**. Không chạy thêm steps để
che failure. Dữ liệu hiện chỉ có3full-intro train labels và lệch mạnh về host;
đồng bộ `layout_requirement` giữa producer/train/validation và độ phủ bố cục
cần xử lý trước round huấn luyện kế tiếp. Nếu dùng failure
validation này để sửa dữ liệu/preset, các source đó tiếp tục là development,
không trở thành tập mới để công bố gain.

Vẫn cần tập B hoàn chỉnh chưa dùng train/RAG, brief/script/branding riêng,
reviewer có khả năng nghe xem toàn master1×, quiz/hook-payoff và timer sửa thực.
Đây là yêu cầu để đánh giá toàn video; tám component không thay thế nó.
Recordly vẫn đang chọn cửa sổ Facebook ở lần kiểm mới; đã mở riêng cửa sổ
FFmpeg preview và hướng dẫn chọn nguồn. Chưa ghi một capture mới.

Evidence private trên D:
`output/reference-training/validation-diagnostic-v001/`: protocol, results,
analysis, model-runs/request/stdout/stderr, render-protocol, render-results,
scene JSON/timeline/QC/media. Harness từ chối chạy lại khi đã có protocol;
không chạy lại mù khi chỉ mất output quan sát. Original checkpoint/cuts giữ nguyên.

Lệnh đọc lại evidence, không tạo inference lần hai:

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
Get-Content output/reference-training/validation-diagnostic-v001/results.json
Get-Content output/reference-training/validation-diagnostic-v001/analysis.json
Get-Content output/reference-training/validation-diagnostic-v001/render-results.json
```
