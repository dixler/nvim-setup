#!/usr/bin/env python3
import os
import base64
import pynvim

class GitPermalink:
    @staticmethod
    def from_permalink(permalink: str):
        remote, rest = permalink.split('/tree/', maxsplit=1)
        commit, rest = rest.split('/', maxsplit=1)

        if '#' not in rest:
            path = rest
            return GitPermalink(remote, path, commit)

        path, rest = rest.split('#', maxsplit=1)

        if not rest.startswith('L'):
            return GitPermalink(remote, path, commit)

        rest = rest.replace('L', '')
        start = None
        if '-' not in rest:
            start = int(rest)
            return GitPermalink(remote, path, commit, start=start)

        start, end = rest.split('-')
        start, end = int(start), int(end)

        return GitPermalink(remote, path, commit, start=start, end=end)

    def __init__(self, remote: str, path: str, commit: str, start=None, end=None):
        self.remote = remote
        self.path = path
        self.commit = commit
        self.start = start
        self.end = end

    def serialize(self):
        permalink = f"{self.remote}/tree/{self.commit}/{self.path}"

        if not self.start:
            return permalink

        permalink += f"#L{self.start}"
        if not self.end or self.start == self.end:
            return permalink

        permalink += f"-L{self.end}"
        return permalink

class GitRepo:
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def get_remote(self, remote='origin'):
        return self._git(f"remote get-url {remote}")

    def get_file_last_commit(self, path):
        return self._git(f"log -1 --format=format:%H {path}")

    def get_head_commit(self):
        return self._git(f"rev-parse HEAD")

    def to_relative_path(self, abs_path):
        abs_path = os.path.abspath(abs_path)
        return abs_path[len(self.root + '/'):]

    def is_dirty(self, path):
        out = self._git(f'diff {path}')
        return out != ''

    def _git(self, args):
        with os.popen(f"git -C '{self.root}' {args}") as p:
            return p.read().strip()

    @staticmethod
    def from_path(path='.'):
        d = os.path.dirname(path)
        with os.popen(f"git -C '{d}' rev-parse --show-toplevel") as p:
            root = p.read().strip()
            return GitRepo(root)
        

def get_git_commentlink(fullpath: str, start, end) -> str:
    repo = GitRepo.from_path(fullpath)

    remote = repo.get_remote()
    if 'github.com' not in remote:
        raise Exception("Not a GitHub repository")

    commit = repo.get_file_last_commit(fullpath)

    path = repo.to_relative_path(fullpath)

    return GitPermalink(remote, path, commit, start=start, end=end).serialize()

def get_git_permalink(fullpath: str, start=None, end=None) -> str:
    repo = GitRepo.from_path(fullpath)

    remote = repo.get_remote()
    if 'github.com' not in remote:
        raise Exception("Not a GitHub repository")

    commit = repo.get_head_commit()

    path = repo.to_relative_path(fullpath)

    return GitPermalink(remote, path, commit, start=start, end=end).serialize()

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
        permalink = get_git_permalink(fullpath, start=start[0], end=end[0])
        self.nvim.feedkeys(f'gv')
        self.nvim.command(f'echom "{permalink}"')

    @pynvim.command("Comment", nargs="*", range="", sync=False)
    def comment(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        bnr = self.nvim.current.buffer

        repo = GitRepo.from_path(fullpath)
        # check if file is dirty
        if repo.is_dirty(fullpath):
            self.nvim.command(f'echom "unable to add comments to dirty file(yet)"')
            return

        start = self.nvim.api.buf_get_mark(bnr, "<")[0]
        end = self.nvim.api.buf_get_mark(bnr, ">")[0]
        permalink = get_git_commentlink(fullpath, start, end)
        self.nvim.command(f'echom "{permalink}"')
        self.highlight_manager.mark_lines(start, end)
        # TODO open buffer to read(or create if not exists) comment


        repo = GitRepo.from_path(fullpath)
        root_path = os.path.join(repo.root, '.git', 'gossip')

        try: os.mkdir(root_path)
        except FileExistsError:...

        comment_filename = base64.b64encode(bytes(permalink, 'utf-8')).decode('utf-8')
        comment_filename += '.gossip.md'

        comment_path = os.path.join(root_path, comment_filename)
        self.nvim.command(f'split {comment_path}')

    @pynvim.autocmd("BufDelete", pattern="*.gossip.md")
    def clear_comment_hl(self, *args, **kwargs):
        self.highlight_manager.unmark()

    def get_comments(self, fullpath):
        with os.popen('git log --format=format:%H init.vim'):
            return []

    @pynvim.command("CommentsOn", nargs="*", range="", sync=False)
    def show_comments(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        comments = self.get_comments(fullpath)
        for comment in comments:
            self.highlight_manager.mark_lines(comment.start, comment.end)

    @pynvim.command("CommentsOff", nargs="*", range="", sync=False)
    def hide_comments(self, *args, **kwargs):
        self.highlight_manager.unmark()
