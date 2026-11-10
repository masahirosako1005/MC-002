"""Offline ticket ledger and board. Run from anywhere inside the project."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATUSES = {"todo": "未着手", "in_progress": "作業中", "review": "検証中", "done": "完了"}
PRIORITIES = ("P0", "P1", "P2", "P3")
ORIGIN = "既存作業を起票時点で整理。過去の着手日時・完了日時は推定していない。"


class TicketError(ValueError):
    pass


def timestamp():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def script_json(value):
    encoded = json.dumps(value, ensure_ascii=False)
    return encoded.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def bounded_text(value, maximum=5000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise TicketError(f"空欄は使えません。文字数は{maximum}文字以内にしてください。")
    return value.strip()


class TicketStore:
    def __init__(self, root=PROJECT_ROOT):
        self.root = Path(root).resolve()
        if not self.root.is_relative_to(PROJECT_ROOT):
            raise TicketError("保存先はこのPJ内に限定します。")
        self.directory = self.safe_path("project")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.snapshot = self.safe_path("project/tickets.json")
        self.ledger = self.safe_path("project/events.jsonl")

    def safe_path(self, relative):
        candidate = (self.root / relative).resolve()
        if not candidate.is_relative_to(self.root):
            raise TicketError("PJ外のパスは使用できません。")
        return candidate

    def document_path(self, value):
        value = bounded_text(value, 500).replace("\\", "/")
        if value.startswith("/") or ":" in value or "#" in value or "?" in value or any(part in {"", ".", ".."} for part in value.split("/")):
            raise TicketError("関連文書はPJ内の相対パスを指定してください。")
        self.safe_path(value)
        return value

    def display_document_path(self, value):
        """Resolve a relocated link for display without changing ledger data."""
        original = self.document_path(value)
        fixed = {"community/README.md": "docs/OPERATIONS.md",
                 "community/compose.yaml": "compose.yaml", "community/Dockerfile": "Dockerfile",
                 "community/.dockerignore": ".dockerignore"}
        candidate = fixed.get(original, original)
        if original.startswith("outputs/"):
            name = original.removeprefix("outputs/")
            if re.fullmatch(r"kou-revisit-intro-(?:v[1-9](?:-ja)?\.(?:mp4|vtt)|ja\.vtt)", name) or name in {"community-intro.mp4", "community-intro-poster.png"}:
                candidate = "outputs/history/videos/" + name
            elif name in {"tang-you-chi-presentation-final.pptx", "tang-you-chi-presentation-final.pdf"}:
                candidate = "outputs/history/presentation/" + name
            elif name in {"tang-you-chi-source.zip", "tang-you-chi-history.bundle", "release-manifest.json"}:
                candidate = "outputs/history/legacy-release/" + name
        if original.startswith("community/artifacts/"):
            candidate = "artifacts/community/" + original.removeprefix("community/artifacts/")
        elif original.startswith("community/") and original not in fixed:
            relative = original.removeprefix("community/")
            if relative.split("/", 1)[0] in {"backend", "frontend", "assets", "models", "backups", "deploy", "quality", "scripts"}:
                candidate = relative
            elif "/" not in relative and relative.lower().endswith(".md"):
                candidate = "docs/contracts/" + relative
        # Never invent a destination for an unavailable historical document.
        candidate = self.document_path(candidate)
        return candidate if candidate != original and self.safe_path(candidate).is_file() else original

    @contextmanager
    def locked(self):
        lock_path = self.safe_path("project/.tickets.lock")
        with lock_path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            deadline = time.monotonic() + 10
            while True:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TicketError("別の更新が進行中です。少し待って再実行してください。")
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def atomic_write(self, destination, content):
        destination = self.safe_path(destination.relative_to(self.root))
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    @staticmethod
    def state_from_events(events):
        tickets = {}
        for event in events:
            tickets[event["ticket"]["id"]] = event["ticket"]
        return {"schema_version": 1, "revision": len(events),
                "last_event_hash": events[-1]["hash"] if events else "0" * 64,
                "updated_at": events[-1]["at"] if events else None,
                "tickets": sorted(tickets.values(), key=lambda ticket: ticket["id"])}

    def load_locked(self):
        events = []
        previous = "0" * 64
        if self.ledger.exists():
            with self.ledger.open("r", encoding="utf-8") as handle:
                for sequence, line in enumerate(handle, start=1):
                    if not line.endswith("\n"):
                        raise TicketError("イベント末尾が不完全です。履歴を変更せず復旧を確認してください。")
                    try:
                        event = json.loads(line)
                        digest = event.pop("hash")
                        valid = event["sequence"] == sequence and event["previous_hash"] == previous and hashlib.sha256(canonical(event).encode("utf-8")).hexdigest() == digest
                        if not valid or not isinstance(event["ticket"]["id"], str):
                            raise TicketError("イベントの順序または整合性が一致しません。")
                        event["hash"] = digest
                    except (KeyError, TypeError, json.JSONDecodeError) as error:
                        raise TicketError("イベント形式を読み取れません。履歴は変更していません。") from error
                    events.append(event)
                    previous = digest
        rebuilt = self.state_from_events(events)
        if self.snapshot.exists():
            try:
                saved = json.loads(self.snapshot.read_text(encoding="utf-8"))
                revision = saved["revision"]
            except (KeyError, json.JSONDecodeError) as error:
                raise TicketError("正本JSONが壊れています。退避してイベントからの再構成を確認してください。") from error
            if type(revision) is not int or revision < 0 or revision > len(events):
                raise TicketError("正本とイベントの版が一致しません。")
            expected = self.state_from_events(events[:revision])
            if canonical(saved) != canonical(expected):
                raise TicketError("正本の内容がイベントと一致しません。直接編集せずCLIを使ってください。")
            if revision < len(events):
                self.atomic_write(self.snapshot, json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n")
        elif events:
            self.atomic_write(self.snapshot, json.dumps(rebuilt, ensure_ascii=False, indent=2) + "\n")
        return rebuilt, events

    def read(self):
        with self.locked():
            return self.load_locked()

    def append_locked(self, state, events, action, ticket, note):
        event = {"sequence": len(events) + 1, "event_id": uuid4().hex, "at": timestamp(),
                 "action": action, "note": note, "previous_hash": state["last_event_hash"], "ticket": ticket}
        event["hash"] = hashlib.sha256(canonical(event).encode("utf-8")).hexdigest()
        with self.ledger.open("ab") as handle:
            handle.write((canonical(event) + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        events.append(event)
        state = self.state_from_events(events)
        self.atomic_write(self.snapshot, json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        self.render_locked(state, events)
        return ticket

    def create(self, ticket_id, title, description, acceptance, priority="P2", owner="主担当", kind="task", dependencies=None, documents=None, origin="この時点で新規起票"):
        if not re.fullmatch(r"[A-Z][A-Z0-9]*-?\d{2,5}", ticket_id):
            raise TicketError("IDはT01やBUG-001の形式にしてください。")
        if priority not in PRIORITIES or kind not in {"task", "bug"}:
            raise TicketError("優先度または種別が正しくありません。")
        acceptance = [bounded_text(value, 1000) for value in acceptance]
        if not acceptance:
            raise TicketError("受入条件を1つ以上指定してください。")
        with self.locked():
            state, events = self.load_locked()
            if any(ticket["id"] == ticket_id for ticket in state["tickets"]):
                raise TicketError("このIDはすでに登録されています。")
            created_at = timestamp()
            ticket = {"id": ticket_id, "title": bounded_text(title, 200), "description": bounded_text(description),
                      "type": kind, "priority": priority, "status": "todo", "owner": bounded_text(owner, 100),
                      "created_at": created_at, "updated_at": created_at, "revision": 1, "origin": origin,
                      "acceptance": [{"text": item, "checked": False} for item in acceptance],
                      "dependencies": dependencies or [], "documents": [self.document_path(item) for item in documents or []],
                      "comments": [], "evidence": [], "revisions": []}
            return self.append_locked(state, events, "created", ticket, origin)

    def update(self, ticket_id, action, note="", **values):
        if note:
            note = bounded_text(note)
        with self.locked():
            state, events = self.load_locked()
            original = next((ticket for ticket in state["tickets"] if ticket["id"] == ticket_id), None)
            if original is None:
                raise TicketError("チケットが見つかりません。")
            ticket = json.loads(json.dumps(original))
            now = timestamp()
            if action == "status":
                status = values["status"]
                if status not in STATUSES:
                    raise TicketError("状態が正しくありません。")
                if status == "done" and (not all(item["checked"] for item in ticket["acceptance"]) or not ticket["evidence"]):
                    raise TicketError("完了には全受入条件の確認と証拠の登録が必要です。")
                if ticket["status"] == "done" and status != "done" and not note:
                    raise TicketError("再開する理由を--noteで残してください。")
                ticket["status"] = status
            elif action == "comment":
                ticket["comments"].append({"at": now, "text": bounded_text(values["text"])})
            elif action == "evidence":
                path = self.document_path(values["path"]) if values.get("path") else None
                if path and not self.safe_path(path).is_file():
                    raise TicketError("証拠のファイルが見つかりません。")
                ticket["evidence"].append({"at": now, "text": bounded_text(values["text"]), "path": path})
            elif action == "check":
                index = values["index"] - 1
                if index < 0 or index >= len(ticket["acceptance"]):
                    raise TicketError("受入条件の番号が範囲外です。")
                if ticket["status"] == "done" and not values["checked"]:
                    raise TicketError("完了したチケットは先に再開してください。")
                ticket["acceptance"][index]["checked"] = bool(values["checked"])
            elif action == "acceptance":
                if not note:
                    raise TicketError("受入条件を改訂する理由を--noteで残してください。")
                index = values["index"]
                if type(index) is not int or not 1 <= index <= len(ticket["acceptance"]):
                    raise TicketError("受入条件の番号が範囲外です。")
                condition = ticket["acceptance"][index - 1]
                condition["text"] = bounded_text(values["text"], 1000)
                condition["checked"] = False
                if ticket["status"] == "done":
                    ticket["status"] = "review"
            elif action == "document":
                document = self.document_path(values["path"])
                if document not in ticket["documents"]:
                    ticket["documents"].append(document)
            elif action == "revision":
                revision = values["revision"]
                if not re.fullmatch(r"[0-9a-fA-F]{7,40}", revision):
                    raise TicketError("commitは7〜40文字の16進数で指定してください。")
                result = subprocess.run(["git", "show", "--no-patch", "--format=%H%n%s", revision], cwd=self.root, capture_output=True, text=True, encoding="utf-8", timeout=10, check=False)
                if result.returncode:
                    raise TicketError("このPJでcommitを確認できませんでした。")
                lines = result.stdout.splitlines()
                if not lines or not re.fullmatch(r"[0-9a-f]{40}", lines[0]):
                    raise TicketError("commitを確認できませんでした。")
                revision_path = f"project/revisions/{lines[0]}.txt"
                summary = "\n".join(lines[1:])
                self.atomic_write(self.safe_path(revision_path), f"リビジョン: {lines[0]}\n件名: {summary}\n確認日時: {now}\n")
                if not any(item["hash"] == lines[0] for item in ticket["revisions"]):
                    ticket["revisions"].append({"hash": lines[0], "summary": summary, "path": revision_path, "at": now})
            else:
                raise TicketError("不明な操作です。")
            ticket["revision"] += 1
            ticket["updated_at"] = now
            return self.append_locked(state, events, action, ticket, note)

    def render_locked(self, state, events):
        template = PROJECT_ROOT / "project" / "board-template.html"
        if not template.is_file():
            raise TicketError("ボードのテンプレートが見つかりません。JSON更新は保存されています。")
        display_state = json.loads(json.dumps(state))
        for ticket in display_state["tickets"]:
            ticket["documents"] = [self.display_document_path(path) for path in ticket["documents"]]
            for record in ticket["evidence"]:
                if record["path"]:
                    record["path"] = self.display_document_path(record["path"])
        data = {"state": display_state, "events": [{key: event[key] for key in ("sequence", "at", "action", "note")} | {"ticket_id": event["ticket"]["id"], "revision": event["ticket"]["revision"]} for event in events]}
        rendered = template.read_text(encoding="utf-8").replace("__BOARD_UPDATED__", html.escape(state["updated_at"] or "まだ起票されていません", quote=True)).replace("__BOARD_DATA__", script_json(data))
        self.atomic_write(self.safe_path("outputs/project-board.html"), rendered)

    def build(self):
        with self.locked():
            state, events = self.load_locked()
            self.render_locked(state, events)
            return state

    def import_tasks(self):
        content = self.safe_path("TASKS.md").read_text(encoding="utf-8")
        created = []
        existing = {ticket["id"] for ticket in self.read()[0]["tickets"]}
        for line in content.splitlines():
            if not re.match(r"\| T\d{2} \|", line):
                continue
            ticket_id, priority_owner, title, dependency_text, acceptance = [part.strip() for part in line.strip("|").split("|")]
            if ticket_id in existing:
                continue
            priority_text, owner = priority_owner.split("・", 1)
            priority = "P1" if priority_text in {"最優先", "高"} else "P2"
            dependencies = re.findall(r"T\d{2}", dependency_text)
            created.append(self.create(ticket_id, title, f"TASKS.mdから整理。依存: {dependency_text}", [acceptance], priority, owner,
                                       dependencies=dependencies, documents=["TASKS.md", "DESIGN.md"], origin=ORIGIN))
        return created


def parser():
    command = argparse.ArgumentParser(description="ローカルのチケットと4列ボードを管理する")
    subparsers = command.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init", help="TASKS.mdのT01〜T18を未着手として起票（重複はスキップ）")
    subparsers.add_parser("build", help="ボードを再生成")
    subparsers.add_parser("list", help="チケット一覧")
    subparsers.add_parser("validate", help="履歴と正本の整合性を検証")
    show = subparsers.add_parser("show")
    show.add_argument("id")
    create = subparsers.add_parser("create")
    create.add_argument("id")
    create.add_argument("--title", required=True)
    create.add_argument("--description", required=True)
    create.add_argument("--accept", action="append", required=True)
    create.add_argument("--priority", choices=PRIORITIES, default="P2")
    create.add_argument("--owner", default="主担当")
    create.add_argument("--type", choices=["task", "bug"], default="task")
    create.add_argument("--depends", action="append", default=[])
    create.add_argument("--doc", action="append", default=[])
    status = subparsers.add_parser("status")
    status.add_argument("id")
    status.add_argument("status", choices=STATUSES)
    status.add_argument("--note", default="")
    for name in ("comment", "evidence"):
        item = subparsers.add_parser(name)
        item.add_argument("id")
        item.add_argument("--text", required=True)
        if name == "evidence":
            item.add_argument("--file")
    check = subparsers.add_parser("check")
    check.add_argument("id")
    check.add_argument("index", type=int)
    check.add_argument("--undo", action="store_true")
    check.add_argument("--note", default="")
    acceptance = subparsers.add_parser("acceptance", help="受入条件を改訂し、確認を未達へ戻す（履歴を保持）")
    acceptance.add_argument("id")
    acceptance.add_argument("index", type=int)
    acceptance.add_argument("--text", required=True)
    acceptance.add_argument("--note", required=True)
    document = subparsers.add_parser("document")
    document.add_argument("id")
    document.add_argument("path")
    revision = subparsers.add_parser("revision")
    revision.add_argument("id")
    revision.add_argument("commit")
    return command


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    arguments = parser().parse_args(argv)
    try:
        store = TicketStore()
        if arguments.command == "init":
            print(f"{len(store.import_tasks())}件を起票しました。")
        elif arguments.command == "create":
            ticket = store.create(arguments.id, arguments.title, arguments.description, arguments.accept, arguments.priority, arguments.owner, arguments.type, arguments.depends, arguments.doc)
            print(f"{ticket['id']} を起票しました。")
        elif arguments.command in {"status", "comment", "evidence", "check", "acceptance", "document", "revision"}:
            values = {}
            note = getattr(arguments, "note", "")
            if arguments.command == "status":
                values = {"status": arguments.status}
            elif arguments.command == "comment":
                values = {"text": arguments.text}
            elif arguments.command == "evidence":
                values = {"text": arguments.text, "path": arguments.file}
            elif arguments.command == "check":
                values = {"index": arguments.index, "checked": not arguments.undo}
            elif arguments.command == "acceptance":
                values = {"index": arguments.index, "text": arguments.text}
            elif arguments.command == "document":
                values = {"path": arguments.path}
            elif arguments.command == "revision":
                values = {"revision": arguments.commit}
            ticket = store.update(arguments.id, arguments.command, note, **values)
            print(f"{ticket['id']} を更新しました（版{ticket['revision']}・{STATUSES[ticket['status']]}）。")
        elif arguments.command == "build":
            store.build()
            print("outputs/project-board.html を更新しました。")
        else:
            state, events = store.read()
            if arguments.command == "validate":
                print(f"整合性確認: {len(state['tickets'])}件・イベント{len(events)}件、正本と履歴は一致しています。")
            elif arguments.command == "show":
                ticket = next((item for item in state["tickets"] if item["id"] == arguments.id), None)
                if ticket is None:
                    raise TicketError("チケットが見つかりません。")
                print(json.dumps(ticket, ensure_ascii=False, indent=2))
            else:
                for ticket in state["tickets"]:
                    print(f"{ticket['id']:8} {ticket['priority']} {STATUSES[ticket['status']]:4} {ticket['title']}")
        return 0
    except (TicketError, OSError, subprocess.TimeoutExpired) as error:
        print(f"更新できませんでした: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
