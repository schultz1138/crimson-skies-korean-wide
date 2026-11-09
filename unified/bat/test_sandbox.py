"""Maintainer integration checks: run CMD, then independently hash its outputs.

The adversarial suite uses artificial data only. No installed game is selected.
"""
from pathlib import Path
import argparse, ctypes, json, os, queue, subprocess, sys, threading, time, winreg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_sandbox import PROFILES, route, sha

def sac_state():
    """Read only. Never change Windows policy as part of a runtime test."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r'SYSTEM\CurrentControlSet\Control\CI\Policy',
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, 'VerifiedAndReputablePolicyState')[0]
    except OSError:
        return None


def command_errors(output):
    return b'is not recognized as an internal or external command' in output.lower()


class Suite:
    def __init__(self, root, report):
        self.root = root.resolve()
        self.content = self.root / 'Sandbox/Content'
        self.report = report
        self.logs = report.parent / (report.stem + '-logs')
        self.logs.mkdir(parents=True, exist_ok=True)
        self.manifest = json.loads((self.root / 'manifest-reference.json').read_text('utf-8-sig'))
        self.batch_sha = sha(self.root / 'Sandbox-Test.cmd')
        self.sac_before = sac_state()
        self.stock = next(v['hashes'] for v in self.manifest['inputs'] if v['id'] == 'stock')
        self.results = []
        self.sentinels = {
            self.content / 'unowned-test-sentinel.bin': b'UNOWNED CONTENT: preserve\x00\xff',
            self.root / 'State/unowned-test-sentinel.bin': b'UNOWNED STATE: preserve\x00\xff',
        }
        # Explicit maintainer fixture; never overwrite any pre-existing sentinel.
        for path, data in self.sentinels.items():
            if path.exists():
                assert path.read_bytes() == data
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)

    def vector(self, number=0):
        if number == 0:
            return self.stock
        return next(p['hashes'] for p in self.manifest['profiles'] if p['id'] == PROFILES[number - 1])

    def snapshot(self):
        return {str(p.relative_to(self.content)): sha(p) for p in self.content.rglob('*') if p.is_file()}

    def verify(self, number):
        for file, digest in zip(self.manifest['files'], self.vector(number)):
            assert sha(self.content / file['path']) == digest, file['path']
        for guard in self.manifest['guards']:
            assert sha(self.content / guard['path']) == guard['sha256'], guard['path']
        for path, data in self.sentinels.items():
            assert path.read_bytes() == data, str(path)
        assert not (self.root / 'State/.lock').exists()
        assert not (self.root / 'State/pending.txt').exists()

    def run(self, name, *args, success=True):
        start = time.monotonic()
        result = subprocess.run(
            [os.path.join(os.environ['SystemRoot'], 'System32', 'cmd.exe'), '/d', '/c',
             'call', str(self.root / 'Sandbox-Test.cmd'), *map(str, args)],
            capture_output=True, timeout=900)
        output = result.stdout + result.stderr
        (self.logs / (name + '.log')).write_bytes(output)
        ok = ((result.returncode == 0) if success else (result.returncode != 0)) and not command_errors(output)
        item = dict(test=name, passed=ok, exitCode=result.returncode,
                    seconds=round(time.monotonic() - start, 2))
        self.results.append(item)
        self.save()
        print(json.dumps(item), flush=True)
        assert ok, output.decode('utf-8', 'replace')[-2500:]
        return output

    def save(self):
        self.report.parent.mkdir(parents=True, exist_ok=True)
        passed = bool(self.results) and all(r['passed'] for r in self.results)
        completed = passed and self.results[-1]['test'] == 'independent-final-stock-and-sentinels'
        sac_after = sac_state()
        status = 'UNVERIFIED'
        if completed:
            status = ('LOCAL_SAC_ON_RUNTIME_PASSED' if self.sac_before == sac_after == 1
                      else 'FUNCTIONAL_TEST_PASSED_WITHOUT_CONFIRMED_SAC_ON')
        self.report.write_text(json.dumps(dict(
            schema=1, sandbox=str(self.root), batchSha256=self.batch_sha, tests=self.results,
            allPassed=passed, completed=completed,
            hashVerification='Independent Python SHA-256 of all 29 components + 4 guards after each apply/restore',
            sacStateBefore=self.sac_before, sacStateAtLastSave=sac_after,
            SACCompatibility=status,
            compatibilityScope='Local runtime only; browser download provenance, other PCs and game DLL loading are separate checks',
            installedGameWrites=0, settingsCacheSaveWrites=0), indent=2) + '\n', encoding='utf-8')

    def matrix(self):
        self.run('initial-check', '--check')
        self.verify(0)
        self.run('list', '--list')
        for number in range(1, 9):
            self.run(f'{number}-apply', '--apply', number)
            self.verify(number)
            self.run(f'{number}-check', '--check')
            self.run(f'{number}-restore', '--restore')
            self.verify(0)

    def rejected_without_content_writes(self, name, *args):
        before = self.snapshot()
        self.run(name, *args, success=False)
        assert self.snapshot() == before, name + ' changed sandbox content'

    def menu(self, wide=True, preset=3):
        """Feed real CHOICE prompts, then independently verify apply/restore."""
        self.verify(0)
        expected = (preset - 1) * 2 + int(wide) + 1
        process = subprocess.Popen(
            [os.path.join(os.environ['SystemRoot'], 'System32', 'cmd.exe'), '/d', '/c',
             'call', str(self.root / 'Sandbox-Test.cmd')],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        incoming = queue.Queue()
        transcript = bytearray()
        def reader():
            while True:
                byte = process.stdout.read(1)
                incoming.put(byte)
                if not byte:
                    break
        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()
        def until(token):
            received = bytearray()
            deadline = time.monotonic() + 120
            while token not in received:
                byte = incoming.get(timeout=max(.1, deadline - time.monotonic()))
                if not byte:
                    raise AssertionError('Menu ended early: ' + received.decode('utf-8', 'replace'))
                received.extend(byte); transcript.extend(byte)
                if byte == b'\n':
                    (self.logs / 'interactive-menu.log').write_bytes(transcript)
                if time.monotonic() > deadline:
                    raise TimeoutError('Menu prompt timeout')
        def choose(token, key):
            until(token)
            process.stdin.write(key + b'\r\n'); process.stdin.flush()
        passed = False
        try:
            choose(b'Voice/caption preset [1-4]: ', str(preset).encode('ascii'))
            choose(b'[Y/N]: ', b'Y' if wide else b'N')
            choose(b'Action [1-4]: ', b'2')
            until(('Applying ' + PROFILES[expected - 1]).encode('ascii'))
            until(b'RESULT: PASS')
            self.verify(expected)
            # PAUSE reads one key. Its localized message is not parsed.
            process.stdin.write(b'x\r\n'); process.stdin.flush()
            choose(b'Voice/caption preset [1-4]: ', b'1')
            choose(b'[Y/N]: ', b'N')
            choose(b'Action [1-4]: ', b'3')
            until(b'RESULT: PASS')
            self.verify(0)
            process.stdin.write(b'x\r\n'); process.stdin.flush()
            choose(b'Voice/caption preset [1-4]: ', b'1')
            choose(b'[Y/N]: ', b'N')
            choose(b'Action [1-4]: ', b'4')
            assert process.wait(timeout=10) == 0
            reader_thread.join(timeout=2)
            while not incoming.empty():
                transcript.extend(incoming.get_nowait())
            assert b'4. Korean voices + matched captions' in transcript
            assert not command_errors(transcript), transcript.decode('utf-8', 'replace')
            passed = True
        finally:
            if process.poll() is None:
                process.kill(); process.wait()
            (self.logs / 'interactive-menu.log').write_bytes(transcript)
            self.results.append(dict(test='interactive-choice-apply-restore-exit',
                                     preset=preset, profile=PROFILES[expected - 1], widescreen=wide, passed=passed))
            self.save()

    def adversarial(self):
        info = json.loads((self.root / 'experiment.json').read_text('utf-8'))
        assert info['kind'] == 'ARTIFICIAL_COMPATIBILITY_PROBE'
        self.run('switch-setup', '--apply', 2)
        self.rejected_without_content_writes('switch-rejected', '--apply', 8)
        self.run('switch-cleanup', '--restore')
        self.verify(0)

        wide = self.vector(2)
        changed = [i for i in range(29) if self.stock[i] != wide[i]]
        assert len(changed) >= 2
        file = self.content / self.manifest['files'][changed[0]]['path']
        data = file.read_bytes()
        altered = bytearray(data); altered[len(altered)//2] ^= 0x40
        try:
            file.write_bytes(altered)
            self.rejected_without_content_writes('unknown-same-size-rejected', '--apply', 2)
        finally:
            file.write_bytes(data)

        guard = self.content / self.manifest['guards'][0]['path']
        data = guard.read_bytes()
        try:
            guard.write_bytes(data + b'TAMPER')
            self.rejected_without_content_writes('guard-rejected', '--apply', 2)
        finally:
            guard.write_bytes(data)

        edge = route(self.manifest['files'][changed[0]], self.stock[changed[0]], wide[changed[0]])[0]
        delta = self.root / edge['path']
        data = delta.read_bytes()
        try:
            delta.write_bytes(data + b'TAMPER')
            self.rejected_without_content_writes('delta-rejected', '--apply', 2)
        finally:
            delta.write_bytes(data)

        tool = self.root / 'tools/xdelta3.exe'
        data = tool.read_bytes()
        try:
            tool.write_bytes(data + b'TAMPER')
            self.rejected_without_content_writes('decoder-rejected-before-launch', '--apply', 2)
        finally:
            tool.write_bytes(data)

        self.run('backup-setup', '--apply', 2)
        backup = self.root / f'State/original/original-{changed[0]}.bin'
        data = backup.read_bytes()
        try:
            backup.write_bytes(data + b'TAMPER')
            self.rejected_without_content_writes('backup-rejected-before-restore', '--restore')
        finally:
            backup.write_bytes(data)
        self.run('backup-cleanup', '--restore')
        self.verify(0)

        lock = self.root / 'State/.lock'
        lock.mkdir()
        try:
            self.rejected_without_content_writes('concurrent-lock-rejected', '--apply', 2)
        finally:
            lock.rmdir()

        state = self.root / 'State/state.txt'
        data = state.read_bytes()
        try:
            state.write_bytes(b'9\r\n')
            self.rejected_without_content_writes('invalid-state-rejected', '--apply', 2)
        finally:
            state.write_bytes(data)

        # Permit reads but deny replacement of the SECOND file. The FIRST file
        # can be committed; CMD must recover it after the second move fails.
        locked = self.content / self.manifest['files'][changed[1]]['path']
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        create = kernel.CreateFileW
        create.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                           ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        create.restype = ctypes.c_void_p
        close = kernel.CloseHandle
        close.argtypes = [ctypes.c_void_p]
        handle = create(str(locked), 0x80000000, 1, None, 3, 0x80, None)
        assert handle != ctypes.c_void_p(-1).value, ctypes.get_last_error()
        try:
            output = self.run('second-commit-failure-rolls-back', '--apply', 2, success=False)
            assert b'Restoring the verified stock copy' in output
            self.verify(0)
        finally:
            close(handle)
        self.run('after-rollback-check', '--check')
        self.verify(0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sandbox', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--adversarial', action='store_true')
    parser.add_argument('--menu-only', action='store_true')
    parser.add_argument('--menu-wide', choices=['Y', 'N'], default='Y')
    parser.add_argument('--menu-preset', type=int, choices=[1, 2, 3, 4], default=3)
    parser.add_argument('--adversarial-only', action='store_true')
    args = parser.parse_args()
    suite = Suite(args.sandbox, args.report)
    try:
        if args.menu_only:
            suite.menu(args.menu_wide == 'Y', args.menu_preset)
        elif args.adversarial_only:
            suite.adversarial()
        else:
            suite.matrix()
            if args.adversarial:
                suite.adversarial()
        suite.results.append(dict(test='independent-final-stock-and-sentinels', passed=True))
        suite.save()
        print('ALL PASSED', flush=True)
    except BaseException as error:
        suite.results.append(dict(test='suite-error', passed=False, error=str(error)))
        suite.save()
        raise
