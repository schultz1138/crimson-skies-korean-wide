"""Release policy tests: standard library only; no executable is launched."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import release


def pe_bytes(signed=False):
    data = bytearray(515)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 0x3c, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 84, 224)
    struct.pack_into('<H', data, 88, 0x10b)
    struct.pack_into('<I', data, 88 + 92, 16)
    data[500:515] = b'owned-code-data!'
    if signed:
        data.extend(b'\0' * (-len(data) % 8))
        offset = len(data)
        data.extend(b'certificate-test')
        struct.pack_into('<II', data, 88 + 96 + 32, offset, 16)
        struct.pack_into('<I', data, 88 + 64, 123)
    return data


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'input'
        self.bundle.mkdir()
        (self.bundle / 'tools').mkdir()
        (self.bundle / 'patches').mkdir()
        (self.bundle / 'CrimsonSkiesSetup.exe').write_bytes(pe_bytes())
        (self.bundle / 'tools/xdelta3.exe').write_bytes(pe_bytes())
        delta = self.bundle / 'patches/000.vcdiff'
        delta.write_bytes(b'fixture delta')
        self.manifest = dict(schema=1, releaseId=release.NEXT_RELEASE,
            tool=dict(path='tools/xdelta3.exe', sha256=release.sha(self.bundle / 'tools/xdelta3.exe')),
            files=[dict(edges=[dict(path='patches/000.vcdiff', sha256=release.sha(delta), bytes=delta.stat().st_size)])] +
                  [dict(edges=[]) for _ in range(28)], profiles=[{}] * 12, guards=[{}] * 4)
        self.save_manifest()
        self.preparation = self.root / 'preparation.json'
        release.record_preparation(self.bundle, self.preparation)
        self.out = self.root / 'published'
        # Keep packaging output in a separate scratch directory for each test.
        self.final_temp = tempfile.TemporaryDirectory()
        self.out = Path(self.final_temp.name) / 'published'

    def tearDown(self):
        self.temp.cleanup()
        self.final_temp.cleanup()

    def save_manifest(self):
        release.save(self.bundle / 'manifest.json', self.manifest)

    def test_version_and_metadata(self):
        self.assertEqual(release.version(release.NEXT_RELEASE), '0.14.0.2')
        metadata = release.assembly_metadata(release.NEXT_RELEASE)
        self.assertIn('AssemblyProduct("Crimson Skies Korean Wide")', metadata)
        self.assertIn('AssemblyInformationalVersion("0.14.0-alpha.2")', metadata)

    def test_version_rejects_injection_and_overflow(self):
        for value in ['anything', 'CrimsonSkies-Unified-0.14.0-alpha.2"', 'CrimsonSkies-Unified-65535.1.0-alpha.1']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.version(value)

    def test_pin_rejects_invalid_hash(self):
        with self.assertRaises(ValueError):
            release.pins_source('invalid', release.NEXT_RELEASE)

    def test_signing_only_changes_code_identity_exclusions(self):
        signed = self.root / 'signed.exe'
        signed.write_bytes(pe_bytes(True))
        self.assertEqual(release.pe_code_identity(signed), release.pe_code_identity(self.bundle / 'CrimsonSkiesSetup.exe'))

    def test_code_modification_changes_identity(self):
        signed = self.root / 'signed.exe'
        changed = pe_bytes(True)
        changed[501] ^= 1
        signed.write_bytes(changed)
        self.assertNotEqual(release.pe_code_identity(signed), release.pe_code_identity(self.bundle / 'CrimsonSkiesSetup.exe'))

    def test_rejects_certificate_overlay(self):
        signed = self.root / 'signed.exe'
        signed.write_bytes(pe_bytes(True) + b'overlay')
        with self.assertRaises(ValueError):
            release.pe_code_identity(signed)

    def test_rejects_malformed_certificate_bounds(self):
        data = pe_bytes(True)
        struct.pack_into('<II', data, 88 + 96 + 32, 512, 90000)
        path = self.root / 'malformed.exe'
        path.write_bytes(data)
        with self.assertRaises(ValueError):
            release.pe_code_identity(path)

    def test_rejects_non_pe(self):
        path = self.root / 'bad.exe'
        path.write_bytes(b'hello')
        with self.assertRaises(ValueError):
            release.pe_code_identity(path)

    def test_valid_bundle(self):
        manifest, files = release.verify_bundle(self.bundle)
        self.assertEqual(len(files), 4)
        self.assertEqual(manifest['releaseId'], release.NEXT_RELEASE)

    def test_rejects_delta_tampering(self):
        (self.bundle / 'patches/000.vcdiff').write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            release.verify_bundle(self.bundle)

    def test_rejects_extra_delta(self):
        (self.bundle / 'patches/001.vcdiff').write_bytes(b'unexpected')
        with self.assertRaises(ValueError):
            release.verify_bundle(self.bundle)

    def test_rejects_path_traversal(self):
        for value in ['../escape', '/absolute', 'C:/outside', 'tools\\xdelta3.exe', 'a//b']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                release.child(self.bundle, value)

    def test_rejects_extra_executable(self):
        (self.bundle / 'unexpected.exe').write_bytes(pe_bytes())
        with self.assertRaises(ValueError):
            release.inventory(self.bundle)

    def test_rejects_disguised_executable(self):
        (self.bundle / 'README.txt').write_bytes(pe_bytes())
        with self.assertRaises(ValueError):
            release.inventory(self.bundle)

    def test_rejects_late_tool_signing(self):
        (self.bundle / 'tools/xdelta3.exe').write_bytes(pe_bytes(True))
        with self.assertRaisesRegex(ValueError, 'sign xdelta BEFORE'):
            release.finalize(self.bundle, self.preparation, self.out)
        self.assertFalse(self.out.exists())

    def test_signed_mode_rejects_unsigned_without_archive(self):
        with patch.object(release, 'verify_signature', side_effect=ValueError('NotSigned')):
            with self.assertRaisesRegex(ValueError, 'NotSigned'):
                release.finalize(self.bundle, self.preparation, self.out, require_signatures=True)
        self.assertFalse(self.out.exists())

    def test_second_binary_failure_does_not_create_archive(self):
        with patch.object(release, 'verify_signature', side_effect=[self.valid_signature(), ValueError('NotSigned decoder')]):
            with self.assertRaisesRegex(ValueError, 'NotSigned decoder'):
                release.finalize(self.bundle, self.preparation, self.out, require_signatures=True)
        self.assertFalse(self.out.exists())

    def valid_signature(self):
        return dict(Status='Valid', Accepted=True, ProductName=release.PRODUCT, FileVersion='0.14.0.2')

    def test_finalizer_packs_after_mock_signature_success(self):
        with patch.object(release, 'verify_signature', return_value=self.valid_signature()):
            report = release.finalize(self.bundle, self.preparation, self.out, require_signatures=True)
        archive = self.out / report['archive']
        self.assertEqual(release.sha(archive), report['sha256'])
        self.assertFalse(report['gameplayVerified'])
        self.assertFalse(report['automaticallyPublished'])
        self.assertEqual(report['signatureVerification'], 'verified')
        with zipfile.ZipFile(archive) as packed:
            self.assertEqual(len(packed.namelist()), 4)
            self.assertTrue(all(name.startswith(release.NEXT_RELEASE + '/') for name in packed.namelist()))

    def test_rejects_code_substitution_before_signature_check(self):
        code = pe_bytes()
        code[501] ^= 1
        (self.bundle / 'CrimsonSkiesSetup.exe').write_bytes(code)
        with patch.object(release, 'verify_signature') as verifier:
            with self.assertRaisesRegex(ValueError, 'code/resources changed'):
                release.finalize(self.bundle, self.preparation, self.out)
        verifier.assert_not_called()

    def test_rejects_metadata_mismatch(self):
        signature = self.valid_signature()
        signature['FileVersion'] = '0.14.0.1'
        with patch.object(release, 'verify_signature', return_value=signature):
            with self.assertRaisesRegex(ValueError, 'metadata mismatch'):
                release.finalize(self.bundle, self.preparation, self.out, require_signatures=True)
        self.assertFalse(self.out.exists())

    def test_rejects_modified_manifest_after_preparation(self):
        self.manifest['profiles'][0] = dict(unexpected=True)
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, 'Package changed'):
            release.finalize(self.bundle, self.preparation, self.out)

    def test_rejects_existing_output(self):
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError, 'new output'):
            release.finalize(self.bundle, self.preparation, self.out)

    def test_published_alpha1_cannot_be_repacked(self):
        self.manifest['releaseId'] = 'CrimsonSkies-Unified-0.14.0-alpha.1'
        self.save_manifest()
        release.record_preparation(self.bundle, self.preparation)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            release.finalize(self.bundle, self.preparation, self.out)

    def test_archive_race_does_not_leave_release_zip(self):
        original_write = zipfile.ZipFile.write
        def changed_write(archive, filename, arcname=None, *args, **kwargs):
            if str(filename).endswith('000.vcdiff'):
                Path(filename).write_bytes(b'changed during ZIP creation')
            return original_write(archive, filename, arcname, *args, **kwargs)
        with patch.object(release, 'verify_signature', return_value=self.valid_signature()), \
             patch.object(zipfile.ZipFile, 'write', changed_write):
            with self.assertRaisesRegex(ValueError, 'changed while archiving'):
                release.finalize(self.bundle, self.preparation, self.out)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_pe64_identity(self):
        data = pe_bytes()
        struct.pack_into('<H', data, 84, 240)
        struct.pack_into('<H', data, 88, 0x20b)
        struct.pack_into('<I', data, 88 + 108, 16)
        data[88+112+32:88+112+40] = b'\0' * 8
        path = self.root / 'x64.exe'
        path.write_bytes(data)
        self.assertEqual(len(release.pe_code_identity(path)), 64)

    def test_rejects_signed_tool_with_changed_code(self):
        original = self.bundle / 'tools/xdelta3.exe'
        signed = self.root / 'signed.exe'
        code = pe_bytes(True)
        code[501] ^= 1
        signed.write_bytes(code)
        with patch.object(release, 'BASE_TOOL', release.sha(original)), \
             patch.object(release, 'verify_signature') as verifier:
            with self.assertRaisesRegex(ValueError, 'code differs'):
                release.check_signed_tool(original, signed)
        verifier.assert_not_called()

    def test_normal_package_does_not_require_signing_service(self):
        with patch.object(release, 'verify_signature', side_effect=AssertionError('Signature service must not be called')):
            report = release.finalize(self.bundle, self.preparation, self.out)
        self.assertTrue((self.out / report['archive']).is_file())
        self.assertEqual(report['signatureVerification'], 'not-requested')
        self.assertEqual(report['signatures'], {})
        self.assertFalse(report['gameplayVerified'])

    def test_normal_package_rejects_post_preparation_certificate_change(self):
        (self.bundle / 'CrimsonSkiesSetup.exe').write_bytes(pe_bytes(True))
        with self.assertRaisesRegex(ValueError, 'Installer file changed'):
            release.finalize(self.bundle, self.preparation, self.out)
        self.assertFalse(self.out.exists())

    def test_legacy_preparation_can_make_normal_package(self):
        report = release.load(self.preparation)
        report['status'] = 'PREPARED_NOT_A_SIGNED_RELEASE'
        release.save(self.preparation, report)
        result = release.finalize(self.bundle, self.preparation, self.out)
        self.assertEqual(result['signatureVerification'], 'not-requested')

    def test_package_output_can_be_sibling_of_bundle(self):
        result = release.finalize(self.bundle, self.preparation, self.root / 'release')
        self.assertTrue((self.root / 'release' / result['archive']).is_file())

    def test_normal_package_rejects_tampered_delta(self):
        (self.bundle / 'patches/000.vcdiff').write_bytes(b'tampered delta')
        with self.assertRaises(ValueError):
            release.finalize(self.bundle, self.preparation, self.out)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
