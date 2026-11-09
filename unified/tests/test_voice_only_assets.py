from pathlib import Path
import copy
import io
import json
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from voice_only_assets import MEMBER, replace_member_fixed_size
import caption_off_overlay


def archive(rows, padding=4096):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as packed:
        for name, data in rows:
            info = zipfile.ZipInfo(name, date_time=(2003, 6, 1, 12, 0, 0))
            info.external_attr = 0x1800000
            packed.writestr(info, data)
    raw = stream.getvalue()
    # Padding before the central directory is part of the supported allocation.
    import struct
    eocd = bytearray(raw[-22:])
    central = struct.unpack_from('<I', eocd, 16)[0]
    struct.pack_into('<I', eocd, 16, central + padding)
    return raw[:central] + bytes(padding) + raw[central:-22] + eocd


class CaptionOffAssetTests(unittest.TestCase):
    def test_original_script_replaces_injected_messages_and_preserves_voice(self):
        source = archive([(MEMBER, b'injected UserMsg KR_SH_TUT_001'),
                          ('audio/voice.wav', b'owned Korean voice bytes'),
                          ('objectives.dat', b'original objectives')])
        restored = b'original tutorial with its original dialogue triggers'
        result = replace_member_fixed_size(source, restored)
        self.assertEqual(len(result), len(source))
        with zipfile.ZipFile(io.BytesIO(source)) as before, zipfile.ZipFile(io.BytesIO(result)) as after:
            self.assertEqual(after.read(MEMBER), restored)
            self.assertNotIn(b'KR_SH_TUT_', after.read(MEMBER))
            for name in ('audio/voice.wav', 'objectives.dat'):
                self.assertEqual(after.read(name), before.read(name))
                self.assertEqual(after.getinfo(name).date_time, before.getinfo(name).date_time)
                self.assertEqual(after.getinfo(name).external_attr, before.getinfo(name).external_attr)

    def test_oversized_script_rejected(self):
        with self.assertRaisesRegex(ValueError, 'allocation'):
            replace_member_fixed_size(archive([(MEMBER, b'x')], padding=0), b'x' * 10000)

    def test_missing_tutorial_rejected(self):
        with self.assertRaisesRegex(ValueError, 'one tutorial'):
            replace_member_fixed_size(archive([('other', b'x')]), b'original')

    def test_duplicate_member_rejected(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            source = archive([(MEMBER, b'x'), (MEMBER, b'y')])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            replace_member_fixed_size(source, b'original')


class CaptionOffOverlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.target = self.root / 'target'
        (self.source / 'patches').mkdir(parents=True)
        real = Path(caption_off_overlay.__file__).with_name('caption-off-overlay') / 'overlay.json'
        self.overlay = json.loads(real.read_text('utf-8'))
        for edge in self.overlay['edges']:
            path = self.source / edge['path']
            path.write_bytes((edge['source'] + edge['target']).encode())
            edge['bytes'], edge['sha256'] = path.stat().st_size, caption_off_overlay.sha(path)
        old = {item['before'] for item in self.overlay['profileUpdates']}
        self.manifest = dict(files=[dict(path='unchanged', nodes=[], edges=[]) for _ in range(29)],
                             profiles=[dict(id=item['id'], hashes=['unchanged'] * 8 + [item['before']])
                                       for item in self.overlay['profileUpdates']] +
                                      [dict(id='k1-w1-d1-dub', hashes=['unchanged'] * 9)])
        self.manifest['files'][8] = dict(path='Game/DefaultPackage.data/Data0005',
                                       nodes=[dict(sha256=digest, bytes=170459136) for digest in old], edges=[])
        self.save()

    def save(self):
        (self.source / 'overlay.json').write_text(json.dumps(self.overlay), encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def test_changes_only_caption_off_data5_and_preserves_other_profiles(self):
        before = copy.deepcopy(self.manifest)
        after = caption_off_overlay.apply(self.manifest, self.target, self.source)
        self.assertEqual(self.manifest, before)
        for index in range(29):
            if index != 8:
                self.assertEqual(after['files'][index], before['files'][index])
        self.assertEqual(after['profiles'][-1], before['profiles'][-1])
        for original, patched in zip(before['profiles'][:4], after['profiles'][:4]):
            self.assertEqual(original['hashes'][:8], patched['hashes'][:8])
            self.assertNotEqual(original['hashes'][8], patched['hashes'][8])

    def test_modified_delta_rejected_before_copying_any_patch(self):
        (self.source / self.overlay['edges'][-1]['path']).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            caption_off_overlay.apply(self.manifest, self.target, self.source)
        self.assertFalse(self.target.exists())

    def test_unexpected_profile_source_rejected(self):
        self.manifest['profiles'][0]['hashes'][8] = 'unexpected'
        with self.assertRaisesRegex(ValueError, 'source changed'):
            caption_off_overlay.apply(self.manifest, self.target, self.source)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
