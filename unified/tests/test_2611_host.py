"""Regression for the runtime-discovered 2611 preset fallback."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from port_2611_host import HOST_2611, preset_decoder, retarget_native_decoder


class HostDecoderTests(unittest.TestCase):
    def setUp(self):
        self.decoder = preset_decoder()
        self.base, self.rva, self.cache = 0x180000000, 0x2853000, 0x182862f00
        self.old, self.old_meta = self.decoder.emit(self.base+self.rva, self.cache)
        self.new, self.new_meta = self.decoder.emit(self.base+self.rva, self.cache, HOST_2611)

    def test_2611_guards_and_import_replace_2608_without_changing_unwind(self):
        self.assertNotEqual(self.old, self.new)
        self.assertEqual(len(self.old), len(self.new))
        self.assertEqual(self.old_meta['unwindFunctions'], self.new_meta['unwindFunctions'])
        asm = self.new_meta['assembly']
        for value in [HOST_2611['timestamp'], HOST_2611['imageSize'], HOST_2611['commandLineIat']]:
            self.assertIn(str(value), asm)
        self.assertNotIn('0xa52f0', asm)

    def test_native_transfer_requires_full_old_decoder_preimage(self):
        class PE:
            class OPTIONAL_HEADER:
                ImageBase = self.base
            @staticmethod
            def get_offset_from_rva(rva):
                self.assertEqual(rva, self.rva)
                return 0
        target = bytearray(self.old)
        proof = retarget_native_decoder(target, PE())
        self.assertEqual(target, self.new)
        self.assertEqual(proof['host'], '2611.323.502.0')
        target = bytearray(self.old)
        target[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, 'preimage'):
            retarget_native_decoder(target, PE())


if __name__ == '__main__':
    unittest.main()
