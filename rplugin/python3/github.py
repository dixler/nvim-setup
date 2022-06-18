#!/usr/bin/env python3
import os
import base64
import pynvim


def get_git_commentlink(fullpath: str, lines, notable_ref='origin/master', memo={}) -> str:
    d = os.path.dirname(fullpath)
    start = lines[0]
    end = lines[1]

    with os.popen(f"git -C '{d}' remote get-url origin") as p:
        base_url = p.read().strip()
        if 'github.com' not in base_url:
            raise Exception("Not a GitHub repository")

    with os.popen(f"git log -1 --format=format:%H {fullpath}") as p:
        commit = p.read().strip()

    with os.popen(f"git -C '{d}' rev-parse --show-toplevel") as p:
        root_path = p.read().strip() + '/'
        path = fullpath[len(root_path):]
    permalink = f"{base_url}/tree/{commit}/{path}"

    if not lines:
        return permalink

    if lines[0] == lines[1]:
        return f"{permalink}#L{lines[0]}"
    return f"{permalink}#L{lines[0]}-L{lines[1]}"

def get_git_permalink(fullpath: str, lines=None) -> str:
    d = os.path.dirname(fullpath)

    with os.popen(f"git -C '{d}' remote get-url origin") as p:
        base_url = p.read().strip()
        if 'github.com' not in base_url:
            raise Exception("Not a GitHub repository")
    #structure = "https://github.com/<org-name>/<repository>/tree/<commit-sha1>/<path/path/path>"

    with os.popen(f"git -C '{d}' rev-parse HEAD") as p:
        commit = p.read().strip()

    with os.popen(f"git -C '{d}' rev-parse --show-toplevel") as p:
        root_path = p.read().strip() + '/'
        path = fullpath[len(root_path):]
    permalink = f"{base_url}/tree/{commit}/{path}"

    if not lines:
        return permalink

    if lines[0] == lines[1]:
        return f"{permalink}#L{lines[0]}"
    return f"{permalink}#L{lines[0]}-L{lines[1]}"

class HLManager:
    def __init__(self, nvim):
        self.nvim = nvim
        self.marks = {}
    def mark_lines(self, start, end):
        bnr = self.nvim.current.buffer
        if bnr not in self.marks:
            self.marks[bnr] = {}
        
        for lineno in range(start, end+1):
            hl_id = f"CommentSign_{lineno}"
            self.nvim.command(f"highlight {hl_id} guibg=grey")
            sign_id = f"617{lineno}"
            self.nvim.command(f"sign define {sign_id} linehl={hl_id}")
            self.marks[bnr][sign_id] = self.nvim.command(f'sign place {sign_id} line={lineno} name={sign_id}') or True
    def unmark(self):
        for bnr in self.marks.keys():
            for lineno in self.marks[bnr].keys():
                self.nvim.command(f"sign unplace {lineno}")
        self.marks = {}

@pynvim.plugin
class TestPlugin(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.highlight_manager = HLManager(nvim)

    @pynvim.command("Permalink", nargs="*", range="", sync=False)
    def permalink(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        bnr = self.nvim.current.buffer
        start = self.nvim.api.buf_get_mark(bnr, "<")
        end = self.nvim.api.buf_get_mark(bnr, ">")
        permalink = get_git_permalink(fullpath, lines=[start[0], end[0]])
        self.nvim.feedkeys(f'gv')
        self.nvim.command(f'echom "{permalink}"')

    @pynvim.command("Comment", nargs="*", range="", sync=False)
    def comment(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        bnr = self.nvim.current.buffer
        start = self.nvim.api.buf_get_mark(bnr, "<")[0]
        end = self.nvim.api.buf_get_mark(bnr, ">")[0]
        permalink = get_git_commentlink(fullpath, lines=[start, end])
        self.nvim.command(f'echom "{permalink}"')
        self.highlight_manager.mark_lines(start, end)
        # TODO open buffer to read(or create if not exists) comment


        d = os.path.dirname(fullpath)
        with os.popen(f"git -C '{d}' rev-parse --show-toplevel") as p:
            root_path = p.read().strip() + '/.git/gossip'

        try: os.mkdir(root_path)
        except FileExistsError:...

        comment_filename = base64.b64encode(bytes(permalink, 'utf-8')).decode('utf-8')
        comment_filename += '.gossip.md'

        comment_path = os.path.join(root_path, comment_filename)
        self.nvim.command(f'split {comment_path}')

    @pynvim.autocmd("BufDelete", pattern="*.gossip.md")
    def clear_comment_hl(self, *args, **kwargs):
        self.highlight_manager.unmark()
