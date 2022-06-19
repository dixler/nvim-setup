#!/usr/bin/env python3
import os
import glob
import base64
import pynvim

class GossipComment:
    def __init__(self, path):
        self.path = path
        with open(path) as f:
            self.text = f.read()

        filename = os.path.basename(path)
        b64ref, _ = filename.split('.gossip.md',maxsplit=1)
        uri = base64.b64decode(b64ref).decode('utf-8')
        self.permalink = GitPermalink.from_permalink(uri)

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

    def get_file_commits(self, path):
        return self._git(f"log --format=format:%H {path}").split('\n')

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
        self.ns_id = nvim.api.create_namespace('gossip')
        self.marks = {}
        self.extmarks = {}
        self.hl_id = f"CommentSign"
        self.nvim.command(f"highlight {self.hl_id} guibg=#333333")
    def mark_lines(self, start, end):
        bnr = self.nvim.current.buffer
        if bnr not in self.marks:
            self.marks[bnr] = {}
        for lineno in range(start, end+1):
            sign_id = f"617{lineno}"
            self.nvim.command(f"sign define {sign_id} linehl={self.hl_id}")
            self.marks[bnr][sign_id] = self.nvim.command(f'sign place {sign_id} line={lineno} name={sign_id}') or True
    def mark_comment(self, comment):
        bnr = self.nvim.current.buffer
        if bnr not in self.extmarks:
            self.extmarks[bnr] = {}
        
        self.mark_lines(comment.permalink.start, comment.permalink.end)
        extmark_id = self.nvim.api.buf_set_extmark(bnr, self.ns_id, comment.permalink.start-1, 0, dict(
            virt_lines=[
                [['-'*self.nvim.current.window.width+'\n', self.hl_id]],
                *[[[line, self.hl_id]] for line in comment.text.split('\n')],
                [['-'*self.nvim.current.window.width+'\n', self.hl_id]],
            ],
            virt_lines_above=True,
            line_hl_group=self.hl_id,
       ))
        self.extmarks[bnr][extmark_id] = True

    def unmark(self):
        for bnr in self.marks.keys():
            for lineno in self.marks[bnr].keys():
                self.nvim.command(f"sign unplace {lineno}")
        self.marks = {}
        for bnr in self.extmarks.keys():
            for mark_id in self.extmarks[bnr].keys():
                self.nvim.api.buf_del_extmark(bnr, self.ns_id, mark_id)
        self.extmarks = {}
        

@pynvim.plugin
class TestPlugin(object):

    def __init__(self, nvim):
        self.nvim = nvim
        self.highlight_manager = HLManager(nvim)
        self.comment_buffer = None
        self.comment_window = None
        self.comments = {}

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
        # TODO probably break this out
        repo = GitRepo.from_path(fullpath)
        gossip_glob = os.path.join(repo.root, '.git', 'gossip', '*.gossip.md')
        commits = set(repo.get_file_commits(fullpath))
        fpath = repo.to_relative_path(fullpath)
        comments = []
        for path in glob.glob(gossip_glob):
            filename = os.path.basename(path)
            b64ref, _ = filename.split('.gossip.md',maxsplit=1)
            uri = base64.b64decode(b64ref).decode('utf-8')
            permalink = GitPermalink.from_permalink(uri)
            if permalink.path != fpath:
                continue
            if permalink.commit not in commits:
                continue
            comments.append(GossipComment(path))
        return comments

    @pynvim.command("CommentsOn", nargs="*", range="", sync=False)
    def show_comments(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        comments = self.get_comments(fullpath)
        self.comments[fullpath] = comments
        for comment in comments:
            self.highlight_manager.mark_comment(comment)

    @pynvim.command("CommentsOff", nargs="*", range="", sync=False)
    def hide_comments(self, *args, **kwargs):
        self.highlight_manager.unmark()
