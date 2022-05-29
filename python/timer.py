#!/usr/bin/env python3
import tempfile
from datetime import datetime, timedelta
from typing import List
from blame import BlameLine
from pynvim import attach
import time
import os
import sys

path = sys.argv[1] if len(sys.argv) >= 2 else '/tmp/nvim'

nvim = attach('socket', path=path)

def pretty_date(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    from datetime import datetime
    now = datetime.now()
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = 0
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365 * 2:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"

def calculate_line_annotations():
    retval = {}
    blames = repo.blame_incremental('HEAD', fullpath)
    for blame in blames:
        commit: git.Commit = blame.commit
        lines = blame.linenos
        for line in lines:
            message_trunc = commit.message.split('\n')[0]
            opts = {
                    #'end_line': line,
                'virt_text': [
                    [
                       f'| {line} {commit.author.name}({pretty_date(commit.authored_datetime.replace(tzinfo=None))}): {commit.message}',
                       'PMenuSel']
                ],
                'virt_text_pos': 'overlay',
                #'virt_text_win_col': 20,
            }
            retval[line] = (lines, opts)
    return retval

def get_buffer_blame(nvim, bnr, memo={}) -> List[BlameLine]:
    text = '\n'.join(bnr[:])
    if text not in memo:
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

ns_id = nvim.api.create_namespace('demo')

try:
    blame_lines = None
    marks = {}
    while True:
        bnr = nvim.current.buffer
        new_blame_lines = get_buffer_blame(nvim, bnr)
        if new_blame_lines == blame_lines:
            print('sleeping')
            time.sleep(0.02)
            continue
        blame_lines = new_blame_lines

        for blame in blame_lines:
            hl_id = f"DiffGutter_{blame.commit}"
            nvim.command(f"highlight {hl_id} guibg=#{blame.commit[:6]}")
            sign_id = f"DiffGutterSign_{blame.commit}"
            sign_text = blame.email.split('@')[0][:2]
            nvim.command(f"sign define {sign_id} texthl={hl_id} numhl={hl_id} text={sign_text}")
            opts = {
                'end_line': blame.lineno,
                'virt_text': [
                    [
                       f'| {blame.commit} {blame.email}',
                       hl_id,
                    ]
                ],
                'virt_text_pos': 'overlay',
                #'virt_text_win_col': 20,
            }
            lineno = blame.lineno
            nvim.command(f'sign place {lineno} line={lineno} name={sign_id}')
            if blame.lineno-1 in marks:
                nvim.api.buf_del_extmark(bnr, ns_id, marks[blame.lineno-1])

            #marks[blame.lineno-1] = nvim.api.buf_set_extmark(bnr, ns_id, blame.lineno-1, -1, opts)

        time.sleep(0.02)
except Exception as e:
    print(e)
    print('cleaning up')
    for mark in marks:
        nvim.api.buf_del_extmark(bnr, ns_id, mark)
exit()
try:
    while True:
        cur_line = nvim.windows[0].cursor[0]
        lines, opts = annotations[cur_line]

        if lines == cur_range:
            continue
        cur_range = lines

        for mark in marks:
            nvim.api.buf_del_extmark(bnr, ns_id, mark)
        
        for line in cur_range:
            mark_id = nvim.api.buf_set_extmark(bnr, ns_id, line-1, -1, opts)
            marks.append(mark_id)

        time.sleep(0.25)
        continue
except KeyboardInterrupt:
    for mark in marks:
        nvim.api.buf_del_extmark(bnr, ns_id, mark)
exit()
try:
    for i, line in enumerate(nvim.current.buffer):
        if i == nvim.current.window.cursor[0] - 1 and nvim.current.buffer.line_count():
            continue

        split = line.split(':')
        if not split or len(split) != 3:
            continue
        timer, mins, secs = split
        mins, secs = int(mins), int(secs)
        secs += mins * 60
        if secs == 0:
            continue
        secs += -1

        nvim.current.buffer[i] = f"{timer}: {secs//60:02}:{secs%60:02}"
        if secs == 0:
            os.popen(f'notify-send "{timer}" "HEY BRO YOUR TIMER FINISHED"') # TODO sanitize
except Exception as e:
    print(e)
while True:
    bnr = nvim.current.buffer
    
    fullpath = nvim.funcs.expand('%:p')
    ns_id = nvim.api.create_namespace('demo')

    d = os.path.dirname(fullpath)
    repo = Repo(d, search_parent_directories=True)
    blames = repo.blame_incremental('master', fullpath)
    for blame in blames:
        commit: git.Commit = blame.commit
        lines = blame.orig_linenos
        print(lines)
        longest_line = max(lines)
        for line in lines:
            print(commit.author, pretty_date(commit.authored_datetime.replace(tzinfo=None)))
            message_trunc = commit.message.split('\n')[0]
            opts = {
                'end_line': line,
                'id': line,
                'virt_text': [
                    [
                       f'| {line} {commit.author.name}({pretty_date(commit.authored_datetime.replace(tzinfo=None))}): {commit.message}',
                       'PMenuSel']
                ],
                'virt_text_pos': 'overlay',
                #'virt_text_win_col': 20,
            }

            mark_id = nvim.api.buf_set_extmark(bnr, ns_id, line-1, -1, opts)
while True:
    bnr = nvim.current.buffer
    
    fullpath = nvim.funcs.expand('%:p')
    ns_id = nvim.api.create_namespace('demo')

    d = os.path.dirname(fullpath)
    repo = Repo(d, search_parent_directories=True)
    blames = repo.blame('master', fullpath)
    for commit, lines in blames:
        print(commit, lines)
        commit: git.Commit

        for line in lines:
            message_trunc = commit.message.split('\n')[0]
            opts = {
                'end_line': line,
                'id': line,
                'virt_text': [
                    [
                       f'| {line} {commit.author.name}({pretty_date(commit.authored_datetime.replace(tzinfo=None))}): {commit.message}',
                       'PMenuSel']
                ],
                'virt_text_pos': 'overlay',
                #'virt_text_win_col': 20,
            }

            mark_id = nvim.api.buf_set_extmark(bnr, ns_id, line-1, -1, opts)
