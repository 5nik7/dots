#!/usr/bin/env python3
"""Run the portable Git safety cases against the native Python controller."""
import os
import unittest
import test_git_operations

os.environ['DOTS_TEST_GIT_FRONTEND'] = 'native'
# These three tests explicitly launch the Bash frontend and require a POSIX PTY.
# Native terminal cancellation and visual acceptance have separate Windows gates.
EXCLUDED = {'test_publish_json_confirmation_shows_preview_and_cancel_preserves',
            'test_sync_interruption_releases_owned_lock',
            'test_status_presentation_and_duplicate_names'}

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite(test_git_operations.GitOperations(name)
                              for name in loader.getTestCaseNames(test_git_operations.GitOperations)
                              if name not in EXCLUDED)
    raise SystemExit(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
