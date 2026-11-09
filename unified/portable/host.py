"""Windows filesystem/host binding and narrowly owned settings. MIT."""
from pathlib import Path
from contextlib import contextmanager
import base64, ctypes, hashlib, json, msvcrt, os, re, stat, uuid, winreg
from ctypes import wintypes as W

FAMILY = 'Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_ksqcvrsvwz2jp'
REGISTRATION = (r'Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion'
                r'\AppModel\Repository\Packages\Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR_2608.3123.1.0_x64__ksqcvrsvwz2jp')
K = ctypes.WinDLL('kernel32', use_last_error=True)
def api(name, result, *args):
    fn = getattr(K, name); fn.restype = result; fn.argtypes = list(args); return fn
create = api('CreateFileW', W.HANDLE, W.LPCWSTR, W.DWORD, W.DWORD, W.LPVOID, W.DWORD, W.DWORD, W.HANDLE)
close = api('CloseHandle', W.BOOL, W.HANDLE)
replace_file = api('ReplaceFileW', W.BOOL, W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, W.DWORD, W.LPVOID, W.LPVOID)
create_mutex = api('CreateMutexW', W.HANDLE, W.LPVOID, W.BOOL, W.LPCWSTR)
wait = api('WaitForSingleObject', W.DWORD, W.HANDLE, W.DWORD)
release_mutex = api('ReleaseMutex', W.BOOL, W.HANDLE)

def need(ok, message):
    if not ok: raise ValueError(message)

def guard(path, exists=True):
    p = Path(os.path.abspath(path))
    need(p.drive and not str(p).startswith('\\\\'), 'A local drive is required')
    for part in reversed([p, *p.parents]):
        try: info = part.lstat()
        except FileNotFoundError: continue
        need(not info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT,
             'Linked/reparse path refused: ' + str(part))
    if exists: need(p.exists(), 'Missing path: ' + str(p))
    return p

def child(root, relative):
    need(isinstance(relative, str) and relative and ':' not in relative and '\\' not in relative,
         'Invalid relative path')
    need(all(s and s not in ('.', '..') for s in relative.split('/')), 'Invalid relative path')
    return guard(Path(root).joinpath(*relative.split('/')), False)

def mkdir(path):
    path = guard(path, False); path.mkdir(parents=True, exist_ok=True); return guard(path)

@contextmanager
def reading(path):
    path = guard(path)
    handle = create(str(path), 0x80000000, 1, None, 3, 0x80, None)
    if handle == W.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    try: fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
    except BaseException: close(handle); raise
    with os.fdopen(fd, 'rb') as stream: yield stream

def sha(path):
    with reading(path) as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()

def digest(data): return hashlib.sha256(data).hexdigest()

def verify(path, expected, size=None):
    path = guard(path)
    need(size is None or path.stat().st_size == size, 'File size differs: ' + str(path))
    need(sha(path) == expected, 'SHA-256 differs: ' + str(path))

def copy_new(source, target, expected):
    target = guard(target, False)
    with reading(source) as src, target.open('xb') as dst:
        while block := src.read(1048576): dst.write(block)
        dst.flush(); os.fsync(dst.fileno())
    verify(target, expected)

def atomic(target, ready, before, after):
    verify(target, before); verify(ready, after)
    need(Path(target).drive.lower() == Path(ready).drive.lower(), 'Replacement must stay on the same drive')
    if not replace_file(str(target), str(ready), None, 0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())
    verify(target, after)

def atomic_json(path, data):
    path = guard(path, False); temp = path.parent / ('.receipt-' + uuid.uuid4().hex + '.tmp')
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    with temp.open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    try:
        if path.exists(): atomic(path, temp, sha(path), digest(raw))
        else: os.rename(temp, path)
    finally:
        if temp.exists(): guard(temp).unlink()

def load_json(path, limit=4194304):
    need(guard(path).stat().st_size <= limit, 'JSON too large')
    with reading(path) as stream: return json.loads(stream.read().decode('utf-8-sig'))

