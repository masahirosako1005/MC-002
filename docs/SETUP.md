# Windows環境の導入・再現手順

確認日：2026-11-09。アプリの完成・動作検証とは別に、環境の導入結果を記録する。

## 確認した構成

| 項目 | 状態 |
|---|---|
| OS | Windows 11 Pro、ビルド26200 |
| メモリ | 約16 GiB。確認時の空きは約3.4 GiBであり、重い作業を無制限に並列化しない |
| Node.js / npm | v24.21.0 / 11.19.0、導入済み |
| Python | 3.13.17を公式wingetパッケージからユーザー単位で導入済み |
| Python仮想環境 | PJ内 `.venv` に作成済み。backend/requirements-dev.txt の導入成功 |
| WSL | 当初未導入。管理者権限で公式パッケージ2.7.14.0を導入。カーネル6.18.33.2-2、既定WSL2を確認 |
| VirtualMachinePlatform | 既にEnabledだった。今回は有効化変更・Windows再起動を実行していない |
| Docker Desktop | 4.98.0、ユーザー単位で既に導入済み。WSL導入後に再起動しServer応答を確認 |
| Docker CLI / Compose | 29.9.2 / v5.6.1 |
| Docker Engine | 29.9.2、linux/amd64。`docker version` のServer情報を確認済み |
| WSL内のDocker | `docker-desktop` がRunning、WSLバージョン2 |
| Python依存 | `pip check` で依存矛盾なし |

当初の `wsl --install` は未導入メッセージで終了した。通常権限のwingetによるWSL導入も管理者権限不足で失敗したため、PJ内 `scripts/enable-wsl.ps1` を管理者として実行し、公式パッケージ導入とバージョン確認まで行った。取得したインストーラーはwingetでハッシュ検証された。

## 別PCでの初回準備

### このPCで適用した資源制限

初回Docker起動直後はWindowsの空きメモリが約0.7 GiBまで減少した。既存の `%UserProfile%/.wslconfig` が存在しないことを確認し、プロジェクト内 `scripts/wslconfig.example` を設定ファイルとして配置した。アプリのソースをPJ外へ配置したものではなく、WSLのシステム設定である。

- WSLメモリ上限：3 GiB
- 仮想CPU：2
- スワップ：1 GiB
- 自動メモリ回収：gradual

Docker Desktop停止→WSL停止→Docker再起動で適用した。OS再起動は行っていない。Dockerから見えるCPUは2、メモリは約2.84 GiBとなり、設定反映を確認した。停止時はWindowsの空きが約4.5 GiBに回復した。空き容量は他作業でも変動するため、ビルドとブラウザー検証の前に再確認する。

`.wslconfig` は全WSL2ディストリビューションに適用される。このPCではDocker用のディストリビューションだけが動作していることを確認してから停止した。別PCでは既存設定や他のWSL作業を確認し、そのまま上書き・停止しない。

### 準備手順

ネットワークを使うのはツール・依存・コンテナイメージの初回取得時。完成アプリの通常実行はローカルで完結する。

1. Node.js、Python 3.12以降、Docker Desktopを導入する。
2. WSL2がなければ管理者PowerShellから本PJの `scripts/enable-wsl.ps1` を実行する。Windowsが再起動を要求する場合は作業を保存して再起動する。スクリプトは自動再起動しない。
3. `wsl --version` と `wsl --status` を確認し、Docker Desktopを起動する。WSL1を使わないため、WSL1機能が無効という表示だけではWSL2の異常ではない。
4. `docker version` のClientに加えてServer情報が表示されることを確認する。
5. PJルートで `docker compose up --build -d` を実行する。起動後は `http://localhost:8080` を開く。

Docker構成は初期設定でホストの127.0.0.1だけに公開する。同じPCのブラウザーで利用する構成であり、スマホ実機へのLAN公開を設定済みという意味ではない。

## Windows上での開発・試験

```powershell
# PJルートから実行。Pythonの場所が違う場合は引数で指定する。
./scripts/setup-local.ps1

# バックエンドの試験（テスト作成後）
./.venv/Scripts/python.exe -m pytest backend/tests -q
```

`setup-local.ps1` はPJ内に仮想環境を作成し、Python依存、フロントエンド依存、ビルドを確認する。アプリ用ソースや生成物をPJ外へ置かない。

Python仮想環境を使用し、WindowsAppsの実行エイリアスだけをPythonの導入確認に使わない。Docker内のPythonはDockerfile指定の3.12系であり、Windows側3.13.17とは異なるため、コンテナ側でも別途動作確認する。

## 公式資料

- [Microsoft：WSLのインストール](https://learn.microsoft.com/en-us/windows/wsl/install)
- [Docker：Windows版の導入要件](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker：Desktopの再起動](https://docs.docker.com/reference/cli/docker/desktop/restart/)
- [Microsoft：WSLの資源設定](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)

公式資料の一般的な手順と、このPCで実際に確認した結果を区別する。環境構築後も、コンテナ起動、データ永続化、通信遮断、復元をアプリの受入試験として別途実行する。
