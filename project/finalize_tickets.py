"""Apply evidence-based progress through the public ticket CLI only."""

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "tickets.py"


def current(ticket_id):
    state = json.loads((ROOT / "project" / "tickets.json").read_text(encoding="utf-8"))
    return next(ticket for ticket in state["tickets"] if ticket["id"] == ticket_id)


def command(*arguments):
    result = subprocess.run([sys.executable, str(CLI), *arguments], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr)


def record(ticket_id, status, text, evidence_file, checked=()):
    ticket = current(ticket_id)
    if any(item["text"] == text for item in ticket["evidence"]):
        return
    command("evidence", ticket_id, "--text", text, "--file", evidence_file)
    if "docs/ACCEPTANCE.md" not in ticket["documents"]:
        command("document", ticket_id, "docs/ACCEPTANCE.md")
    for number in checked:
        if not current(ticket_id)["acceptance"][number - 1]["checked"]:
            command("check", ticket_id, str(number), "--note", "保存された結果と試験コード・実装を照合。対象範囲と限界は証拠・ACCEPTANCE.mdを参照。")
    if current(ticket_id)["status"] != status:
        command("status", ticket_id, status, "--note", "最終整理時点の受入条件と証拠を照合。未達は合格扱いしない。")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    records = [
        ("BUG-001", "done", "backend33件の翌年度・復旧後season保持と、browser12件中『過年度の謎の季節がカタログに依存せず残る』の合格を確認。後者は旧attempt応答差替えで現在catalogにない秋の収集印1件を確認する。実時計変更のフルスタックE2Eではなく、API境界試験との組合せ。", "artifacts/browser-tests.json", (1, 2)),
        ("BUG-002", "done", "最終保存ログbackend33 passed（5.14秒）を照合。500注入時のCSP・no-store・nosniff・frame/referrerと詳細非露出を確認する試験を含む。独立SEC-02でも同じ例外注入を再確認済み。", "artifacts/backend-tests.txt", (1, 2)),
        ("BUG-003", "review", "Promiseを成功/失敗後に解放するコードと、初期journal503後の再試行でGET sessionが2回以上となるブラウザー合格を確認。変更APIに無条件自動再送はない。ただし失効した旧画面の書込からの回復と別タブ復旧後の旧タブの全導線はこの12件には含まれず、主担当が追加修正・実結合試験中。受入条件1は未確認のまま残す。", "docs/SECURITY-REVIEW.md", (2,)),
        ("BUG-004", "done", "Windows127.0.0.1:8080を対象とするA/Bブラウザー12件合格を確認。container-verificationはapp internal network、外部TCP1.1.1.1:443接続失敗、gatewayのHostIp127.0.0.1を記録。composeでもappに公開portsなし、固定gateway経由。gateway自身の全外向き通信遮断や全宛先・全プロトコル遮断を主張しない。", "artifacts/container-verification.json", (1, 2)),
        ("BUG-005", "done", "sample-tests.txtの5件合格と試験コードを照合。氏名と日時区切りだけ訂正したCSVの再取込で1件保持・already_present1。不正日時/欠損利用者/欠損対象の拒否も確認。自然キーの同一別イベントは統合、キー列そのものの訂正は別記録となるとDATA-QUALITY.md/SEC-04で定義。旧DBの移行やイベントID付き継続同期は対象外。", "artifacts/sample-tests.txt", (1, 2)),
        ("BUG-006", "done", "修正前のaxe-journal-before-fix.jsonを保持。修正後axe-journal.jsonは違反0で、ブラウザー12件全成功。未獲得文字色#56624f、spanのモバイル文字0.75remへの変更をstyles.cssで確認。3幅の文字拡大・390pxで200%を含む主要画面試験も成功。実利用者の読みやすさ評価とWCAG全体適合は別途未確認。", "artifacts/axe-journal.json", (1, 2)),
        ("T01", "done", "DESIGN/API/SETUPで提供済みサンプル、既存ソース/API/参照CSS/正式名称/提出条件の未提供、独立ローカル実装の接続範囲、WSL/Dockerの所在と導入を記録。T01は所在と未決事項の整理であり、未提供CSSを入手・一致確認した意味ではない。秘密情報ファイルは参照していない。", "docs/SETUP.md", (1,)),
        ("T02", "done", "CityMapに会議館→水門、北に桜社、東に海辺の関係を明示。seedに徒歩時間・滞在・季節・営業条件を設定。A次季の謎、B会議の空き時間・海辺・任意の人生行事をAPI/画面で説明・保存。位置関係は架空の見取り図で経路案内ではない。", "backend/app/seed.py", (1,)),
        ("T03", "done", "5CSVの件数、型/列、欠損・完全一致重複、参照、日時、利用範囲・限界を集計。前後のhash一致、再取込追加0、保存件数一致を確認。sample5試験合格、個票・自由記述を成果物へ再掲しない。全内容の真実性確認や実来訪率算定は行っていない。", "docs/DATA-QUALITY.md", (1,)),
        ("T04", "done", "API契約・DBモデルで訪問/挑戦/実績/候補を分離し、所有者・CSRF・一意制約・原子更新・履歴季節年度版・復旧を記載。SECURITY-REVIEWの脅威/実装/修正、backend33試験を対応付けた。既存APIへの接続仕様は未提供として分離。", "docs/API.md", (1,)),
        ("T05", "done", "SETUPにWindows/WSL2/Docker/Python導入・資源制限・起動手順を記録。container-verificationでloopback公開、app内部ネットワーク、DB永続性、rootfs/権限設定、バックアップ整合を確認。OS再起動の未処理は記録上なし。別PC初期状態からの再現は未実施。", "artifacts/container-verification.json", (1,)),
        ("T06", "review", "主要3画面の日本語遷移、空状態、コード誤り、通信失敗と再試行、320/390/430px・拡大、axe対象6画面違反0を確認。ただし元の参照CSSは未提示で、カードの大小・形状を参照へ照合する受入条件は未達。", "artifacts/browser-tests.json", ()),
        ("T07", "done", "保存・権限分離・DB制約・初期化・backup復元・復旧コードをbackend33試験で検証。サンプル再取込を5試験で確認し、仮名化分析DBと架空マスター/アプリDBを分離。旧CSV方式DBからの自動移行や自然キー訂正同期は未提供として記録。", "artifacts/backend-tests.txt", (1,)),
        ("T08", "done", "browser12件中Aの操作で無効コード→正しい訪問→謎→誤答→ヒント→表示された手掛かりから正答→75点→実績→次季保存→再表示を確認。backendは同時正答/再送の二重付与防止・サーバー採点を検証。印刷コードが物理来訪の強い証明ではない限界を記録。", "artifacts/browser-tests.json", (1,)),
        ("T09", "done", "APIで会議館から徒歩往復＋体験＋10分余裕、時間不足・火曜休み・営業終了・将来季節を確認。ブラウザーで30分海辺の候補なし、180分枠の120分候補、保存・取消・理由を確認。現実の天候等は取得しない架空設定。", "artifacts/browser-tests.json", (1,)),
        ("T10", "done", "A実績と訪問をタイムラインに表示し、B候補保存/取消、reloadとコンテナー再起動後の保持、別ブラウザーへの手帳復旧を確認。APIは候補保存で訪問/挑戦/実績が増えないことを検証。過年度の収集表示はBUG-001で確認。", "artifacts/container-verification.json", (1,)),
        ("T11", "done", "seedは四季×初級/上級の8問題で異なる正答と条件を持つ。APIで同一ゲーム版だけの最高点、初級/上級分離、年度境界を確認。Aのブラウザー動線はランキングを開かず完了できる。全問題版を全ブラウザーで手動攻略した意味ではない。", "backend/tests/test_api.py", (1,)),
        ("T12", "done", "人生行事は本人の任意選択で通年、海辺は四季で別体験。UIでお宮参りと希望する時期、冬の海辺保存を確認。APIでお宮参り候補の保存・重複防止と保存だけでは実績が変わらないことを確認。妊娠等を履歴から推定しない。", "artifacts/browser-tests.json", (1,)),
        ("T13", "review", "50候補表を受領し、採用10大会の公式資料を独立照合・分類・採否へ反映。主対象は報告値31で約50目標に19件不足、独立照合済み主対象は5。残りの出典照合・別大会としての独立性・受賞要因確認が不足するため完了にしない。", "docs/CONTEST-VERIFICATION.md", ()),
        ("T14", "done", "BENCHMARKSにASVS5.0.0/WCAG2.2/SSDF1.1の要求ID・版・適用範囲・確認方法・証拠の対応を記録。CIS本文未取得は個別適合を確定せずDocker公式のPJチェックへ分離。対応表の確定と、全要求の実測/全面適合を区別する。後者の未確認はAC-13・T15/T16へ残す。", "docs/BENCHMARKS.md", (1,)),
        ("T15", "review", "ACCEPTANCE.mdへAC01〜20の合否/条件/証拠/未確認を整理。backend33・browser12・sample5・container・依存監査0を照合。DB原子性/復元/越権を確認済みだが、BUG-003の実失効後の旧画面導線を追加検証中。未提示CSS、プレゼン、基準の全要求別結果などの残条件も未達として記録。", "docs/ACCEPTANCE.md", ()),
        ("T16", "review", "320/390/430px、390pxで200%文字、主要画面の横溢れ、キーボードの一部、動き軽減、axe対象6画面違反0を確認。実利用者の課題達成率・所要時間・誤操作・理解、スマホ実機/読み上げ、全操作のキーボード、実利用の性能指標は未測定。自動試験秒数を人の評価へ転用しない。", "docs/ACCEPTANCE.md", ()),
        ("T17", "review", "採用10大会の採否、審査基準/実装/試験証拠、未達・限界を文書へ統合。主対象約50大会の調査と実利用者評価、プレゼン最終検証が残るため提出一式全体の統合完了にはしない。候補保存と実来訪の効果は区別している。", "docs/ACCEPTANCE.md", ()),
    ]
    for item in records:
        record(*item)
    command("validate")
    print(f"{len(records)}件を証拠に沿って更新しました。T18は変更していません。")


if __name__ == "__main__":
    main()
