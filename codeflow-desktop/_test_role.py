import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

_RE_STRICT = re.compile(r'(?<![a-z0-9])(?P<idx>0[1-9]|[1-9][0-9])[\s\-\.]+(?P<name>[A-Za-z][A-Za-z0-9]{1,19})(?![a-z0-9\-])', re.IGNORECASE)
_RE_LOOSE  = re.compile(r'(?<![a-z0-9])(?P<idx>[1-9][0-9]?)[\s\-\.]+(?P<name>[A-Za-z][A-Za-z0-9]{1,19})(?![a-z0-9\-])', re.IGNORECASE)
_ROLE_EXCLUDE = {'files','file','days','day','of','to','in','at','completed','background','shell'}
_OCR_IDX_FIX = str.maketrans('OI', '01')
_COMMON = ['PM','DEV','QA','OPS','PUBLISHER','COLLECTOR','WRITER','EDITOR','MARKETER','RESEARCHER','DESIGNER','BUILDER']

def _lev(a, b):
    if abs(len(a)-len(b)) > 3: return 99
    dp = list(range(len(b)+1))
    for i, ca in enumerate(a):
        ndp = [i+1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            ndp.append(min(ndp[j]+1, dp[j+1]+1, dp[j]+cost))
        dp = ndp
    return dp[-1]

def fuzzy(raw):
    s = raw.upper()
    if s in _COMMON: return s
    best, best_d = s, 99
    for c in _COMMON:
        d = _lev(s, c)
        if d < best_d: best_d, best = d, c
    return best if best_d <= 2 and abs(len(s)-len(best)) <= 2 else s

def find_role(text):
    cands = [text]
    t = text.strip()
    if t and t[0].upper() in 'OI':
        cands.append(t.translate(_OCR_IDX_FIX))
    for cand in cands:
        for pat in (_RE_STRICT, _RE_LOOSE):
            m = pat.search(cand)
            if m:
                raw = m.group('name').upper()
                if raw.lower() in _ROLE_EXCLUDE: continue
                name = fuzzy(raw)
                idx = int(m.group('idx'))
                return f'{idx:02d}-{name}'
    return ''

tests = [
    ('01-PUBLISHER',  '01-PUBLISHER'),
    ('01-PUBLLSHER',  '01-PUBLISHER'),
    ('01-PUBL1SHER',  '01-PUBLISHER'),
    ('03-WRLTER',     '03-WRITER'),
    ('04-EDLTOR',     '04-EDITOR'),
    ('02-COLLECTOR',  '02-COLLECTOR'),
    ('OI-PM',         '01-PM'),
    ('03-TESTONE',    '03-TESTONE'),   # 自定义名，不应纠错
    ('02-TEST',       '02-TEST'),
    ('1 of 15 Files', ''),
    ('Read COLLECTOR.md', ''),
]
ok = True
for text, exp in tests:
    got = find_role(text)
    status = 'OK  ' if got == exp else 'FAIL'
    if got != exp: ok = False
    print(f'  {status}  {text!r:28s} -> {got!r:22s}  期望={exp!r}')
print()
print('全部通过' if ok else '有失败！')
