#!/usr/bin/env python3
"""Published component controls preserve native activity and singleton behavior."""
import unittest
from unittest.mock import patch
import test_codex_status as activity
import test_config_layout as configured


class PublishedActivity(activity.Native):
    def setUp(self):
        with patch.object(activity.status,'TmuxStatus',configured.GeneratedStatus):
            super().setUp()


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(PublishedActivity(name) for name in (
        'test_native_colors_titles_warnings_widths_and_failure',
        'test_native_singleton_markers_names_and_visibility',
        'test_native_session_markers_widths_transitions_and_failure'))


if __name__=='__main__':unittest.main()
