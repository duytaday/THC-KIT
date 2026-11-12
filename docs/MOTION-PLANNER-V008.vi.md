# V008 — intro nhiều thẻ và nguồn preview im lặng

Ngày13/11/2026, đang chạy một experiment64optimizer steps theo protocol đã
freeze. **Chưa có checkpoint v008 được xác nhận COMPLETE** tại thời điểm ghi
phần chuẩn bị này. Không đổi mặc định sản phẩm hoặc ký master.

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

257app tests PASS. Metadata preview dùng “source audio”, vì audio nguồn có thể
im lặng hoặc không có presenter; không tự nhận mọi source đều có giọng nói.

## Lượt Kaggle đã gửi

Private dataset `duytruyenthong/talking-head-animation-spec-58f891bd45e9`,
kernel `duytruyenthong/talking-head-spec-training-58f891bd45e9`,version1.
10flat training data/code files, không raw media. Status lúc khởi chạy RUNNING.
Prompt9/retrieval3/Qwen pinned/optimizer/lr/sampling/64steps giữ nguyên như v007;
thay đổi experiment là16train examples mới. Initialization từ pinned base,
không resume adapter v007. Validation đã được xem là development; không là final.

Sau complete: kiểm provenance/steps/weight update/checkpoint hash, tải riêng
adapter/receipts, reload thật qua app. So base tắt adapter và tuned bật adapter
với cùng train-only RAG mới và decoder. Kiểm content coverage riêng với native
validity; giữ repair receipts, lỗi và mọi cut/model trước. Vlog5repo là regression,
không phải tập B mới để chứng minh whole-video gain.

Evidence private trên D:`output/reference-training/reference-spec-v008/`:
protocol, authored fixtures/project/timelines, inspections, recovery, token
curation v001–v003, dataset-v003, preflight, Kaggle logs và preparation.

```powershell
. .\talking-head-qc\tools\use_d_storage.ps1
kaggle kernels status duytruyenthong/talking-head-spec-training-58f891bd45e9
python -m unittest discover -s app -p 'test_*.py'
```

Còn cần kết quả run/reload/UI mới, tậpB hoàn chỉnh, người có khả năng nghe xem
toàn master1×, câu trả lời hook/proof và phút sửa thực. Không release/promote
chỉ vì dữ liệu đã upload hoặc nhiều fixture hơn.
