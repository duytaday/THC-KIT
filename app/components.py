"""Conservative component inventory; availability is not editorial sign-off."""
NAMES = ['Người dẫn toàn khung','Người dẫn trên/dưới demo','Người dẫn PiP trên demo',
         'Demo toàn khung','Chữ hook','Phụ đề theo cụm lời','Nhấn từ hoặc số',
         'Lower third','Nhãn bước/chương','Phóng vùng chi tiết','Callout',
         'Nhấn tiếp xúc','Giữ kết quả','So sánh A/B','Minh họa nội dung',
         'Chuyển cảnh','Nhạc dưới giọng','SFX sự kiện','Thẻ CTA','Xem sớm kết quả']


def inventory():
    # Only these variants are covered by the real-footage buyer render test.
    tested = {1,3,4,6,11,12,13,17,18}
    rows = [dict(id=f'{i:02}',version='1.0',name=name,specified=True,
                 render_tested=i in tested,editorially_approved=False,
                 limitation=('Generic split not implemented' if i==2 else
                             'Cut only; slide/zoom-blur remain proposals' if i==16 else
                             'Full-master viewing/listening and per-job evidence still required'))
            for i,name in enumerate(NAMES,1)]
    import motion_specs
    for row in rows:
        native=row['id'] in motion_specs.COMPONENTS
        row.update(renderer='native_ass_data_v1' if native else 'episode_compositor' if row['id'] in ('01','03','04','06','17','18','20') else None,
                   kind='native_editable' if native else 'composition' if row['id']!='02' else 'specified_only',
                   parameters=['text','rect','font_size','keyframes','hold_frames','theme','sfx'] if native else ['pip_shape','pip_corner','pip_width','pip_crop'] if row['id']=='03' else [],
                   requirements=['Current episode source interval and words']+(['Observed control/contact/result anchors'] if row['id'] in ('11','12','13') else []),
                   selectable_in_scene_plan=row['id'] in ('05','07','08','09','15','19'),
                   validation='Previously render-tested variant; current parameters need export verification' if row['render_tested'] else 'Implementation/specification only; selected variant needs render verification')
    return dict(specified=len(rows),render_tested=len(tested),editorially_approved=0,
                evidence='docs/REAL-FOOTAGE-RESULTS.vi.md',components=rows)
