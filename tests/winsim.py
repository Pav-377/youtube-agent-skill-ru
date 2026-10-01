"""winsim.py - run a script as it runs on a Russian Windows, on any OS.

    python tests/winsim.py path/to/script.py args...

Two things differ there from a developer machine:
  - open() without an encoding reads cp1251 (the ANSI code page), so a UTF-8 file turns to mojibake;
  - stdout redirected to a file or a pipe is cp1251 too, so an emoji or an arrow raises
    UnicodeEncodeError.
This reproduces both, strictly, which a CI runner (cp1252 or UTF-8) does not do on its own.
"""
import builtins, io, os, runpy, sys

script, args = sys.argv[1], sys.argv[2:]
_open = builtins.open


def open_cp1251(file, mode="r", buffering=-1, encoding=None, *rest, **kw):
    if "b" not in mode and encoding is None:
        encoding = "cp1251"
    return _open(file, mode, buffering, encoding, *rest, **kw)


builtins.open = open_cp1251
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="cp1251", line_buffering=True)
os.environ.pop("PYTHONIOENCODING", None)
sys.argv = [script] + args
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__main__")
