import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const skill =
  "C:/Users/Jisui_share002/.codex/plugins/cache/openai-primary-runtime/presentations/26.1104.22356/skills/presentations";
const runtime =
  "C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1104-2876-0_26.1104.2876.0_x64__3k8sg7r9htsxt/dependencies";
process.env.RUNTIME_NODE_MODULES ??= path.join(runtime, "node/node_modules");
const build = path.join(root, "artifacts/presentation");
const output = path.join(root, "outputs");
await fs.mkdir(build, { recursive: true });
await fs.mkdir(output, { recursive: true });
let metrics = {
  score: 5,
  apiTests: "検証中",
  browserTests: "検証中",
  status: "実装・検証中",
};
try {
  metrics = JSON.parse(
    await fs.readFile(
      path.join(root, "artifacts/release-metrics.json"),
      "utf8",
    ),
  );
} catch {}
const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
console.log("Presentation initialized");
const color = {
  paper: "#F6F2E9",
  ink: "#183E42",
  muted: "#5B6D6B",
  red: "#AF4936",
  line: "#D7D4C9",
  gold: "#AD8036",
  white: "#FFFFFF",
};
const font = "BIZ UDGothic";
function box(s, x, y, w, h, fill = color.ink) {
  return s.shapes.add({
    geometry: "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { fill: "none", width: 0 },
  });
}
function text(s, value, x, y, w, h, size = 30, fill = color.ink, bold = false) {
  const sh = s.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  sh.text = [
    {
      runs: [
        {
          run: value,
          style: { typeface: font, fontSize: `${size}px`, color: fill, bold },
        },
      ],
    },
  ];
  sh.text.style = {
    fontSize: size,
    color: fill,
    insets: 0,
    wrap: "word",
    verticalAlignment: "top",
  };
  return sh;
}
function slide(title, notes = "") {
  const s = p.slides.add();
  s.background.fill = color.paper;
  text(s, title, 72, 58, 1136, 80, 42, color.ink, true);
  box(s, 72, 154, 1136, 2, color.line);
  text(
    s,
    String(p.slides.items.length).padStart(2, "0"),
    1154,
    660,
    54,
    28,
    16,
    color.muted,
  );
  s.speakerNotes.text = notes;
  return s;
}
function statement(s, num, title, desc, y) {
  text(s, num, 76, y, 90, 64, 44, color.red, true);
  text(s, title, 188, y, 950, 52, 30, color.ink, true);
  text(s, desc, 188, y + 64, 920, 72, 23, color.muted);
}
async function shot(s, file, x, y, w, h) {
  try {
    const buf = await fs.readFile(path.join(root, "artifacts", file));
    s.images.add({
      blob: buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
      contentType: /\.jpe?g$/i.test(file) ? "image/jpeg" : "image/png",
      alt: "アプリ実画面",
      fit: "contain",
      position: { left: x, top: y, width: w, height: h },
    });
  } catch {
    text(s, "操作画面は検証後に挿入", x, y + 140, w, 90, 24, color.muted);
  }
}

