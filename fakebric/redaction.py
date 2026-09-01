import re


_SECRET = re.compile(r'''(?ix)
    (authorization\s*[:=]\s*bearer\s+|
     ["']?(?:token|secret|password|api[_-]?key)["']?\s*[:=]\s*["']?)
    ([^\s,"';}]+)
''')


def redact_sensitive(value: object) -> str:
    text=str(value)
    return _SECRET.sub(lambda match: match.group(1)+'[REDACTED]', text)