def root_id(root): return digest(str(guard(root)).rstrip('\\/').upper().encode('utf-8'))

@contextmanager
def mutex(root):
    handle = create_mutex(None, False, 'Local\\CrimsonSkies-KoreanPatch-' + root_id(root))
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    held = False
    try:
        held = wait(handle, 0) in (0, 0x80)
        need(held, 'Another installer owns this game')
        yield
    finally:
        if held: release_mutex(handle)
        close(handle)

class ProcessEntry(ctypes.Structure):
    _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('pid', W.DWORD),
                ('heap', ctypes.c_size_t), ('module', W.DWORD), ('threads', W.DWORD),
                ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD), ('exe', W.WCHAR * 260)]
snapshot = api('CreateToolhelp32Snapshot', W.HANDLE, W.DWORD, W.DWORD)
first = api('Process32FirstW', W.BOOL, W.HANDLE, ctypes.POINTER(ProcessEntry))
next_process = api('Process32NextW', W.BOOL, W.HANDLE, ctypes.POINTER(ProcessEntry))
def stopped():
    handle = snapshot(2, 0)
    if handle == W.HANDLE(-1).value: raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = ProcessEntry(); entry.size = ctypes.sizeof(entry)
        more = first(handle, ctypes.byref(entry))
        while more:
            need(entry.exe.lower() not in ('emu.exe', 'emumenu.exe'), '게임과 플레이 창을 종료하세요 / Close game and Play window')
            more = next_process(handle, ctypes.byref(entry))
    finally: close(handle)

def registered_root():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRATION) as key:
            # WindowsApps registration itself can be an OS-maintained junction
            # to XboxGames. Resolve that registration, then reject reparse
            # components in the canonical write target as usual.
            return guard(Path(winreg.QueryValueEx(key, 'PackageRootFolder')[0]).resolve(strict=True))
    except FileNotFoundError: return None

def registered(content):
    root = registered_root()
    if root is None: return False
    return all((Path(content) / name).exists() and (root / name).exists()
               and os.path.samefile(Path(content) / name, root / name)
               for name in ('Emu.exe', 'appxmanifest.xml'))

def sac_state():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\CI\Policy') as key:
            return winreg.QueryValueEx(key, 'VerifiedAndReputablePolicyState')[0]
    except OSError: return None

class Locations:
    def __init__(self, content):
        local = Path(os.environ['LOCALAPPDATA'])
        self.backups = local / 'CrimsonSkiesBAT/Backups'
        self.legacy = local / 'CrimsonSkiesUnified/Backups'
        base = local / 'Packages' / FAMILY / 'LocalCache/Local'
        self.settings = base / 'Settings.ini' if registered(content) else None
        self.cache = base / 'VirtualDrive/Harddisk/Cache1/RawPartition' if registered(content) else None
    def stopped(self): stopped()
    def point(self, name): pass

KEYS = ('game-language', 'scaling')
SCALES = ['640×480 (4:3)', '1280×960 (4:3)', '1920×1440 (4:3)', '2560×1920 (4:3)',
          '800×600 (4:3)', '1024×768 (4:3)', '1280×720 (720p, 16:9)', '1600×900 (16:9)',
          '1920×1080 (1080p, 16:9)', '2560×1440 (1440p, 16:9)', '3840×2160 (4K, 16:9)']
LEGACY = ['1x - 640x480', '2x - 1280x960', '3x - 1920x1440', '4x - 2560x1920']
ALIASES = {v: (i, v) for i, v in enumerate(SCALES)}
ALIASES.update({v: (i, SCALES[i]) for i, v in enumerate(LEGACY)})
for i, key in [(4,'800x600'),(5,'1024x768'),(6,'1280x720'),(7,'1600x900'),(8,'1920x1080'),(9,'2560x1440'),(10,'3840x2160')]:
    ALIASES['res-' + key] = (i, SCALES[i])