{
  const s = p.slides.add();
  s.background.fill = color.ink;
  text(s, "tang you chi", 76, 76, 950, 90, 70, color.paper, true);
  text(s, "四季の謎と、次の旅", 80, 224, 1000, 130, 58, color.paper, true);
  text(
    s,
    "旅の記録から、次に訪れる理由をつくる。",
    80,
    407,
    990,
    76,
    30,
    "#CDDAD5",
  );
  box(s, 80, 557, 220, 5, color.red);
  text(s, "観光スタンプラリーの再訪拡張", 80, 595, 1000, 50, 24, "#CDDAD5");
  s.speakerNotes.text =
    "製品名・モデル都市の表記は仮。実在の平城京や奈良の地理を再現するアプリではない。今回の課題と2つの戦略、検証の根拠を説明する。";
}
{
  const s = slide(
    "一度きりの来訪を、次の旅へ",
    "課題は利用者から提示されたもの。実際の観光客への新規調査結果として扱わない。",
  );
  statement(
    s,
    "01",
    "観光客",
    "スタンプを集めたあと、また来るきっかけが見つからない。",
    196,
  );
  statement(
    s,
    "02",
    "地域事業者",
    "訪れてくれた人との接点が、一回で終わってしまう。",
    356,
  );
  text(s, "今回つくるもの", 76, 545, 290, 46, 25, color.red, true);
  text(
    s,
    "体験の記録に、次の時期と目的を結び付ける仕組み。",
    76,
    600,
    1090,
    52,
    30,
    color.ink,
    true,
  );
}
{
  const s = slide("再訪の目的をつくり、地域の機会をつなぐ");
  text(s, "A", 76, 195, 100, 80, 64, color.red, true);
  text(s, "季節で変わる謎解き", 76, 299, 515, 65, 35, color.ink, true);
  text(
    s,
    "同じ水門でも、春と秋では違う謎。\n難易度と実績で、続きを楽しむ。",
    76,
    397,
    520,
    140,
    27,
    color.muted,
  );
  box(s, 638, 205, 2, 362, color.line);
  text(s, "B", 700, 195, 100, 80, 64, color.gold, true);
  text(s, "地域にある次の機会", 700, 299, 510, 65, 35, color.ink, true);
  text(
    s,
    "会議の合間、人生の節目、海辺の四季。\n時間と希望に合う体験を選ぶ。",
    700,
    397,
    500,
    140,
    27,
    color.muted,
  );
}
{
  const s = slide(
    "水門を解いて、次の季節を残す",
    "現地コードは印刷しおりを使う。デモのコード入力は実地での所在を独立証明しない。別季節・難易度の問題と実績を説明する。",
  );
  await shot(s, "puzzle-controls.jpg", 830, 180, 300, 450);
  statement(s, "1", "現地の手がかり", "訪問を記録して、水門の謎へ進む。", 192);
  text(s, "2  三つの水門を操作する", 76, 382, 700, 54, 31, color.ink, true);
  text(
    s,
    "ヒントと条件から水量を選び、実績を得る。",
    76,
    450,
    700,
    66,
    25,
    color.muted,
  );
  text(s, "3  次の季節の体験を保存する", 76, 558, 720, 60, 31, color.red, true);
}
{
  const s = slide(
    "会議の空き時間から、次の観光へ",
    "推薦は往復の移動、体験時間、余裕時間を合計する。開催条件・時間不足の確認を含む。予約成立や実際の再訪を意味しない。",
  );
  await shot(s, "next-screen.png", 830, 180, 300, 450);
  text(s, "戻る時間に間に合う候補", 76, 208, 710, 70, 37, color.ink, true);
  text(
    s,
    "往復の移動 ＋ 滞在 ＋ 余裕時間",
    76,
    323,
    720,
    60,
    28,
    color.red,
    true,
  );
  text(
    s,
    "短時間で地域を知る。\n気になった体験を、次の旅に保存する。",
    76,
    420,
    700,
    125,
    29,
    color.muted,
  );
  text(s, "候補がないときも、理由が分かる。", 76, 582, 710, 48, 25, color.ink);
}
{
  const s = slide("旅の手帳で、時期と実績がつながる");
  const seasons = [
    ["春", "潮干狩り"],
    ["夏", "海水浴"],
    ["秋", "SUP"],
    ["冬", "釣り"],
  ];
  seasons.forEach(([season, event], i) => {
    const x = 80 + i * 290;
    text(s, season, x, 214, 240, 78, 56, i === 2 ? color.red : color.ink, true);
    box(s, x, 315, 232, 3, color.line);
    text(s, event, x, 352, 240, 58, 31, color.ink);
  });
  text(
    s,
    "人生の節目は、希望する時期に",
    80,
    487,
    1090,
    54,
    32,
    color.ink,
    true,
  );
  text(
    s,
    "安産祈願やお宮参りを任意で選択。履歴から家族構成を推測しない。",
    80,
    565,
    1100,
    80,
    24,
    color.muted,
  );
  s.speakerNotes.text =
    "海辺の活動はモデル都市の設定。実在施設の季節・営業情報ではない。七五三を含む神社の行事は任意で、利用者へ強制しない。";
}
{
  const s = slide(
    "次に集める一品から、次の訪問を選ぶ",
    "出典：docs/COLLECTION-API.md。3棚12種。初段階の獲得と全段階の完成を区別。水門訪問と今季の謎が最初のひと組。別日記録は独立した旅行や現地所在を保証しない。スクリーンショットはローカル操作検証で取得。",
  );
  await shot(s, "collection-screen.png", 870, 178, 270, 454);
  text(s, "訪問と謎で、最初のひと組", 76, 204, 730, 65, 34, color.ink, true);
  text(s, "場所・季節・続く旅の12種。\n条件と記録日を、記念品から開く。", 76, 295, 730, 110, 28, color.muted);
  text(s, "別の日、別の季節に続きがある", 76, 440, 760, 65, 32, color.ink, true);
  text(s, "狙う一品を選び、次の場所へ進む。\n手帳を引き継いでも目標が残る。", 76, 527, 730, 110, 27, color.red);
}
{
  const s = slide(
    "収集体験の比較から採用した仕組み",
    "6サービス7仕組みの一次資料調査：docs/TROPHY-RESEARCH.md。Geocaching https://www.geocaching.com/blog/2025/02/the-first-treasure-collections-coming-march-17th/ ; Pokémon GO https://scopelyexplore.helpshift.com/hc/en/5-pokemon-go/faq/1095-what-are-collection-challenges/ ; Pikmin Bloom https://scopelyexplore.helpshift.com/hc/en/11-pikmin-bloom/faq/2156-what-are-rare-decor-pikmin/ 。仕様と本PJの面白さの仮説を分離。キャラクターや徽章は複製しない。",
  );
  text(s, "Geocaching", 80, 206, 360, 54, 30, color.red, true);
  text(s, "小さなセットを完成させる", 470, 206, 740, 60, 31, color.ink, true);
  text(s, "Pokémon GO", 80, 321, 360, 54, 30, color.red, true);
  text(s, "未取得でも対象と条件が分かる", 470, 321, 740, 60, 31, color.ink, true);
  text(s, "Pikmin Bloom", 80, 436, 360, 54, 30, color.red, true);
  text(s, "完成後に、好きな収集の続きがある", 470, 436, 740, 60, 31, color.ink, true);
  text(s, "楽しさ・再訪意欲への効果は仮説。利用者との比較評価は未実施。", 80, 583, 1100, 70, 23, color.muted);
}
{
  const s = slide(
    "端末の画面から、ローカルの保存まで",
    "出典：DESIGN.md、Dockerfile、compose.yaml、backend/app。初回の依存取得にはネットワークが必要。通常実行で外部API・DB・素材配信に依存しない。",
  );
  const labels = [
    ["React", "日本語のスマホ画面"],
    ["Python / FastAPI", "判定・権限・時間条件"],
    ["SQLite", "履歴と予定を永続保存"],
  ];
  labels.forEach(([a, b], i) => {
    const x = 78 + i * 386;
    box(s, x, 235, 350, 160, i === 1 ? color.ink : "#E6E8DF");
    text(
      s,
      a,
      x + 22,
      261,
      308,
      52,
      31,
      i === 1 ? color.paper : color.ink,
      true,
    );
    text(s, b, x + 22, 331, 308, 46, 21, i === 1 ? "#CDDAD5" : color.muted);
  });
  text(s, "Dockerで同じ構成を再現", 80, 466, 1110, 60, 34, color.ink, true);
  text(
    s,
    "外部APIなし。履歴はローカル保存。実行権限と公開範囲を制限。",
    80,
    554,
    1100,
    86,
    26,
    color.muted,
  );
}
{
  const s = slide(
    "記録の意味を分けて、破損と水増しを防ぐ",
    "検証根拠：backend/tests、scripts/test_samples.py、docs/EVALUATION.md。候補保存は実再訪の証拠ではない。",
  );
  statement(
    s,
    "01",
    "訪問・挑戦・実績・予定を分離",
    "保存しただけで訪問済みにはしない。",
    192,
  );
  statement(
    s,
    "02",
    "重複と途中失敗に備える",
    "一意制約と一括更新。再送・障害・他人の識別子を試験。",
    356,
  );
  text(s, "提供データも保護", 76, 536, 1100, 46, 29, color.red, true);
  text(
    s,
    "5ファイルを検証。再取込でも件数不変。氏名・連絡先を出力しない。",
    76,
    592,
    1100,
    64,
    25,
    color.muted,
  );
}
{
  const s = slide(
    "評価基準と測定結果",
    "PJ独自の20項目各5点。大会公式点ではない。未検証は0点、重大な安全性問題・データ破損・起動不能は点数によらず提出不可。docs/EVALUATION.md、docs/BENCHMARKS.mdと各試験証拠を参照。採用した要求と項目に限定し、ASVS特定レベル・WCAG AA・CIS全体適合を主張しない。公式一次資料: https://github.com/OWASP/ASVS/tree/v5.0.0/5.0/en ; https://www.w3.org/TR/2024/REC-WCAG22-20241212/ ; https://docs.docker.com/engine/containers/run/ 。",
  );
  text(s, "PJ独自の検証完了率（固定20項目）", 80, 183, 680, 38, 23, color.muted);
  text(s, `${metrics.score} / 100`, 80, 210, 580, 130, 84, color.red, true);
  text(s, "動作と証拠を確認した項目だけを集計", 80, 374, 690, 70, 29, color.ink, true);
  text(
    s,
    `API試験：${metrics.apiTests}\n画面試験：${metrics.browserTests}`,
    80,
    478,
    680,
    120,
    25,
    color.muted,
  );
  text(s, "採用した評価基準", 800, 220, 400, 55, 29, color.ink, true);
  text(
    s,
    "ASVS 5.0.0：入力・権限\nWCAG 2.2：可読性・操作\nDocker公式：権限・保存",
    800,
    312,
    420,
    160,
    24,
    color.muted,
  );
  text(
    s,
    "実際の再訪効果は\n運用後に測定する",
    800,
    503,
    400,
    100,
    28,
    color.ink,
    true,
  );
  text(
    s,
    "大会公式点・規格全面適合・実際の再訪率を示す数値ではありません。",
    80,
    628,
    1080,
    36,
    20,
    color.muted,
  );
}
{
  const s = slide(
    "AI駆動開発の判断と改善履歴",
    "Gitの各リビジョン、docs/CHANGELOG.md、docs/EVALUATION.md、docs/CONTEST-VERIFICATION.md、docs/BENCHMARKS.md、docs/STANDARDS-RESULTS.mdを参照。追加検証中のPJ独自評価は85、75（Q01/Q08の回帰）、85、95、100と推移。別ブラウザーの復旧で失効したセッションと、別タブの更新で古くなったCSRFを区別し、拒否した保存を自動再送せず、画面内の再読込と明示操作で回復することを確認した。旧タブから最初に再復旧する経路も試験した。キーボード動線はTab、Enter、矢印で訪問から保存・手帳確認まで通し、引継ダイアログのEscapeと焦点復帰も確認。誤答1回の期待点数は減点規則に沿って95へ修正した。初期11枚版の検証はAPI33件成功4.72秒、画面15件成功1.5分。画面試験時間には実際の復旧操作上限5回/分に伴う61秒の冷却待ちを含む。これらは実装試験とPJ内の検証完了状況であり、規格の全成功基準や人間の使いやすさを保証しない。大会調査は受領50候補を照合。期間内の資料を確認した49候補はAI開発中心の主対象28件、関連競技21件。受賞作品を確認した40件、募集・開催等まで9件、本文未取得による保留1件。従来10件の詳細な設計採用判断も保持。AI駆動開発の独立した50大会を確認する目標は未達であり、主対象28件を関連競技で水増ししない。公式の受賞表示と選考理由、作者による性能主張を区別し、受賞を保証する因果関係とは主張しない。" + ` 更新版の検証：API試験${metrics.apiTests}、画面試験${metrics.browserTests}。収集棚の条件・段階・目標保持・復旧・キーボード操作と画像配信を追加検証。配色と画像MIMEの指摘を修正し再検証した。更新版の画面試験20件は既存15件、収集4件、画像1件で構成し、待機122秒を含む。作成セッションと復旧の回数制限を弱めず、試験間隔を調整した。`,
  );
  statement(
    s,
    "1",
    "独立した作業とレビュー",
    "画面・データ・環境を分担し、契約と試験で統合する。",
    190,
  );
  statement(
    s,
    "2",
    "評価の差分から修正",
    "不具合を記録し、修正後に同じ条件で再検証する。",
    347,
  );
  text(
    s,
    "変更はGitで保存。発表から実装と証拠をたどれる。",
    80,
    557,
    1110,
    78,
    32,
    color.red,
    true,
  );
}
{
  const s = slide(
    "次の来訪理由を、手元に残す",
    "完成状態と未達はrelease metricsおよびREADMEの記載に従う。架空都市のデモのみでは実際の地域経済効果を証明できない。製品・都市の正式名称、参照CSS、既存APIは未提供または未確認。実地運用と利用者調査は未実施であり、再訪率・地域経済効果を測定済みとは扱わない。" + metrics.status,
  );
  text(s, "次は、冬の水門を解きに。", 80, 221, 1110, 100, 51, color.ink, true);
  text(
    s,
    "次は、会議のない日に海辺へ。",
    80,
    352,
    1110,
    100,
    51,
    color.ink,
    true,
  );
  text(
    s,
    "ソース一式・設計書・操作デモと検証の証拠",
    80,
    530,
    1100,
    64,
    29,
    color.red,
    true,
  );
  text(s, "正式名称・参照CSS・既存APIは未確認。\n実地での再訪効果は、利用者調査と継続運用で測定。", 80, 610, 1050, 70, 19, color.muted);
}
const candidate = path.join(build, "candidate.pptx");
console.log("Exporting PPTX candidate");
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log("PPTX candidate saved");
// Native PNG export exits in the current Windows runtime. PowerPoint renders the validated file.
// Keep the Artifact Tool rendering option for hosts where its rasterizer is available.
for (
  let i = 0;
  i < p.slides.items.length && process.argv.includes("--artifact-render");
  i++
) {
  console.log(`Rendering slide ${i + 1}`);
  const blob = await p.export({
    slide: p.slides.items[i],
    format: "png",
    scale: 1,
  });
  await fs.writeFile(
    path.join(build, `slide-${String(i + 1).padStart(2, "0")}.png`),
    new Uint8Array(await blob.arrayBuffer()),
  );
}
if (process.argv.includes("--render-only")) process.exit(0);
const { finalizePresentation } = await import(
  pathToFileURL(path.join(skill, "container_tools/artifact_tool_utils.mjs"))
    .href
);
const filename =
  process.argv.slice(2).find((arg) => !arg.startsWith("--")) ||
  "tang-you-chi-presentation.pptx";
const result = await finalizePresentation({
  explicitTotalSlideCount: 13,
  workspaceDir: root,
  candidatePath: candidate,
  finalPath: path.join(output, filename),
  pythonExecutable: path.join(runtime, "python/python.exe"),
  integrityValidatorPath: path.join(
    skill,
    "container_tools/inspect_presentation_package_integrity.py",
  ),
  layoutValidatorPath: path.join(
    skill,
    "container_tools/inspect_presentation_layout_geometry.py",
  ),
  layoutArgs: [
    "--expected-slide-size-emu",
    "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
  ],
  fontPolicy: { basis: "design", families: [font] },
  requiredNativeTableOwnerSlides: [],
  requiredNativeChartOwnerSlides: [],
  verifyArtifactToolImport: true,
  receiptPath: path.join(build, `${filename}.validation.json`),
});
console.log(
  JSON.stringify({ slides: p.slides.items.length, output: filename, result }),
);
