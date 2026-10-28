import io
import os
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
from test_blastoff import Harness, core

class Terminal(io.StringIO):
    def isatty(self): return True

class ReleaseHarness(Harness):
    def tree(self):
        return {str(p.relative_to(self.home)):(p.lstat().st_mode,p.lstat().st_mtime_ns,os.readlink(p) if p.is_symlink() else None if p.is_dir() else p.read_bytes())
                for p in self.home.rglob('*')}
    def run_tty(self, argv, answers='', callback=None):
        class Input(Terminal):
            def readline(this,*args):
                if callback: callback()
                return super().readline(*args)
        out,err=Terminal(),Terminal()
        with patch.dict(os.environ,self.env,clear=True),patch('sys.stdin',Input(answers)),redirect_stdout(out),redirect_stderr(err):
            try: code=core.run(argv)
            except core.Failure as e: code=e.code;err.write(str(e))
        return code,out.getvalue(),err.getvalue()
