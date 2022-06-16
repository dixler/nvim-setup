#!/usr/bin/env python3
import os
import pynvim


def get_git_permalink(fullpath: str, nvim=None) -> str:
    d = os.path.dirname(fullpath)

    with os.popen(f"git -C '{d}' remote get-url origin") as p:
        base_url = p.read().strip()
        if 'github.com' not in base_url:
            raise Exception("Not a GitHub repository")
    #structure = "https://github.com/<org-name>/<repository>/tree/<commit-sha1>/<path/path/path>"

    with os.popen(f"git -C '{d}' rev-parse HEAD") as p:
        commit = p.read().strip()

        # TODO get file path using fullpath
        path = os.path.basename(fullpath)
        dirs = d.split(os.path.sep)
        while dirs:
            try:
                git_root_candidate = str(os.path.join(*dirs, '.git'))
                os.stat(git_root_candidate)

                permalink = f"{base_url}/tree/{commit}/{path}"
                return permalink
            except FileNotFoundError:
                path = os.path.join(dirs.pop(), path)
                dirs.pop()
    raise FileNotFoundError("unable to find .git")

            
@pynvim.plugin
class TestPlugin(object):

    def __init__(self, nvim):
        self.nvim = nvim

    @pynvim.command("Permalink", nargs="*", range="", sync=False)
    def testfunction(self, *args, **kwargs):
        fullpath = self.nvim.funcs.expand('%:p')
        self.nvim.command(f'echom "{get_git_permalink(fullpath)}"')
