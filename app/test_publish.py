"""Posting receipts and revision guards using explicit non-media fixture bytes."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from threading import RLock
from unittest.mock import patch

import publish
from engine import media
from revisions import Conflict


class PostingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.video = Path(temp.name)/'edit.mp4'
        self.video.write_bytes(b'explicit master fixture')
        self.export = dict(id='master', job='host', revision=2, duration=5,
                           sha256=media.sha(self.video), folder=temp.name)
        self.ws = type('WorkspaceStub', (), {})()
        self.ws.export = lambda key: self.export if key == 'master' else None
        self.ws.lock = self.ws.archive_lock = RLock()
        self.ws.save = lambda: None
        self.ws.data = {'jobs': {'host': {'id':'host','revision':2,'latest':'master','settings':{}}}}
        self.body = dict(export='master', sha256=self.export['sha256'], caption='Đọc kết quả.', at=1)

    def save(self, **overrides):
        def render(video, folder, at, *args):
            name = 'thumbnail.png' if video is not None else 'cover.png'
            (folder/name).write_bytes(f'{name} {at}'.encode())
        with patch.object(publish,'thumbnail',side_effect=render), patch.object(
            media,'stream',return_value={'width':1080,'height':1920,'avg_frame_rate':'30/1'}
        ):
            return publish.save(self.ws, {**self.body, **overrides})

    def test_saved_thumbnail_versions_package_the_same_master(self):
        first, second = self.save(), self.save(at=2)
        self.assertNotEqual(first['thumbnail_sha256'],second['thumbnail_sha256'])
        for record in (first,second):
            with zipfile.ZipFile(publish.download(self.ws,'master',record['id'],'posting.zip')) as bundle:
                self.assertEqual(bundle.read('edit.mp4'),self.video.read_bytes())
                self.assertEqual(bundle.read('caption.txt').decode(),'Đọc kết quả.')
                saved = json.loads(bundle.read('manifest.json'))
                self.assertEqual(saved['source_frame'],record['source_frame'])
        self.assertEqual(self.ws.data['jobs']['host']['revision'],2)
        self.assertEqual(publish.selection(self.ws,'master')['id'],second['id'])

    def test_download_refuses_master_and_thumbnail_tampering(self):
        record = self.save()
        folder = publish.folder_for(self.video, record['id'])
        thumbnail = folder/'thumbnail.png'
        original = thumbnail.read_bytes()
        thumbnail.write_bytes(b'tampered')
        with self.assertRaises(Conflict):
            publish.download(self.ws,'master',record['id'],'posting.zip')
        thumbnail.write_bytes(original)
        self.video.write_bytes(b'tampered master')
        with self.assertRaises(Conflict):
            publish.download(self.ws,'master',record['id'],'posting.zip')

    def test_cover_rejects_stale_request_and_proof_overlap(self):
        record = self.save(title='Đọc kết quả')
        body = dict(export='master',package=record['id'],revision=1,sha256=self.export['sha256'])
        with self.assertRaises(Conflict):
            publish.set_cover(self.ws,body)
        with self.assertRaisesRegex(ValueError,'opening demo'):
            publish.apply(self.ws,{'posting_cover':{'export':'master','id':record['id']}},
                          {'keep':[[2,3]],'proof':[{'start':2.2,'end':2.7}]})
        self.assertEqual(self.ws.data['jobs']['host']['revision'],2)
