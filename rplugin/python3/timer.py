#!/usr/bin/env python3
import os
from datetime import datetime
import tempfile
from typing import List
import pynvim
import asyncio


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

def get_buffer_blame(nvim, bnr, memo={}) -> List[BlameLine]:
    text = '\n'.join(bnr[:])
    if bnr.name not in memo:
        memo[bnr.name] = {}
    if text not in memo.get(bnr.name):
        fullpath = nvim.funcs.expand('%:p')
        d = os.path.dirname(fullpath)
        filename = os.path.basename(fullpath)

        fd, path = tempfile.mkstemp()

        os.write(fd, bytes(text, 'utf-8'))
        os.close(fd)

        with os.popen(f"git -C '{d}' blame '{filename}' --content '{path}' -e") as p:
            blame = p.read()
            lines = [BlameLine.from_line(line) for line in blame.split('\n') if line != ""]
        
        memo[text] = lines
    return memo[text]

@pynvim.plugin
class TestPlugin(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.ns_id = nvim.api.create_namespace('demo')
        self.blame_lines = {}
        self.marks = {}

    @pynvim.command("Glame", nargs="*", range="", sync=False)
    def testfunction(self, *args, **kwargs):
        self.update()

    @pynvim.autocmd('BufReadPost')
    def on_bufenter(self, *args, **kwargs):
        self.update()

    @pynvim.autocmd('TextChanged')
    def on_textchanged(self, *args, **kwargs):
        self.update()

    def update(self):
        bnr = self.nvim.current.buffer
        new_blame_lines = get_buffer_blame(self.nvim, bnr)
        if new_blame_lines == self.blame_lines.get(bnr.name):
            return
        self.blame_lines[bnr.name] = new_blame_lines

        for blame in self.blame_lines[bnr.name]:
            hl_id = f"DiffGutter_{blame.commit}"
            self.nvim.command(f"highlight {hl_id} guibg=#{blame.commit[:6]}")
            sign_id = f"DiffGutterSign_{blame.commit}"
            sign_text = blame.email.split('@')[0][:2]
            self.nvim.command(f"sign define {sign_id} texthl={hl_id} numhl={hl_id} text={sign_text}")
            lineno = blame.lineno
            if lineno in self.marks:
                self.nvim.command(f'sign unplace {lineno}')
            self.marks[lineno] = self.nvim.command(f'sign place {lineno} line={lineno} name={sign_id}') or True
