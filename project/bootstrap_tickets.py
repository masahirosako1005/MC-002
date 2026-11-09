"""Record the existing work at bootstrap time; never backdate or overwrite it."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from tickets import ORIGIN, TicketStore


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    store = TicketStore()
    store.import_tasks()
    task_states = {
        "T01": ("in_progress", "既存資料・サンプル・API境界は整理。正式な固有名詞、参照CSS、提出条件などは未確定。"),
        "T02": ("review", "架空都市の桜社・会議館・海辺・水門と2戦略を設計・初期データへ反映。最終シナリオの受入確認待ち。"),
        "T03": ("review", "ローカルCSV分析・取込スクリプトを実装。訂正版CSVの重複扱いはBUG-005で追跡。分析全項目の受入確認は主担当が更新する。"),
        "T04": ("review", "API契約、状態分離、履歴版、認証・復旧と独立セキュリティレビューを作成。全受入条件の照合待ち。"),
        "T05": ("in_progress", "Python・WSL・Dockerの環境整備が進行。Windows公開経路とネットワーク制限をBUG-004で追跡。"),
        "T06": ("review", "Reactのスマホ画面を実装。アクセシビリティの残課題BUG-006と実操作の確認を追跡。"),
        "T07": ("review", "FastAPI・SQLite、Cookie認証、CSRF、復旧コード、DB整合性、独立したサンプル分析DBを実装。全体の結合受入確認待ち。"),
        "T08": ("review", "訪問、問題開始、回答・ヒント、採点、実績、次の旅を実装。API自動試験は確認済み。UI結合の最終証拠を主担当が登録する。"),
        "T09": ("review", "会議館の往復＋体験＋余裕時間、営業時間・休業日をAPI試験で確認。実操作証拠と全受入条件の最終照合待ち。"),
        "T10": ("review", "旅の手帳、候補の保存・取消、復旧を実装。旧年度collection表示はBUG-001で追跡。"),
        "T11": ("review", "四季・2難易度の異なる問題、同じ問題版の最高点比較を実装。画面を含む受入確認待ち。"),
        "T12": ("review", "本人が選ぶ通年の人生行事と、海辺の季節別体験を実装。機微情報を推定しない方針。受入の最終確認待ち。"),
        "T13": ("in_progress", "大会調査の依頼・受領資料を整理中。約50大会の有効件数と不足、設計への採否を確認する。"),
        "T14": ("in_progress", "外部基準と審査項目の対応を整理。適用版・要求ID・検証証拠・非該当理由の最終照合を進める。"),
        "T15": ("in_progress", "API33件合格、独立セキュリティレビューとブラウザー試験で発見した課題を個別ticket化。全体合格とは扱わない。"),
        "T16": ("in_progress", "スマホの実操作・アクセシビリティ計測が進行。旅の手帳のコントラスト不合格をBUG-006で追跡。"),
    }
    state, _ = store.read()
    current = {ticket["id"]: ticket for ticket in state["tickets"]}
    for ticket_id, (status, note) in task_states.items():
        if current[ticket_id]["revision"] == 1:
            store.update(ticket_id, "status", ORIGIN + " " + note, status=status)
            store.update(ticket_id, "comment", text=note)

    bugs = [
        {
            "id": "BUG-001", "title": "年度が変わると獲得した季節が未達成に戻る", "priority": "P1", "owner": "バックエンド・UI", "status": "review",
            "description": "完了attemptを現在のcatalog.gamesへ照合していたため、旧年度の問題がカタログから外れると収集表示が消える。保存済みseasonのAPI返却とフロント参照は修正済み。年越しブラウザー表示の実測は未確認。",
            "acceptance": ["翌年度・復旧後も旧問題のattemptとseasonが保持される", "現在カタログにない旧年度の獲得季節をブラウザーでも表示できる"],
            "documents": ["docs/SECURITY-REVIEW.md", "docs/API.md", "frontend/src/Journal.tsx"],
            "evidence": [("backend pytest 33件合格（6.10秒）。test_completed_attempt_keeps_season_when_catalog_moves_to_next_yearで翌年度のcatalogから旧gameが消えた後もattempt全項目とseasonが保持されることを確認。起票以前に実行した作業をこの時点で整理。", "backend/tests/test_api.py"), ("独立レビューでAPI修正とfrontendのa.season参照を確認。年越しのブラウザー実測は未実施と明記されている。", "docs/SECURITY-REVIEW.md")], "checked": [1],
        },
        {
            "id": "BUG-002", "title": "想定外500応答にCSPと保存禁止が付かない", "priority": "P2", "owner": "バックエンド", "status": "done",
            "description": "最外層の例外応答が通常のヘッダー付与を通らなかった。共通ヘッダー関数を想定外500応答へも適用し、独立レビューで再確認した。",
            "acceptance": ["RuntimeErrorを注入した500応答にCSP・no-store・nosniff・frame拒否・referrer抑制が付く", "500本文へ例外詳細を出さず、日本語の汎用エラーを返す"],
            "documents": ["docs/SECURITY-REVIEW.md", "backend/app/security.py", "backend/app/main.py"],
            "evidence": [("backend pytest 33件合格（6.10秒）。test_unexpected_error_keeps_security_headers_and_hides_detailsで実際の500応答ヘッダーと秘密非露出を検証。", "backend/tests/test_api.py"), ("SEC-02の独立再実行で500・秘密非露出・Cache-Control:no-store・base-uri noneを含むCSPを確認済み。", "docs/SECURITY-REVIEW.md")], "checked": [1, 2],
        },
        {
            "id": "BUG-003", "title": "セッション失効後の再試行で手帳を開き直せない", "priority": "P2", "owner": "UI", "status": "in_progress",
            "description": "成功したsessionPromiseが保持され、他APIの401/403後に初期化をやり直せない場合がある。サーバーは認証を拒否するため権限突破ではない。主担当からUI担当へ修正を依頼済み。",
            "acceptance": ["セッション失効・別タブ復旧後に、画面内の再試行で新しい認証状態を取得できる", "失敗した書込を自動再送して二重変更せず、利用者が再操作できる"],
            "documents": ["docs/SECURITY-REVIEW.md", "frontend/src/api.ts"],
            "evidence": [("SEC-03として独立レビューで検出。修正・再試験の完了証拠は起票時点で未登録。", "docs/SECURITY-REVIEW.md")], "checked": [],
        },
        {
            "id": "BUG-004", "title": "Docker内部ポートへWindowsから接続できない", "priority": "P0", "owner": "環境・主担当", "status": "review",
            "description": "内部ネットワークのアプリをWindowsのlocalhostから利用できなかった。主担当報告ではgateway追加後に127.0.0.1:8080へ到達しA/Bの実操作に成功。公開範囲・ネットワーク制限の再検証を残す。",
            "acceptance": ["Windowsの127.0.0.1:8080からA/Bの主要操作を完了できる", "公開がローカルに限定され、アプリ内部ネットワークから不要な外部通信を行えないことを再検証する"],
            "documents": ["compose.yaml", "Dockerfile"],
            "evidence": [("主担当からgateway追加後のWindows到達とA/B実操作成功の報告あり。公開設定・ネットワーク制限は再検証待ち。ブラウザー試験の記録を参照する。", "artifacts/browser-tests.json")], "checked": [],
        },
        {
            "id": "BUG-005", "title": "CSV訂正版の再取込で同じ記録が重複する可能性", "priority": "P3", "owner": "データ・主担当", "status": "in_progress",
            "description": "同じファイルの再取込だけでなく、訂正版CSVで変わらない行をどう識別するかが残課題。主担当が安定したキーへの修正を予定している。元データの変更や個票の外部出力は行わない。",
            "acceptance": ["内容の一部を訂正したCSVを再取込しても、変わらない履歴を重複保存しない", "訂正・別記録・欠損キーの扱いを定義し、合成データの試験で確認する"],
            "documents": ["docs/SECURITY-REVIEW.md", "scripts/analyze_samples.py", "scripts/test_samples.py"], "evidence": [], "checked": [],
        },
        {
            "id": "BUG-006", "title": "旅の手帳の未獲得季節が薄く小さく読みにくい", "priority": "P1", "owner": "UI・品質", "status": "in_progress",
            "description": "主担当のブラウザー試験8件中7件成功・1件失敗。未獲得季節spanのコントラスト3.89が目標4.5未満で、文字サイズ8.48px。UI担当が修正中。",
            "acceptance": ["未獲得季節の通常サイズの文字コントラストが4.5:1以上になる", "文字を読みやすい大きさに調整し、スマホ表示とアクセシビリティ検査を再実行する"],
            "documents": ["frontend/src/Journal.tsx", "artifacts/axe-journal.json", "artifacts/browser-tests.json"],
            "evidence": [("初回の旅の手帳アクセシビリティ検査でcontrast不合格を検出。修正後の成功結果ではない。", "artifacts/axe-journal.json"), ("主担当報告のブラウザー試験8件・成功7件・失敗1件の記録。", "artifacts/browser-tests.json")], "checked": [],
        },
    ]
    existing = {ticket["id"] for ticket in store.read()[0]["tickets"]}
    for bug in bugs:
        if bug["id"] in existing:
            continue
        store.create(bug["id"], bug["title"], bug["description"], bug["acceptance"], bug["priority"], bug["owner"], "bug", documents=bug["documents"], origin=ORIGIN)
        for text, path in bug["evidence"]:
            store.update(bug["id"], "evidence", text=text, path=path)
        for index in bug["checked"]:
            store.update(bug["id"], "check", "登録した試験・独立レビューの証拠で確認。", index=index, checked=True)
        store.update(bug["id"], "status", "起票時点で確認できる修正・検証範囲を反映。", status=bug["status"])
    store.build()
    state, events = store.read()
    print(f"{len(state['tickets'])}件、イベント{len(events)}件を整理しました。")


if __name__ == "__main__":
    main()