ALIASES['3840×2160 (4K, 16:9, AA 자동 끔)'] = (10, SCALES[10])
def pattern(key): return re.compile(r'(?:\A|(?<=[\r\n]))(?P<line>\ufeff?[^\S\r\n]*' + re.escape(key) + r'[^\S\r\n]*=[^\r\n]*)(?=[\r\n]|\Z)', re.I)
def settings_text(raw):
    if raw is None: return None
    need(len(raw) <= 65536 and b'\0' not in raw, 'Unsupported settings')
    text = raw.decode('utf-8')
    for key in KEYS: need(len(pattern(key).findall(text)) <= 1, 'Duplicate settings key: ' + key)
    return text
def read_settings(path):
    if path is None: return None
    guard(path, False)
    if not Path(path).exists(): return None
    with reading(path) as f: raw = f.read(65537)
    settings_text(raw); return raw
def line(text, key):
    match = pattern(key).search(text or '')
    return match['line'] if match else None
def set_line(text, key, value):
    match = pattern(key).search(text)
    return text if match is None else text[:match.start('line')] + (value or '') + text[match.end('line'):]
def value(item): return item.split('=', 1)[1].strip() if item is not None else None
def origin(raw):
    text = settings_text(raw)
    return {key: line(text, key) for key in KEYS}
def valid_origin(saved):
    need(isinstance(saved, dict) and set(saved) == set(KEYS), 'Invalid settings origin')
    for key, item in saved.items():
        need(item is None or isinstance(item, str) and len(item) <= 65536 and not any(c in item for c in '\r\n\0')
             and line(item, key) == item, 'Invalid settings origin line')
def plan_settings(raw, saved, korean, wide, restore=False):
    valid_origin(saved); text = settings_text(raw)
    if text is None: return None
    def put(key, wanted):
        nonlocal text
        current = line(text, key)
        if current is not None:
            head, tail = current.split('=', 1)
            lead = tail[:len(tail)-len(tail.lstrip())]
            trail = tail[len(tail.rstrip()):]
            text = set_line(text, key, head + '=' + lead + wanted + trail)
    language = value(line(text, KEYS[0])); scale = value(line(text, KEYS[1]))
    if restore:
        if language == 'ko-KR': text = set_line(text, KEYS[0], saved[KEYS[0]])
        if scale is not None:
            need(scale in ALIASES, 'Unknown resolution key'); text = set_line(text, KEYS[1], saved[KEYS[1]])
    else:
        if korean: put(KEYS[0], 'ko-KR')
        elif language == 'ko-KR':
            text = set_line(text, KEYS[0], saved[KEYS[0]])
            old = value(saved[KEYS[0]])
            if old is not None and old not in ('System','Deutsch','English','français','한국어','中文（繁體）'): put(KEYS[0], 'System')
        if scale is not None:
            need(scale in ALIASES, 'Unknown resolution key')
            index, canonical = ALIASES[scale]
            put(KEYS[1], canonical if wide else LEGACY[index if index < 4 else 1])
    result = text.encode('utf-8'); settings_text(result); return result
def encode(raw): return None if raw is None else base64.b64encode(raw).decode('ascii')
def decode(text):
    if text is None: return None
    need(isinstance(text, str) and len(text) <= 90000, 'Invalid settings journal')
    raw = base64.b64decode(text, validate=True); settings_text(raw); return raw
def rollback_settings(current, before, after):
    if current == before or before == after: return current
    if current == after: return before
    need(current is not None and before is not None and after is not None, 'Settings externally created/deleted')
    now, old, applied = map(settings_text, (current, before, after))
    for key in KEYS:
        a,b,c = line(old,key),line(applied,key),line(now,key)
        if a == b or c == a: continue
        need(c == b, 'Recovery refused concurrent change of ' + key)
        now = set_line(now, key, a)
    return now.encode('utf-8')
