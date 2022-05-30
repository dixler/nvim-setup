# %%
import traceback
from datetime import datetime
# %%

class BlameLine:
    def __init__(self, commit=None, email=None, timestamp=None, lineno=None, line=None, git_text=None):
        self.commit = commit
        self.email = email
        self.timestamp = timestamp
        self.lineno = lineno
        self.line = line
    def __repr__(self):
        return f'|{self.commit}|{self.email}|{self.timestamp}|{self.lineno}|{self.line}|'
    @staticmethod
    def from_line(line):
        s = line.split('(', maxsplit=1)
        commit = s[0].strip()
        s = s[1].split('>', maxsplit=1)
        email = s[0][1:].strip()
        date_format = "%Y-%m-%d %H:%M:%S %z"
        ts = datetime.strptime(s[1].lstrip()[:10+1+2+2+2+2+1+5], date_format)
        datestr = ts.strftime(date_format)
        s = s[1].split(datestr, maxsplit=1)[1].lstrip()
        s = s.split(')', maxsplit=1)
        lineno, line = s
        lineno, line = int(lineno), line[1:]
        return BlameLine(
            commit=commit,
            email=email,
            timestamp=ts,
            lineno=lineno,
            line=line,
        )
