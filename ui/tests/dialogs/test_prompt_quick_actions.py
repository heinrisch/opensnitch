"""Run with QT_QPA_PLATFORM=offscreen PYTHONPATH=ui python -m unittest
tests.dialogs.test_prompt_quick_actions.
"""
import threading
import re
import unittest
from unittest.mock import Mock

from PyQt6 import QtGui, QtTest, QtWidgets
import opensnitch.utils  # Initialize the application's shared imports first.
from opensnitch.config import Config
from opensnitch.dialogs.prompt.dialog import PromptDialog, ui_pb2
from opensnitch.dialogs.prompt import constants, utils


class QuickActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        # Use real widgets and rule serialization without starting network services.
        self.dialog = PromptDialog.__new__(PromptDialog)
        QtWidgets.QDialog.__init__(self.dialog)
        self.dialog.setupUi(self.dialog)
        self.dialog._setup_quick_actions()
        self.dialog._cfg = Mock()
        self.dialog._rules = Mock()
        self.dialog._rules.exists.return_value = True
        self.dialog.logger = Mock()
        self.dialog._peer = "test"
        self.dialog._done = threading.Event()
        self.dialog._ischeckAdvanceded = False
        self.dialog.stop_countdown = Mock()
        self.dialog._con = ui_pb2.Connection(
            process_path="/usr/bin/example", dst_host="api.example.com",
            dst_ip="192.0.2.1", dst_port=443)
        self.dialog.whatCombo.clear()
        self.dialog.whatCombo.addItem("Application", constants.FIELD_PROC_PATH)
        self.dialog.whatCombo.addItem("api.example.com", constants.FIELD_DST_HOST)

    def tearDown(self):
        self.dialog.deleteLater()

    def test_all_buttons_send_their_exact_scope_action_and_duration(self):
        buttons = self.dialog.findChildren(QtWidgets.QGroupBox)[0].findChildren(QtWidgets.QPushButton)
        self.assertEqual(len(buttons), 14)
        for row, (_, row_buttons, action, domain) in enumerate(self.dialog._quick_rows):
            for button in row_buttons:
                duration = {"Forever": "always", "1h": "1h"}[
                    button.property("durationLabel")]
                with self.subTest(row=row, duration=duration):
                    self.dialog._done.clear()
                    for checkbox in (self.dialog.checkDstIP, self.dialog.checkDstPort,
                                     self.dialog.checkUserID, self.dialog.checkSum):
                        checkbox.setChecked(True)
                    button.click()
                    rule = self.dialog._rule
                    self.assertTrue(self.dialog._done.is_set())
                    self.assertEqual(rule.duration, duration)
                    self.assertEqual(rule.action, "allow" if action == Config.ACTION_ALLOW_IDX else "deny")
                    self.assertEqual(rule.operator.type,
                                     Config.RULE_TYPE_REGEXP if domain == "parent" else Config.RULE_TYPE_SIMPLE)
                    self.assertEqual(rule.operator.operand,
                                     Config.OPERAND_DEST_HOST if domain else Config.OPERAND_PROCESS_PATH)
                    if domain == "parent":
                        for host in ("example.com", "bla.example.com", "deep.bla.example.com"):
                            self.assertIsNotNone(re.fullmatch(rule.operator.data, host))
                        for host in ("notexample.com", "example.com.evil.org", "exampleXcom"):
                            self.assertIsNone(re.fullmatch(rule.operator.data, host))
                    else:
                        self.assertEqual(rule.operator.data,
                                         "api.example.com" if domain else "/usr/bin/example")

    def test_allow_once_sends_a_one_time_allow_decision(self):
        self.dialog.allowOnceButton.click()
        self.assertTrue(self.dialog._done.is_set())
        self.assertEqual(self.dialog._rule.action, Config.ACTION_ALLOW)
        self.assertEqual(self.dialog._rule.duration, Config.DURATION_ONCE)

    def test_scoped_buttons_keep_their_existing_durations(self):
        for _, buttons, _, _ in self.dialog._quick_rows:
            self.assertEqual([button.property("durationLabel") for button in buttons],
                             ["Forever", "1h"])

    def test_block_once_sends_a_one_time_block_decision(self):
        self.dialog.blockOnceButton.click()
        self.assertTrue(self.dialog._done.is_set())
        self.assertEqual(self.dialog._rule.action, Config.ACTION_DENY)
        self.assertEqual(self.dialog._rule.duration, Config.DURATION_ONCE)

    def test_quick_buttons_grow_with_available_window_space(self):
        self.dialog.showEvent = Mock(return_value=None)
        self.dialog.show()
        self.app.processEvents()
        button = self.dialog._quick_rows[0][1][0]
        initial = button.size()
        self.dialog.resize(self.dialog.width() + 300, self.dialog.height() + 180)
        self.app.processEvents()
        self.assertGreater(button.width(), initial.width())
        self.assertGreaterEqual(button.height(), 40)

    def test_hidden_parent_row_leaves_no_large_gap_in_tall_window(self):
        self.dialog.showEvent = Mock(return_value=None)
        self.dialog._con.dst_host = "meta.com"
        self.dialog._update_quick_actions("curl", self.dialog._con)
        self.dialog.resize(1500, 1700)
        self.dialog.show()
        self.app.processEvents()
        visible = [buttons[0] for label, buttons, _, _ in self.dialog._quick_rows
                   if not label.isHidden()]
        for previous, current in zip(visible, visible[1:]):
            self.assertLess(current.y() - (previous.y() + previous.height()), 24)
        self.assertLess(visible[-1].geometry().bottom() - visible[0].y(), 400)

    def test_parent_domain_respects_public_and_private_suffixes(self):
        for host, parent in (("bla.example.com", "example.com"),
                             ("a.b.example.co.uk", "example.co.uk"),
                             ("api.alice.github.io", "alice.github.io"),
                             ("example.com", ""), ("co.uk", ""),
                             ("alice.github.io", ""), ("localhost", ""),
                             ("192.0.2.1", ""), ("::1", "")):
            with self.subTest(host=host):
                self.assertEqual(utils.get_parent_domain(host), parent)

    def test_parent_rows_show_the_domain_and_subdomain_scope(self):
        self.dialog._update_quick_actions("Example", self.dialog._con)
        label, buttons, _, _ = self.dialog._quick_rows[3]
        self.assertEqual(label.text(), "Allow example.com (including subdomains)")
        self.assertFalse(label.isHidden())
        self.assertIn("all its subdomains", buttons[0].toolTip())
        self.dialog._con.dst_host = "example.com"
        self.dialog._update_quick_actions("Example", self.dialog._con)
        self.assertTrue(label.isHidden())
        self.assertTrue(all(button.isHidden() for button in buttons))
        block_label, block_buttons, _, _ = self.dialog._quick_rows[4]
        self.assertEqual(block_label.text(), "Block example.com (including subdomains)")
        self.assertFalse(block_label.isHidden())
        self.dialog._done.clear()
        block_buttons[0].click()
        self.assertEqual(self.dialog._rule.action, "deny")
        self.assertIsNotNone(re.fullmatch(self.dialog._rule.operator.data, "api.example.com"))

    def test_missing_domain_does_not_send_a_rule(self):
        self.dialog.whatCombo.removeItem(1)
        self.dialog._update_quick_actions("Example", self.dialog._con)
        self.assertTrue(all(not button.isEnabled() for button in self.dialog._domain_buttons))
        self.dialog._on_quick_action(Config.ACTION_ALLOW_IDX, 8, True)
        self.assertFalse(self.dialog._done.is_set())

    def test_labels_follow_the_current_hostname(self):
        self.dialog._update_quick_actions("Example", self.dialog._con)
        label, buttons, _, _ = self.dialog._quick_rows[2]
        self.assertEqual(label.text(), "Allow api.example.com")
        self.assertEqual(buttons[0].accessibleName(), "Allow api.example.com · Forever")
        self.dialog._con.dst_host = "other.example.org"
        self.dialog._update_quick_actions("Example", self.dialog._con)
        self.assertEqual(label.text(), "Allow other.example.org")
        self.assertIn("other.example.org", buttons[0].toolTip())

    def test_duplicate_click_does_not_replace_decision(self):
        self.dialog._on_quick_action(Config.ACTION_ALLOW_IDX, 0, False)
        rule = self.dialog._rule
        self.dialog._on_quick_action(Config.ACTION_DROP_IDX, 8, True)
        self.assertIs(self.dialog._rule, rule)

    def test_letter_shortcuts_match_buttons_and_send_rules(self):
        self.dialog.showEvent = Mock(return_value=None)
        self.dialog.show()
        self.dialog.activateWindow()
        self.app.processEvents()
        shortcuts = self.dialog.findChildren(QtGui.QShortcut)
        self.assertEqual(len(shortcuts), 14)
        self.assertEqual(len({shortcut.key().toString() for shortcut in shortcuts}), 14)
        for shortcut in shortcuts:
            with self.subTest(key=shortcut.key().toString()):
                self.dialog._done.clear()
                self.dialog.show()
                self.dialog.activateWindow()
                self.app.processEvents()
                button = shortcut.parent()
                self.assertIn("[{}]".format(shortcut.key().toString().lower()), button.text())
                button.setFocus()
                QtTest.QTest.keyClick(button, shortcut.key()[0].key())
                self.assertTrue(self.dialog._done.is_set())
                self.assertEqual(self.dialog._rule.duration,
                                 {"Forever": "always", "1h": "1h", None: Config.DURATION_ONCE}[
                                     button.property("durationLabel")])

    def test_shortcut_does_not_submit_while_editing(self):
        self.dialog.showEvent = Mock(return_value=None)
        editor = QtWidgets.QLineEdit(self.dialog)
        self.dialog.show()
        editor.show()
        editor.setFocus()
        self.app.processEvents()
        button = self.dialog._quick_rows[0][1][0]
        self.dialog._activate_quick_shortcut(button)
        self.assertFalse(self.dialog._done.is_set())


if __name__ == "__main__":
    unittest.main()
