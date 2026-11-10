import concurrent.futures
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from tickets import PROJECT_ROOT, TicketError, TicketStore, main


class TicketTests(unittest.TestCase):
    def setUp(self):
        test_root = PROJECT_ROOT / "test" / "fixtures" / "runtime" / "tickets"
        test_root.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="tickets-", dir=test_root)
        self.root = Path(self.temporary.name)
        self.store = TicketStore(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def create(self):
        return self.store.create("BUG-001", "記録を保つ", "年を越えて履歴を確認する。", ["旧年度の記録を表示できる"], kind="bug")

    def test_done_requires_checked_acceptance_and_evidence(self):
        self.create()
        with self.assertRaises(TicketError):
            self.store.update("BUG-001", "status", status="done")
        self.store.update("BUG-001", "check", index=1, checked=True)
        with self.assertRaises(TicketError):
            self.store.update("BUG-001", "status", status="done")
        self.store.update("BUG-001", "evidence", text="固定時計で旧年度の記録が保持されることを確認。")
        closed = self.store.update("BUG-001", "status", status="done")
        self.assertEqual(closed["status"], "done")
        with self.assertRaises(TicketError):
            self.store.update("BUG-001", "check", index=1, checked=False)
        with self.assertRaises(TicketError):
            self.store.update("BUG-001", "status", status="in_progress")
        reopened = self.store.update("BUG-001", "status", "追加条件の確認", status="in_progress")
        self.assertEqual(reopened["status"], "in_progress")

    def test_append_only_and_snapshot_recovers_after_interrupted_write(self):
        self.create()
        prefix = self.store.ledger.read_bytes()
        old_snapshot = self.store.snapshot.read_bytes()
        original_atomic_write = self.store.atomic_write

        def interrupted(destination, content):
            if destination == self.store.snapshot:
                raise OSError("simulated interruption after durable event")
            return original_atomic_write(destination, content)

        with patch.object(self.store, "atomic_write", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.store.update("BUG-001", "comment", text="障害前に受理された変更")
        self.assertEqual(self.store.snapshot.read_bytes(), old_snapshot)
        self.assertTrue(self.store.ledger.read_bytes().startswith(prefix))
        recovered, events = self.store.read()
        self.assertEqual(len(events), 2)
        self.assertEqual(recovered["tickets"][0]["comments"][0]["text"], "障害前に受理された変更")
        self.assertEqual(json.loads(self.store.snapshot.read_text(encoding="utf-8")), recovered)
        self.assertTrue(self.store.ledger.read_bytes().startswith(prefix))

    def test_acceptance_cli_preserves_history_and_requires_rechecking(self):
        self.store.create("CP53", "日帰り距離", "最新指定へ改訂する。", ["片道50〜100km・120分以内", "距離の出典を表示する"])
        self.store.update("CP53", "status", status="in_progress")
        for index in (1, 2):
            self.store.update("CP53", "check", index=index, checked=True)
        self.store.update("CP53", "evidence", text="変更前の条件を確認した記録。")
        before, old_events = self.store.read()
        prefix = self.store.ledger.read_bytes()
        note = "利用者の最新指定で距離と時間条件を改訂"
        with patch("tickets.TicketStore", return_value=self.store), redirect_stdout(io.StringIO()):
            result = main(["acceptance", "CP53", "1", "--text", "片道20〜40km・固定時間上限なし", "--note", note])
        self.assertEqual(result, 0)
        state, events = self.store.read()
        ticket = state["tickets"][0]
        self.assertEqual(ticket["acceptance"], [{"text": "片道20〜40km・固定時間上限なし", "checked": False}, {"text": "距離の出典を表示する", "checked": True}])
        self.assertEqual(ticket["status"], "in_progress")
        self.assertEqual(ticket["evidence"], before["tickets"][0]["evidence"])
        self.assertTrue(self.store.ledger.read_bytes().startswith(prefix))
        self.assertEqual(events[:-1], old_events)
        self.assertEqual(events[-1]["action"], "acceptance")
        self.assertEqual(events[-1]["note"], note)
        self.assertEqual(ticket["revision"], before["tickets"][0]["revision"] + 1)
        with self.assertRaises(TicketError):
            self.store.update("CP53", "status", status="done")

    def test_acceptance_revision_reopens_completed_ticket_for_review(self):
        self.create()
        self.store.update("BUG-001", "check", index=1, checked=True)
        self.store.update("BUG-001", "evidence", text="旧条件で確認済み。")
        self.store.update("BUG-001", "status", status="done")
        prefix = self.store.ledger.read_bytes()
        amended = self.store.update("BUG-001", "acceptance", "新しい要件を確認するため", index=1, text="新条件で過去記録を表示できる")
        self.assertEqual(amended["status"], "review")
        self.assertFalse(amended["acceptance"][0]["checked"])
        state, events = self.store.read()
        self.assertEqual(state["tickets"][0], amended)
        self.assertTrue(self.store.ledger.read_bytes().startswith(prefix))
        self.assertEqual(events[-2]["ticket"]["status"], "done")
        self.assertTrue(events[-2]["ticket"]["acceptance"][0]["checked"])
        self.assertEqual(events[-2]["ticket"]["acceptance"][0]["text"], "旧年度の記録を表示できる")
        with self.assertRaises(TicketError):
            self.store.update("BUG-001", "status", status="done")

    def test_acceptance_invalid_index_does_not_write_history(self):
        self.create()
        before = self.store.ledger.read_bytes(), self.store.snapshot.read_bytes()
        for index in (0, -1, 2, 1.5, "1", True, None):
            with self.subTest(index=index), self.assertRaises(TicketError):
                self.store.update("BUG-001", "acceptance", "条件変更", index=index, text="変更後の条件")
            self.assertEqual((self.store.ledger.read_bytes(), self.store.snapshot.read_bytes()), before)

    def test_acceptance_requires_reason_and_bounded_nonempty_text(self):
        self.create()
        before = self.store.ledger.read_bytes(), self.store.snapshot.read_bytes()
        for note, text in (("", "新条件"), ("   ", "新条件"), ("変更理由", ""), ("変更理由", "   "), ("変更理由", "あ" * 1001)):
            with self.subTest(note=note, length=len(text)), self.assertRaises(TicketError):
                self.store.update("BUG-001", "acceptance", note, index=1, text=text)
            self.assertEqual((self.store.ledger.read_bytes(), self.store.snapshot.read_bytes()), before)

    def test_concurrent_updates_do_not_lose_events(self):
        self.create()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda number: TicketStore(self.root).update("BUG-001", "comment", text=f"確認{number}"), range(4)))
        state, events = self.store.read()
        self.assertEqual(len(results), 4)
        self.assertEqual(len(state["tickets"][0]["comments"]), 4)
        self.assertEqual([event["sequence"] for event in events], [1, 2, 3, 4, 5])
        self.assertEqual(state["tickets"][0]["revision"], 5)

    def test_board_escapes_script_data_and_rejects_outside_paths(self):
        malicious = '</script><script>alert("x")</script>&\u2028'
        self.store.create("BUG-001", malicious, malicious, [malicious])
        generated = (self.root / "outputs" / "project-board.html").read_text(encoding="utf-8")
        self.assertNotIn(malicious, generated)
        embedded = re.search(r'<script type="application/json" id="board-data">(.*?)</script>', generated, re.DOTALL).group(1)
        self.assertEqual(json.loads(embedded)["state"]["tickets"][0]["title"], malicious.strip())
        self.assertIn("\\u003c/script\\u003e", embedded)
        self.assertNotIn("innerHTML", generated)
        self.assertIn("connect-src 'none'", generated)
        for path in ("../outside.md", "javascript:alert(1)", "https://example.com", "C:/secret.txt"):
            with self.assertRaises(TicketError):
                self.store.update("BUG-001", "document", path=path)
        with self.assertRaises(TicketError):
            TicketStore(PROJECT_ROOT.parent)

    def test_ledger_corruption_is_reported_without_overwriting_snapshot(self):
        self.create()
        snapshot = self.store.snapshot.read_bytes()
        corrupted = self.store.ledger.read_bytes().replace(b'"priority":"P2"', b'"priority":"P1"')
        self.store.ledger.write_bytes(corrupted)
        with self.assertRaises(TicketError):
            self.store.read()
        self.assertEqual(self.store.snapshot.read_bytes(), snapshot)
        self.assertEqual(self.store.ledger.read_bytes(), corrupted)

    def test_task_import_is_idempotent_and_preserves_acceptance(self):
        (self.root / "TASKS.md").write_text("| T01 | 最優先・主担当 | 資産確認 | なし | 所在を記録 |\n| T02 | 高・設計 | 体験設計 | T01 | 2戦略を説明 |\n", encoding="utf-8")
        self.assertEqual(len(self.store.import_tasks()), 2)
        self.assertEqual(self.store.import_tasks(), [])
        state, events = self.store.read()
        self.assertEqual(len(events), 2)
        self.assertEqual(state["tickets"][1]["dependencies"], ["T01"])
        self.assertEqual(state["tickets"][1]["acceptance"][0]["text"], "2戦略を説明")
        self.assertTrue(all(ticket["status"] == "todo" for ticket in state["tickets"]))


if __name__ == "__main__":
    unittest.main()
