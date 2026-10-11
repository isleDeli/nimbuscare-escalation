#!/usr/bin/env python3
"""Run the agent's own entry point (`python3 -m agent`, as run.sh does) with the
network disabled and every file open recorded. Used by evals/score.py.

    python3 evals/sandbox_child.py <log.json> [agent arguments...]      (cwd = project root)

Before the agent is imported: socket.socket and socket.create_connection are
replaced with functions that record the attempt and raise; builtins.open and
io.open are wrapped; and a sys audit hook records every file open (this also
catches pathlib, os.open and imports), every socket/DNS/urllib event and every
attempt to start another process. The log is written when the agent exits.
"""
import builtins
import io
import json
import os
import runpy
import socket
import sys

log_path = os.path.abspath(sys.argv[1])
agent_args = sys.argv[2:]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = {"network_attempts": [], "process_attempts": [], "opens": []}


def _blocked(kind):
    def fn(*args, **kwargs):
        LOG["network_attempts"].append({"call": kind, "args": repr(args)[:200]})
        raise OSError("network disabled by evals/sandbox_child.py (%s)" % kind)
    return fn


class _BlockedSocket(socket.socket):
    def __init__(self, *args, **kwargs):
        _blocked("socket.socket")(*args, **kwargs)


socket.socket = _BlockedSocket
socket.create_connection = _blocked("socket.create_connection")

_real_open = builtins.open


def _note(path, mode, via):
    if isinstance(path, bytes):
        path = os.fsdecode(path)
    if isinstance(path, os.PathLike):
        path = os.fspath(path)
    if isinstance(path, str):
        LOG["opens"].append({"path": os.path.realpath(path), "mode": mode if isinstance(mode, str) else "r", "via": via})


def _open(file, mode="r", *args, **kwargs):
    _note(file, mode, "open")
    return _real_open(file, mode, *args, **kwargs)


builtins.open = _open
io.open = _open

NET_EVENTS = ("socket.connect", "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr",
              "socket.sendto", "socket.bind", "urllib.Request", "http.client.connect", "ftplib.connect",
              "smtplib.connect", "webbrowser.open")
PROC_EVENTS = ("subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork")
_active = [True]


def _hook(event, args):
    if not _active[0]:
        return
    if event == "open":
        _note(args[0], args[1], "audit")
    elif event in NET_EVENTS:
        LOG["network_attempts"].append({"call": event, "args": repr(args)[:200]})
    elif event in PROC_EVENTS:
        LOG["process_attempts"].append({"call": event, "args": repr(args)[:200]})


sys.addaudithook(_hook)

sys.path[0] = ROOT            # same import root as `cd <root>; python3 -m agent`
sys.argv = ["agent"] + agent_args
code = 0
try:
    runpy.run_module("agent", run_name="__main__", alter_sys=True)
except SystemExit as e:
    code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
finally:
    _active[0] = False
    sys.stdout.flush()
    with _real_open(log_path, "w", encoding="utf-8") as f:
        json.dump(LOG, f)
sys.exit(code)
