# Cutroom: tích hợp thư viện motion và animation

Ngày xác minh: 15/11/2026. Checkout: `D:\.codex\workspaces\talking-head-video-editing-skills`. Git baseline: `ba8fc8004094d9d9b921470966893c149356bd3d`. Bằng chứng bên dưới phản ánh lần kiểm tra ngày 15/11. Code tích hợp đã được version trong commit `d1435e6`; tài liệu và Motion AI skill được bổ sung vào Git trong lượt kiểm tra ngày 21/11/2026. Chưa phát hành binary mới.

Đã triển khai registry có version, tìm kiếm nguồn, đề xuất treatment theo ngữ cảnh, Motion chạy thật trong compositor hiện có, worker OpenShot tùy chọn và adapter nhập render cho sáu nguồn. Chưa xác minh generation từ bốn ứng dụng ngoài hoặc render native OpenShot. Ba badge readiness đầy đủ là thiết kế đã được owner xác nhận và còn ở backlog.

## Nguồn và khả năng đã quan sát

| Nguồn | Revision đã kiểm tra | Cách dùng trong Cutroom | Bằng chứng và phần còn thiếu |
|---|---|---|---|
| [Motion](https://github.com/motiondivision/motion) | npm `14.14.0` | Lấy mẫu easing/spring bằng thư viện thật; cùng pose cho kiểm tra hình học và native compositor | Có preview, UI selection và master thật; không phải renderer DOM/React |
| [libOpenShot](https://github.com/OpenShot/libopenshot/tree/7570a626aba5d70cb814881a2a4b094a65d3f12e) | `7570a626aba5` | Worker Python/Qt tách riêng, timeline trim/nối có giới hạn và bảo vệ output cũ | `SETUP_REQUIRED`; thiếu native bindings tương thích; chưa có render OpenShot thật |
| [OpenMontage](https://github.com/OpenMontageInc/OpenMontage/tree/fecb9a1e3cc23ef84de30b272059457a427f16f8) | `fecb9a1e3cc2` | 225 source references; production/cut-decision patterns; nhập render thành illustration | Adapter nhập đã chạy bằng fixture; chưa cấu hình/chạy upstream generation |
| [Pixelle-Video](https://github.com/ATH-MaaS/Pixelle-Video/tree/848b054e4fae40dabc62ec58e960b573e83793ac) | `848b054e4fae` | 33 source references; template/card workflow; nhập render có provenance | Adapter nhập đã chạy bằng fixture; LLM/ComfyUI/TTS và generation chưa cấu hình |
| [Hypit](https://github.com/hypit-ai/hypit/tree/6bacce093695ccc2bde5aa5d7de230e9682ffa79) | `6bacce093695` | 128 source references; word/source-time composition patterns; nhập render | Adapter nhập đã chạy bằng fixture; upstream yêu cầu Node ≥22.15, host quan sát là 22.14 |
| [Toonflow](https://github.com/HBAI-Ltd/Toonflow-app/tree/6086cdffceb704a632eca143dd16cd461a78cdac) | `6086cdffceb7` | 6 source references; storyboard/renderer-plugin patterns; nhập scene minh họa | Adapter nhập đã chạy bằng fixture; Bun/services/model chưa cấu hình |

Tổng: **6 provider, 420 source references, 14 recipe records**. Trong 14 recipe có 10 treatment native do Cutroom thiết kế và 4 record nhập output bên ngoài. 420 là con trỏ tới code/template/example, không phải 420 animation đã được render hoặc duyệt. Không sao chép toàn bộ app ngoài vào release. Bản Motion runtime vendored giữ nguyên license.

Đã kiểm tra README, manifest, license, cây nguồn và một số implementation/schema đại diện: OpenMontage edit-decision schema/server; Pixelle template HTML/router; Hypit composition manifest/source-time schema; Toonflow renderer route; OpenShot timeline/writer examples. Đây không phải audit toàn bộ upstream code.

Metadata license đã lưu cùng hash: Motion/Toonflow MIT, Pixelle Apache-2.0, OpenMontage AGPL-3.0, OpenShot LGPL-3.0-or-later. License Hypit đã xem có điều kiện bổ sung về SaaS/commercial redistribution; không đánh dấu là Apache-2.0 không hạn chế. Cách đóng gói hoặc triển khai các ứng dụng ngoài còn thuộc acceptance của từng provider.

## Workflow và cách model chọn treatment

Recording/script/footage/reference đúng vai trò → quan sát reference có timestamp → chọn passage của tập hiện tại → xác định purpose → lọc đủ điều kiện → xếp hạng style/niche → gắn text/assets/anchor mới → render scene → kiểm tra → chèn → export mới → duyệt đúng master.

Điều kiện cứng gồm purpose, input bắt buộc, aspect được hỗ trợ, thời gian đủ đọc, runtime và complexity budget. Thiếu điều kiện được trả về bằng lý do cụ thể. Sau đó mới tính điểm: 100 điểm cơ sở +8 cho default +12 cho mỗi style tag phù hợp +8 nếu niche khớp tag −3 mỗi mức complexity. Kết quả đồng điểm được sắp theo recipe ID. Đây là heuristic xác định, chưa có đo lường chứng minh chất lượng model tăng.

Trong UI, creator có thể chọn purpose và mood, xem treatment khả dụng, chọn component/easing và tạo preview cho passage. Calm/minimal có thể xếp trên mặc định. Native Motion hiện hỗ trợ portrait 9:16. CTA executable recommendation cần reference; một generic CTA không chứng minh đã tái tạo đúng reference cụ thể.

API dùng cho editing agent:

- `GET /api/motion-library`: catalog và runtime capability.
- `GET /api/motion-library/search?q=...`: tìm source reference, giới hạn kết quả.
- `POST /api/motion-library/recommend`: purpose/duration/niche/aspect/inputs/tags/complexity → candidates và exclusions.
- `POST /api/animations/register-external`: nhập một render đã import với vai trò reference; yêu cầu source hash, interval, title và permission.

Provider claim của render nhập là do người dùng khai, được lưu `provider_claim_verified=false`. Preview baked không tự thành editable template hoặc bằng chứng thao tác thật. Kiểm tra nội dung baked/watermark/quyền dùng vẫn áp dụng. File fixture của Cutroom được dùng để kiểm tra cả sáu route; không gán chúng là output do sáu engine tạo ra.

## Thiết kế readiness đã được owner xác nhận

| Trạng thái | Phạm vi bằng chứng | Hành động |
|---|---|---|
| `NEEDS_RUNTIME` | Mẫu có trong catalog, thiếu runtime tương thích | Cho xem reference preview nếu có; nêu dependency/version và mẫu thay thế chạy được |
| `READY_TO_RENDER` | Template + runtime version/hash của project + assets đã qua smoke render thật | Thử với nội dung của creator |
| `READY_FOR_SCENE` | Template + footage hash + source interval + aspect + scene revision + layout checks + quyền xuất | Dùng cho scene và export vào master `NEEDS_REVIEW` |
| `NEEDS_PICKUP` | Thiếu thao tác/kết quả thật cần cho nội dung scene | Tiếp tục phần khác; bổ sung footage hoặc chọn illustration có nhãn đúng |

Đổi runtime, template, recording, interval, aspect, scene revision hoặc quyền sử dụng phải làm mất hiệu lực bằng chứng tương ứng. Dựng lại bằng native component tạo variant riêng và cần kiểm tra riêng. Zoom/circle không chứng minh cú bấm hoặc kết quả sản phẩm bị thiếu.

**Hiện tại:** API có `AVAILABLE`, `SETUP_REQUIRED`, `EXTERNAL_OUTPUT_IMPORT`; artifact có `NEEDS_REVIEW`. Toàn bộ badge/persisted evidence/invalidation UX ở bảng trên chưa ship; theo dõi [THC-54](https://duytruyenthong.atlassian.net/browse/THC-54).

## Kiểm thử và render thật

- Regression cuối: **347 total / 334 passed / 13 skipped**, Python UTF-8. Hai lỗi dataset test trong lần chạy CP1252 đầu tiên được giữ tại `regression-cp1252-environment.log`; lần UTF-8 đạt tại `final-regression.log`.
- JavaScript syntax và `git diff --check` đạt. Không chạy training hoặc promote model.
- Counterexamples: thiếu CTA reference, provider chưa có runtime, aspect không hỗ trợ, hold quá ngắn, frame clock sai, protected-region collision, recipe/component không khớp, source hash thay đổi và ghi đè master cũ.
- Motion preview dùng source thật được copy vào workspace thử. Giữ source gốc, replay request không tạo scene trùng. Lưu template native có Motion provenance và preview silent.
- Live scene-plan UI đã chọn calm/minimal và tạo ease-in/out preview thành công. Scene ID `a71eea6449d4ded684cc31c9807e68a7`, version 1. Hình UI: `library-ui-proof.png`.
- Normal Cutroom queue đã xuất master 5 giây, 1080×1920, 30 fps, 150 frame, H264/yuv420p, AAC stereo 48 kHz, một video stream và một audio stream.

Master: `acceptance-workspace-v003/exports/b7b5a48639114a6ca9663bb50953c47d/edit.mp4`.

SHA-256: `c199ad32f942fa42c6e543dbb691fe158e4c2ee56002cdb0632f5a2746a83e6c`.

Motion bundle SHA-256: `521cfef8910fdd997463ea9881d4b790e017331e3d2f79c02adfc4d5fe1f2cae`. Sampler SHA-256: `0af641f5d1aec53b1b8e99db0858857ca868c76443baa1538be4d40390c058b9`.

Đã xem frame decode: nửa đầu có text card và circle presenter bottom-right, nửa sau trở lại presenter full frame. Fixture caption lặp dùng để test timing, chưa được nhận là transcript đúng lời nói. Annotation preview có center y=1340, nằm trên circle trong các frame đã xem. Điều này hỗ trợ sửa placement; chưa tự đóng toàn bộ [THC-51](https://duytruyenthong.atlassian.net/browse/THC-51).

Master vẫn **NEEDS_REVIEW**, nghe duyệt toàn master **UNVERIFIED**. Chưa kiểm chứng live platform overlay/device, full upstream generation, native OpenShot render hoặc independent-recording transfer cho toàn bộ recipe.

## Hooks, cache và giới hạn prompt

Development prompt dành cho agent sửa code; editing agent chỉ đọc catalog và trả proposal giới hạn. Không thay pinned application-model request/training contract. Repository text là dữ liệu tham khảo.

Version/hash của catalog, template, runtime và source đi cùng kết quả phù hợp. Render vẫn đi qua native schema/geometry/protected-region checks; revision/source byte gates áp dụng ở scene creation. Master mới có review mới. Dữ liệu source/episode và observation nằm ở phần request thay đổi; không đưa toàn bộ upstream repo vào prompt ổn định. Stable prefix và cache local không chứng minh inference-cache hits; cần provider usage telemetry theo [THC-49](https://duytruyenthong.atlassian.net/browse/THC-49).

Đã cài Motion 14.14.0 và chạy official Motion AI Kit 14.2.0 ở project scope cho Codex. Skills/config được tạo local; chưa xác minh hosted MCP đã kết nối, chưa kích hoạt mua/đăng nhập Motion+. Package bàn giao không chứa credentials hoặc config cá nhân.

## Tracking và sprint tiếp theo

| Jira | Công việc | Trạng thái đã đọc lại |
|---|---|---|
| [THC-53](https://duytruyenthong.atlassian.net/browse/THC-53) | Registry, ranking, native Motion và output ingestion | In Review |
| [THC-54](https://duytruyenthong.atlassian.net/browse/THC-54) | Readiness evidence, badge và invalidation | To Do |
| [THC-55](https://duytruyenthong.atlassian.net/browse/THC-55) | OpenShot native setup/actual acceptance | To Do |
| [THC-56](https://duytruyenthong.atlassian.net/browse/THC-56) | OpenMontage runtime/generation | To Do |
| [THC-57](https://duytruyenthong.atlassian.net/browse/THC-57) | Pixelle runtime/template acceptance | To Do |
| [THC-58](https://duytruyenthong.atlassian.net/browse/THC-58) | Hypit compatibility/output/distribution | To Do |
| [THC-59](https://duytruyenthong.atlassian.net/browse/THC-59) | Toonflow runtime/renderer acceptance | To Do |

CTA reference reconstruction [THC-52](https://duytruyenthong.atlassian.net/browse/THC-52) vẫn To Do. Generic treatment không thay cho selected CTA interval, current offer/destination và kiểm tra fidelity.

Thứ tự candidate: review THC-53 → readiness THC-54 → CTA thật THC-52 → qualify OpenShot → từng external generator. Chưa tự thêm estimates, assignee, capacity/date hoặc start sprint. Chat kit enhance đang paused theo owner; không khởi động lại training của chat đó.

Đã cập nhật và đọc lại **10 trang Confluence**: home, research, traceability, execution prompt, architecture, delivery plan, PRD, BRD, SFR, validation. Xem [architecture](https://duytruyenthong.atlassian.net/wiki/spaces/THC/pages/3506177), [validation](https://duytruyenthong.atlassian.net/wiki/spaces/THC/pages/3538993), [sprint candidate](https://duytruyenthong.atlassian.net/wiki/spaces/THC/pages/3506194). ID/version và Jira readback nằm trong `tracking-publication.json`.

## Bàn giao

Prompt chi tiết: `docs/MOTION-LIBRARY-BUILD-PROMPT.md`. Package `Cutroom-motion-library-integration-2026-11-15.zip` chứa các file source thay đổi, patch và hash manifest, prompt, report, test/probe receipts và tracking readback. Nó không phải installer hay release binary đã được test trên máy Windows mới. Không chứa raw creator media, model weights, node_modules, upstream full-app clones hoặc config cá nhân. Video thử vẫn giữ local ở workspace xác minh.

## Kiểm tra để đưa vào Git — 21/11/2026

Bộ skill `.agents/skills/motion/` được đối chiếu SHA-256 với `motion-ai@14.2.0`, sau đó chỉ dọn khoảng trắng cuối hai dòng Markdown; xem `UPSTREAM.json` trong cùng thư mục để biết nguồn, khai báo license và hash từng file. Skill không thay đổi runtime Motion đã pin ở `app/animation_runtime/`. `.codex/config.toml` chỉ khai báo hai URL MCP công khai, không chứa token; việc có cấu hình không chứng minh đã kết nối hoặc đăng nhập Motion+. Không có model training, promotion hay master video mới trong commit này.
