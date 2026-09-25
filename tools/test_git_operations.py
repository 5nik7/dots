"""Black-box tests: all Git mutations use test-owned directories and remotes."""
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLI = PROJECT / "bin/dots"


# Adapted from git-it tests; MIT notice: lib/dots/git/LICENSE.
class GitOperations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="git-it-test-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith("GIT_"):
                self.env.pop(key)
        self.env.update(
            HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / ".config"),
            GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
            GIT_AUTHOR_NAME="Git It Test", GIT_COMMITTER_NAME="Git It Test",
            GIT_AUTHOR_EMAIL="test@example.invalid", GIT_COMMITTER_EMAIL="test@example.invalid",
            GIT_TERMINAL_PROMPT="0", GIT_CONFIG_COUNT="3",
            DOTS_COLOR="never", DOTS_ICONS="never",
            GIT_CONFIG_KEY_0="protocol.file.allow", GIT_CONFIG_VALUE_0="always",
            GIT_CONFIG_KEY_1="commit.gpgSign", GIT_CONFIG_VALUE_1="false",
            GIT_CONFIG_KEY_2="core.hooksPath", GIT_CONFIG_VALUE_2=os.devnull,
        )
        self.config = self.base / "config"
        self.config.write_text('[dots-git]\nowner = github.com/5nik7\n')


    def run_cmd(self, args, cwd=None, ok=True, env=None, **kwargs):
        result = subprocess.run(args, cwd=cwd or self.base, env=env or self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=40, **kwargs)
        if ok:
            self.assertEqual(result.returncode, 0, f"{args}\n{result.stdout}\n{result.stderr}")
        return result


    def git(self, repo, *args, ok=True):
        return self.run_cmd(["git", "-C", str(repo), *args], ok=ok).stdout.rstrip("\n")


    def cli(self, repo, *args, ok=True, env=None):
        command, *options = args
        if command == 'publish':
            options += ['--config', str(self.config)]
        return self.run_cmd(['bash', str(CLI), 'git', command, '-C', str(repo), *options], ok=ok, env=env)

    def repo(self, name):
        repo = self.base / name
        repo.mkdir(parents=True)
        self.git(repo, "init", "-b", "main")
        (repo / "file").write_text("initial\n")
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "initial")
        return repo


    def remote_repo(self, name):
        source = self.repo(name + "-source")
        bare = self.base / (name + ".git")
        self.run_cmd(["git", "clone", "--bare", str(source), str(bare)])
        clone = self.base / name
        self.run_cmd(["git", "clone", str(bare), str(clone)])
        return source, bare, clone


    def advance(self, source, bare, content="updated\n"):
        (source / "file").write_text(content)
        self.git(source, "add", "file")
        self.git(source, "commit", "-m", "advance")
        self.git(source, "push", str(bare), "main")
        return self.git(source, "rev-parse", "HEAD")


    def sub(self, parent, source, path):
        self.git(parent, "submodule", "add", "--", str(source), path)
        self.git(parent, "commit", "-am", "add submodule")
        return parent / path


    def owned_remote(self, repo, bare):
        # A test-only SSH transport runs upload/receive-pack against local bare
        # repositories. No GitHub access or URL-rewrite ownership bypass.
        ssh = self.base / "ssh-test"
        ssh.write_text("#!" + shutil.which("bash") + "\n"
                       "[[ $1 != -G ]] || exit 1\n"
                       "exec bash -c \"${!#}\"\n")
        ssh.chmod(0o700)
        self.env["GIT_SSH_COMMAND"] = str(ssh)
        self.env["GIT_SSH_VARIANT"] = "ssh"
        url = "ssh://git@example.invalid" + str(bare)
        namespace = str(bare.parent).lstrip("/")
        self.config.write_text(f'[dots-git]\nowner = example.invalid/{namespace}\n')
        self.git(repo, "remote", "set-url", "origin", url)


    def test_sync_uninitialized_literal_special_path(self):
        _, child_bare, _ = self.remote_repo("special-child")
        source, bare, top = self.remote_repo("special-top")
        path = 'mods/-literal[1] space\tline\nend'
        self.git(source, "submodule", "add", "--name", "special", "--", str(child_bare), path)
        self.git(source, "commit", "-am", "add specially named path")
        self.git(source, "push", str(bare), "main")
        self.cli(top, "sync", "--init")
        self.assertTrue((top / path / "file").is_file())
        data = json.loads(self.cli(top / path, "status", "--json").stdout)
        self.assertEqual(data["repositories"][0]["path"], str(top / path))


    def test_sync_fast_forward_and_dry_run(self):
        source, bare, repo = self.remote_repo("sync")
        before = self.git(repo, "rev-parse", "HEAD")
        after = self.advance(source, bare)
        refs = self.git(repo, "show-ref")
        preview = json.loads(self.cli(repo, "sync", "--dry-run", "--json").stdout)
        self.assertTrue(preview["dry_run"])
        self.assertEqual(self.git(repo, "show-ref"), refs)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
        self.cli(repo, "sync")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), after)


    def test_sync_local_changes_preserved(self):
        source, bare, repo = self.remote_repo("dirty")
        self.advance(source, bare)
        (repo / "file").write_text("local edit\n")
        before = self.git(repo, "rev-parse", "HEAD")
        result = self.cli(repo, "sync", ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual((repo / "file").read_text(), "local edit\n")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
        self.assertFalse((repo / ".git/git-it.lock").exists())


    def test_sync_ahead_retained_and_divergence_refused(self):
        source, bare, repo = self.remote_repo("diverged")
        (repo / "local").write_text("local\n")
        self.git(repo, "add", "local"); self.git(repo, "commit", "-m", "local")
        head = self.git(repo, "rev-parse", "HEAD")
        self.cli(repo, "sync")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.advance(source, bare)
        self.assertEqual(self.cli(repo, "sync", ok=False).returncode, 1)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)


    def test_sync_missing_upstream_detached_and_lock(self):
        repo = self.repo("no-upstream")
        self.assertEqual(self.cli(repo, "sync", ok=False).returncode, 1)
        self.git(repo, "checkout", "--detach")
        self.assertEqual(self.cli(repo, "sync", ok=False).returncode, 1)
        (repo / ".git/git-it.lock").mkdir()
        self.assertEqual(self.cli(repo, "sync", ok=False).returncode, 1)
        self.assertTrue((repo / ".git/git-it.lock").is_dir())


    def make_sync_tree(self):
        leaf_source, leaf_bare, _ = self.remote_repo("leaf")
        mid_source, mid_bare, _ = self.remote_repo("mid")
        self.sub(mid_source, leaf_bare, "leaf")
        self.git(mid_source, "push", str(mid_bare), "main")
        top_source, top_bare, top = self.remote_repo("top")
        self.sub(top_source, mid_bare, "middle")
        self.sub(top_source, leaf_bare, "sibling")
        self.git(top_source, "push", str(top_bare), "main")
        return top_source, top_bare, top, mid_source, mid_bare, leaf_source, leaf_bare


    def test_sync_initializes_three_levels_and_keeps_pins(self):
        _, _, top, _, _, leaf_source, leaf_bare = self.make_sync_tree()
        self.cli(top, "sync", "--init")
        nested = top / "middle/leaf"
        before = self.git(nested, "rev-parse", "HEAD")
        self.advance(leaf_source, leaf_bare)
        self.cli(top, "sync", "--init")
        self.assertEqual(self.git(nested, "rev-parse", "HEAD"), before)
        self.assertEqual(self.git(top, "status", "--porcelain"), "")


    def test_sync_remote_updates_and_continues_safe_sibling(self):
        _, _, top, _, _, leaf_source, leaf_bare = self.make_sync_tree()
        self.cli(top, "sync", "--init")
        self.git(top, "config", "submodule.middle.branch", "main")
        self.git(top, "config", "submodule.sibling.branch", "main")
        (top / "middle/file").write_text("local edit\n")
        new = self.advance(leaf_source, leaf_bare)
        result = self.cli(top, "sync", "--remote", "--json", ok=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.git(top / "sibling", "rev-parse", "HEAD"), new)
        self.assertEqual((top / "middle/file").read_text(), "local edit\n")
        self.assertEqual(self.git(top, "diff", "--cached", "--name-only"), "")


    def test_publish_staged_only_and_existing_commits(self):
        _, bare, repo = self.remote_repo("publish")
        self.owned_remote(repo, bare)
        (repo / "staged").write_text("selected\n")
        (repo / "untracked").write_text("leave me\n")
        self.git(repo, "add", "staged")
        preview = self.cli(repo, "publish", "--dry-run")
        self.assertIn("selected", preview.stdout)
        self.assertNotIn("?? untracked", preview.stdout)
        self.cli(repo, "publish", "--yes", "-m", "selected commit")
        self.assertEqual(self.git(repo, "log", "-1", "--format=%s"), "selected commit")
        self.assertEqual(self.git(bare, "rev-parse", "main"), self.git(repo, "rev-parse", "HEAD"))
        self.assertEqual(self.git(repo, "status", "--porcelain"), "?? untracked")
        self.git(repo, "add", "untracked"); self.git(repo, "commit", "-m", "already committed")
        self.cli(repo, "publish", "--yes")
        self.assertEqual(self.git(bare, "rev-parse", "main"), self.git(repo, "rev-parse", "HEAD"))


    def test_publish_all_and_ownership_block(self):
        _, bare, repo = self.remote_repo("all")
        self.owned_remote(repo, bare)
        (repo / "new file").write_text("new\n")
        before = self.git(repo, "rev-parse", "HEAD")
        self.config.write_text('[dots-git]\nowner = other.invalid/other\n')
        self.assertEqual(self.cli(repo, "publish", "--all", "--yes", ok=False).returncode, 1)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
        self.owned_remote(repo, bare)
        self.cli(repo, "publish", "--all", "--yes")
        self.assertEqual(self.git(repo, "status", "--porcelain"), "")


    def test_publish_requires_confirmation_and_no_dry_run_writes(self):
        _, bare, repo = self.remote_repo("confirm")
        self.owned_remote(repo, bare)
        (repo / "new").write_text("new\n"); self.git(repo, "add", "new")
        before = self.git(repo, "show-ref")
        index = (repo / ".git/index").read_bytes()
        self.cli(repo, "publish", "--dry-run")
        self.assertEqual((repo / ".git/index").read_bytes(), index)
        self.assertEqual(self.git(repo, "show-ref"), before)
        self.assertEqual(self.cli(repo, "publish", ok=False).returncode, 2)


    def test_publish_push_failure_retains_commit(self):
        _, bare, repo = self.remote_repo("reject")
        self.owned_remote(repo, bare)
        # Receive-pack hook policy is test-owned and configured only on this bare.
        hookdir = self.base / "hooks"; hookdir.mkdir()
        hook = hookdir / "pre-receive"
        hook.write_text("#!" + shutil.which("bash") + "\nexit 1\n"); hook.chmod(0o700)
        # Env core.hooksPath would override repo config, so replace it for this test.
        self.env["GIT_CONFIG_VALUE_2"] = str(hookdir)
        self.git(bare, "config", "core.hooksPath", str(hookdir))
        before = self.git(bare, "rev-parse", "main")
        (repo / "new").write_text("new\n"); self.git(repo, "add", "new")
        self.assertEqual(self.cli(repo, "publish", "--yes", ok=False).returncode, 1)
        self.assertNotEqual(self.git(repo, "rev-parse", "HEAD"), before)
        self.assertEqual(self.git(bare, "rev-parse", "main"), before)


    def publish_tree(self):
        leaf_source, leaf_bare, _ = self.remote_repo("pub-leaf")
        mid_source, mid_bare, _ = self.remote_repo("pub-mid")
        self.sub(mid_source, leaf_bare, "leaf")
        self.git(mid_source, "push", str(mid_bare), "main")
        top_source, top_bare, top = self.remote_repo("pub-top")
        self.sub(top_source, mid_bare, "middle")
        self.git(top_source, "push", str(top_bare), "main")
        self.cli(top, "sync", "--init")
        mid, leaf = top / "middle", top / "middle/leaf"
        for repo, bare in ((top, top_bare), (mid, mid_bare), (leaf, leaf_bare)):
            self.git(repo, "checkout", "main")
            self.owned_remote(repo, bare)
        return top, mid, leaf, top_bare, mid_bare, leaf_bare


    def test_publish_three_levels_child_before_parent(self):
        top, mid, leaf, top_bare, mid_bare, leaf_bare = self.publish_tree()
        (leaf / "change").write_text("leaf change\n"); self.git(leaf, "add", "change")
        result = self.cli(top, "publish", "--yes", "--json", "-m", "recursive")
        events = json.loads(result.stdout)["events"]
        self.assertEqual([e["path"] for e in events if e["status"] == "published"],
                         [str(leaf), str(mid), str(top)])
        for repo, bare in ((top, top_bare), (mid, mid_bare), (leaf, leaf_bare)):
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), self.git(bare, "rev-parse", "main"))
        self.assertEqual(self.git(top, "status", "--porcelain"), "")


    def test_publish_detached_changed_child_blocks_ancestors(self):
        top, _, leaf, top_bare, _, _ = self.publish_tree()
        self.git(leaf, "checkout", "--detach")
        (leaf / "change").write_text("leaf change\n"); self.git(leaf, "add", "change")
        before = self.git(top_bare, "rev-parse", "main")
        result = self.cli(top, "publish", "--yes", "--json", ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["complete"])
        self.assertEqual(self.git(top_bare, "rev-parse", "main"), before)


    def test_publish_rejected_child_allows_independent_sibling(self):
        top, mid, leaf, top_bare, mid_bare, leaf_bare = self.publish_tree()
        _, sibling_bare, _ = self.remote_repo("pub-sibling")
        sibling = self.sub(top, sibling_bare, "sibling")
        self.git(top, "push", str(top_bare), "main")
        self.owned_remote(sibling, sibling_bare)
        hookdir = self.base / "reject-leaf-hooks"; hookdir.mkdir()
        hook = hookdir / "pre-receive"
        hook.write_text("#!" + shutil.which("bash") + "\nexit 1\n"); hook.chmod(0o700)
        self.git(leaf_bare, "config", "core.hooksPath", str(hookdir))
        before_top = self.git(top_bare, "rev-parse", "main")
        before_mid = self.git(mid_bare, "rev-parse", "main")
        before_sibling = self.git(sibling_bare, "rev-parse", "main")
        for repo in (leaf, sibling):
            (repo / "change").write_text("selected\n"); self.git(repo, "add", "change")
        result = self.cli(top, "publish", "--yes", "--json", ok=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.git(top_bare, "rev-parse", "main"), before_top)
        self.assertEqual(self.git(mid_bare, "rev-parse", "main"), before_mid)
        self.assertNotEqual(self.git(sibling_bare, "rev-parse", "main"), before_sibling)
        events = json.loads(result.stdout)["events"]
        self.assertTrue(any(e["path"] == str(sibling) and e["status"] == "published" for e in events))


    def test_publish_preserves_deliberately_staged_child_pointer(self):
        top, mid, leaf, _, _, leaf_bare = self.publish_tree()
        (leaf / "second").write_text("second\n")
        self.git(leaf, "add", "second"); self.git(leaf, "commit", "-m", "second")
        self.git(leaf, "push", str(leaf_bare), "main")
        self.git(mid, "add", "leaf")
        staged = self.git(mid, "ls-files", "--stage", "leaf")
        (leaf / "third").write_text("third\n"); self.git(leaf, "add", "third")
        result = self.cli(top, "publish", "--yes", ok=False)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(self.git(mid, "ls-files", "--stage", "leaf"), staged)


    def test_sync_preserves_ignored_file_collision(self):
        source, bare, repo = self.remote_repo("ignored")
        (repo / ".git/info/exclude").write_text("collision\n")
        (repo / "collision").write_text("precious ignored contents\n")
        (source / "collision").write_text("upstream\n")
        self.git(source, "add", "collision"); self.git(source, "commit", "-m", "new tracked path")
        self.git(source, "push", str(bare), "main")
        before = self.git(repo, "rev-parse", "HEAD")
        self.assertEqual(self.cli(repo, "sync", ok=False).returncode, 1)
        self.assertEqual((repo / "collision").read_text(), "precious ignored contents\n")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)


    def test_sync_preserves_unpublished_submodule_commit(self):
        _, _, top, _, _, _, _ = self.make_sync_tree()
        self.cli(top, "sync", "--init")
        child = top / "middle"
        (child / "local").write_text("unpublished\n")
        self.git(child, "add", "local"); self.git(child, "commit", "-m", "unpublished")
        before = self.git(child, "rev-parse", "HEAD")
        self.assertEqual(self.cli(top, "sync", ok=False).returncode, 1)
        self.assertEqual(self.git(child, "rev-parse", "HEAD"), before)


    def test_sync_refuses_submodule_removal(self):
        source, bare, top, _, _, _, _ = self.make_sync_tree()
        self.cli(top, "sync", "--init")
        self.git(source, "rm", "-f", "sibling"); self.git(source, "commit", "-m", "remove")
        self.git(source, "push", str(bare), "main")
        before = self.git(top, "rev-parse", "HEAD")
        self.assertEqual(self.cli(top, "sync", ok=False).returncode, 1)
        self.assertEqual(self.git(top, "rev-parse", "HEAD"), before)
        self.assertTrue((top / "sibling/file").is_file())


    def test_publish_checks_push_url_and_conflicting_configuration(self):
        _, bare, repo = self.remote_repo("push-config")
        self.owned_remote(repo, bare)
        (repo / "new").write_text("new\n"); self.git(repo, "add", "new")
        before = self.git(repo, "rev-parse", "HEAD")
        self.git(repo, "remote", "set-url", "--push", "origin", "https://not-owned.invalid/owner/repo")
        self.assertEqual(self.cli(repo, "publish", "--yes", ok=False).returncode, 1)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
        self.git(repo, "config", "--unset-all", "remote.origin.pushurl")
        self.git(repo, "config", "remote.origin.push", "HEAD:refs/heads/surprise")
        self.assertEqual(self.cli(repo, "publish", "--yes", ok=False).returncode, 1)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)


    def test_status_compact_json_and_default_root(self):
        root = self.repo('root ü')
        child = self.repo('child')
        self.sub(root, child, 'config/nvim')
        (root/'new file').write_text('new')
        before = (root/'.git/index').read_bytes()
        result = self.cli(root, 'status')
        self.assertNotIn(str(root), result.stdout)
        self.assertIn('new file', result.stdout)
        self.assertIn('nvim', result.stdout)
        self.assertIn(str(root), self.cli(root, 'status', '--full-paths').stdout)
        data = json.loads(self.cli(root, 'status', '--json', env=dict(self.env,DOTS_COLOR='always')).stdout)
        self.assertEqual(len(data['repositories']), 2)
        self.assertEqual(data['repositories'][0]['files'][0]['path'], 'new file')
        self.assertEqual((root/'.git/index').read_bytes(), before)
        default = self.run_cmd(['bash',str(CLI),'--command-dir',str(PROJECT/'bin'),'git','status','--json'], env=dict(self.env,DOTS=str(root)))
        self.assertEqual(json.loads(default.stdout)['repositories'][0]['path'],str(root))

    def test_sync_missing_requires_init(self):
        _, _, top, _, _, _, _ = self.make_sync_tree()
        result=self.cli(top,'sync','--json',ok=False)
        self.assertEqual(result.returncode,1)
        self.assertFalse((top/'middle/.git').exists())
        self.cli(top,'sync','--init')
        self.assertTrue((top/'middle/.git').exists())

    def test_staged_pointer_with_all(self):
        top, mid, leaf, _, _, leaf_bare = self.publish_tree()
        (leaf/'second').write_text('second')
        self.git(leaf,'add','second'); self.git(leaf,'commit','-m','second')
        self.git(leaf,'push',str(leaf_bare),'main')
        self.git(mid,'add','leaf')
        staged=self.git(mid,'ls-files','--stage','leaf')
        (leaf/'third').write_text('third')
        result=self.cli(top,'publish','--all','--yes',ok=False)
        self.assertEqual(result.returncode,1)
        self.assertEqual(self.git(mid,'ls-files','--stage','leaf'),staged)

    def test_publish_json_confirmation_shows_preview_and_cancel_preserves(self):
        _, bare, repo = self.remote_repo("cancel")
        self.owned_remote(repo, bare)
        (repo / "selected-file").write_text("selected\n"); self.git(repo, "add", "selected-file")
        before = self.git(repo, "rev-parse", "HEAD")
        master, slave = pty.openpty()
        try:
            proc = subprocess.Popen(["bash", str(CLI), "git", "publish", "--config", str(self.config), "-C", str(repo), "--json"], env=self.env, stdin=slave,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            preview = b""
            deadline = time.monotonic() + 20
            while b"[y/N]" not in preview and time.monotonic() < deadline:
                if select.select([proc.stderr], [], [], 0.1)[0]:
                    chunk = os.read(proc.stderr.fileno(), 4096)
                    if not chunk:
                        break
                    preview += chunk
            self.assertIn(b"selected-file", preview)
            self.assertIn(b"[y/N]", preview)
            self.assertNotIn(b"\n  " + str(repo).encode() + b"\n", preview)
            os.write(master, b"n\n")
            stdout, stderr = proc.communicate(timeout=10)
            self.assertEqual(proc.returncode, 0, preview + stderr)
            self.assertTrue(any(e["status"] == "cancelled" for e in json.loads(stdout)["events"]))
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
            self.assertFalse((repo / ".git/git-it.lock").exists())
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=10)
            os.close(master); os.close(slave)


    def test_sync_interruption_releases_owned_lock(self):
        _, _, repo = self.remote_repo("interrupt")
        wrappers = self.base / "wrappers"; wrappers.mkdir()
        marker = self.base / "fetch-started"
        script = wrappers / "git"
        script.write_text("#!" + shutil.which("bash") + "\n"
                          'for arg in "$@"; do\n'
                          '  if [[ $arg == fetch ]]; then : > "$TEST_MARKER"; sleep 30; exit 1; fi\n'
                          'done\nexec "$REAL_GIT" "$@"\n')
        script.chmod(0o700)
        env = self.env.copy()
        env.update(PATH=str(wrappers) + os.pathsep + env["PATH"],
                   TEST_MARKER=str(marker), REAL_GIT=shutil.which("git"))
        before = self.git(repo, "rev-parse", "HEAD")
        proc = subprocess.Popen(["bash", str(CLI), "git", "sync", "-C", str(repo)],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            os.killpg(proc.pid, signal.SIGTERM)
            proc.communicate(timeout=10)
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse((repo / ".git/git-it.lock").exists())
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), before)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL); proc.communicate()


    def test_status_presentation_and_duplicate_names(self):
        repo=self.repo('presentation')
        child=self.repo('dependency')
        self.sub(repo,child,'one/shared')
        self.sub(repo,child,'two/shared')
        for width in ('40','80','120'):
            result=self.cli(repo,'status',env=dict(self.env,DOTS_COLOR='always',COLUMNS=width))
            self.assertIn('\x1b[',result.stdout)
            self.assertIn('one/shared',result.stdout)
            self.assertIn('two/shared',result.stdout)
            self.assertNotIn(str(repo),result.stdout)
        for env in [dict(self.env,DOTS_COLOR='auto',NO_COLOR='1',TERM='xterm-256color'),dict(self.env,DOTS_COLOR='auto',TERM='dumb')]:
            master,slave=pty.openpty()
            try:
                proc=subprocess.Popen(['bash',str(CLI),'git','status','-C',str(repo)],env=env,stdout=slave,stderr=subprocess.PIPE)
                proc.communicate(timeout=10)
                self.assertEqual(proc.returncode,0)
                self.assertNotIn(b'\x1b[',os.read(master,65536))
            finally:
                os.close(master);os.close(slave)

if __name__ == '__main__': unittest.main()
