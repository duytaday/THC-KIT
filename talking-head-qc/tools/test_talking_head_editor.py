import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from talking_head_editor import words

class WordBridgeTests(unittest.TestCase):
    def convert(self, rows):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);source=root/'asr.json';output=root/'edit/words.json'
        source.write_text(json.dumps({'segments':[{'words':rows}]},ensure_ascii=False),encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):words(source,output)
        return source,output

    def test_preserves_vietnamese_and_time_origin(self):
        _,out=self.convert([dict(word=' chào',start=12.25,end=12.7),dict(word=' GitHub',start=13,end=13.4)])
        self.assertEqual(json.loads(out.read_text(encoding='utf-8')),[dict(i=0,w='chào',t=12.25,e=12.7),dict(i=1,w='GitHub',t=13,e=13.4)])

    def test_does_not_replace_existing_transcript(self):
        source,out=self.convert([dict(word='có',start=1,end=2)])
        original=out.read_bytes()
        with self.assertRaises(FileExistsError):words(source,out)
        self.assertEqual(out.read_bytes(),original)

    def test_rejects_invalid_or_out_of_order_words(self):
        for rows in ([dict(word='x',start=2,end=1)], [dict(word='x',start=float('nan'),end=1)], [dict(word='x',start=2,end=3),dict(word='y',start=1,end=2)]):
            with self.subTest(rows=rows),self.assertRaises(ValueError):self.convert(rows)

if __name__=='__main__':unittest.main()
