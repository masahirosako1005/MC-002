/** Build the current local deck from saved UI captures and verified local evidence. */
import fs from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const RUNTIME = process.env.KOU_BUNDLED_RUNTIME || 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1104-2876-0_26.1104.2876.0_x64__3k8sg7r9htsxt/dependencies';
const SKILL = process.env.KOU_PRESENTATIONS_SKILL || 'C:/Users/Jisui_share002/.codex/plugins/cache/openai-primary-runtime/presentations/26.1104.22356/skills/presentations';
process.env.RUNTIME_NODE_MODULES = path.join(RUNTIME, 'node/node_modules');
process.env.RUNTIME_BIN_DIR = path.join(RUNTIME, 'bin/override');
const req = createRequire(path.join(RUNTIME, 'node/node_modules/'));
const { Presentation, PresentationFile } = await import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
const sharp = req('sharp');
const ASSETS = path.join(ROOT, 'presentation/assets/current');
const BUILD = path.join(ROOT, 'artifacts/presentation-current');
const OUTPUT = path.join(ROOT, 'outputs/kou-current-20261110.pptx');
const SIZE = { width: 1280, height: 720 };
const INK = '#332f25', RED = '#9d3b2d', MUTED = '#6f675b';
const FONT = 'Meiryo';
const manifest = [];
const sourceFiles = ['DESIGN.md', 'docs/COMMUNITY-SAMPLE-ANALYSIS.md', 'docs/COMMUNITY-RATIONALE.md',
  'docs/JOURNEY-PROGRAMS-CONTRACT.md', 'docs/DAYTRIP-RANK-V2.md', 'docs/DAYTRIP-ZONE-BENEFITS.md',
  'docs/CITY-ANALYTICS-CONTRACT.md', 'docs/OPERATIONAL-DATA-PACK.md',
  'artifacts/quality/root-layout-final/summary.json', 'artifacts/quality/root-layout-final/tests.log',
  'artifacts/quality/root-layout-final/tests.xml', 'artifacts/video-revisit/v10/operations/recording.json', 'artifacts/omikuji/verification.json'];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

async function asset(name, original, png = false) {
  const input = await fs.readFile(path.join(ROOT, original));
  const output = png ? await sharp(input).png().toBuffer() : input;
  const target = path.join(ASSETS, name);
  await fs.writeFile(target, output);
  manifest.push({ name, original, sourceSha256: sha(input), outputSha256: sha(output), transformation: png ? 'Format conversion only; no content change' : 'Exact copy' });
  return target;
}

function text(slide, value, left, top, width, height, size = 30, options = {}) {
  const box = slide.shapes.add({ geometry: 'textbox', position: { left, top, width, height },
    fill: 'none', line: { fill: 'none', width: 0 } });
  box.text = value;
  box.text.style = { typeface: FONT, fontSize: size, color: INK, wrap: 'square', autoFit: 'none',
    insets: 0, verticalAlignment: 'top', ...options };
  return box;
}
function image(slide, source, left, top, width, height, alt) {
  return slide.images.add({ blob: new Uint8Array(readFileSync(source)),
    contentType: source.endsWith('.png') ? 'image/png' : 'image/jpeg',
    alt, fit: 'contain', position: { left, top, width, height } });
}
function note(slide, sources, explanation = '') {
  slide.speakerNotes.text = `${explanation}\n\n出典（プロジェクト内）:\n${sources.join('\n')}\n更新: 2026-11-10。画面内の人物・施設・実績は来歴を管理した架空初期データ。`;
}
function table(slide, values, left, top, width, height, columns, size = 26) {
  const tab = slide.tables.add({ rows: values.length, columns: values[0].length,
    left, top, width, height, columnWidths: columns, values });
  for (let row = 0; row < values.length; row++) for (let col = 0; col < values[0].length; col++) {
    const cell = tab.getCell(row, col);
    cell.fill = row === 0 ? '#9d3b2d' : row % 2 ? '#fffdf7' : '#f2ede0';
    cell.text.style = { typeface: FONT, fontSize: size, color: row === 0 ? '#ffffff' : INK,
      bold: row === 0, wrap: 'square', autoFit: 'none', verticalAlignment: 'middle', insets: 14 };
  }
  tab.borders.assign({ fill: '#d8d0bf', width: .6, style: 'solid' });
  return tab;
}

async function main() {
  if (await fs.stat(OUTPUT).catch(() => null)) throw new Error('Final deck already exists; preserve it and select a new output in the script.');
  await fs.mkdir(ASSETS, { recursive: true });
  await fs.mkdir(BUILD, { recursive: true });
  const a = {};
  a.paper = await asset('washi-paper.png', 'frontend/public/art/wa/washi-paper-v1.webp', true);
  a.cover = await asset('travel-woodcut.png', 'frontend/public/art/wa/travel-woodcut-v1.png');
  a.home = await asset('visitor-home.jpg', 'artifacts/video-revisit/screens/visitor-home.jpg');
  a.chat = await asset('visitor-chat.jpg', 'artifacts/video-revisit/screens/visitor-chat.jpg');
  a.city = await asset('city-dashboard.jpg', 'artifacts/video-revisit/v10/operations/pc-city-112.jpg');
  a.program = await asset('program-progress.jpg', 'artifacts/video-revisit/v10/operations/phone-open-015.jpg');
  a.rank = await asset('rank-phone.jpg', 'artifacts/video-revisit/screens/06-rank-phone.jpg');
  a.zone = await asset('zone-coupon.jpg', 'artifacts/video-revisit/screens/07-zone-phone.jpg');
  a.fortune = await asset('fortune-result.jpg', 'artifacts/omikuji/visitor-result.jpg');
  a.redeemed = await asset('fortune-redeemed.jpg', 'artifacts/omikuji/provider-after-use.jpg');
  const p = Presentation.create({ slideSize: SIZE });
  function slide(title, source) {
    const s = p.slides.add();
    image(s, a.paper, 0, 0, 1280, 720, '和紙の背景');
    text(s, title, 64, 42, 1150, 72, 44, { bold: true });
    text(s, `${source}  ／  ${p.slides.items.length}`, 64, 679, 1150, 24, 14, { color: MUTED });
    return s;
  }

  let s = slide('講', '現行版 2026-11-10');
  // Editable text remains separate from the existing illustration.
  text(s, '仲間で相談し、\nN西市へ通う旅', 70, 190, 650, 168, 58, { bold: true });
  text(s, 'やりたいことのために集まり、\n少しずつ力を持ち寄る仲間。', 74, 411, 640, 110, 32);
  text(s, '通う目的・開催への協力・距離に応じた特典', 74, 565, 700, 74, 27, { color: RED });
  image(s, a.cover, 795, 135, 425, 495, '旅人と地域を描いた同梱の木版画風イラスト');
  note(s, ['DESIGN.md §§1–3', 'frontend/public/art/wa/travel-woodcut-v1.prompt.txt'],
    '目的地は大阪府内を想定した架空都市N西市。講は協力する仲間を表すアプリの名称。絵は同梱の生成イラストであり、実際の旅行記録ではない。');

  s = slide('企画の根拠と、データの限界', '出典：設計書／サンプル分析／企画の根拠');
  text(s, '500 人', 70, 156, 400, 118, 76, { bold: true, color: RED });
  text(s, '行動記録', 76, 280, 410, 50, 31);
  text(s, '287 人', 70, 385, 400, 118, 76, { bold: true, color: RED });
  text(s, '満足度に回答した人', 76, 508, 430, 56, 31);
  text(s, '設計課題', 570, 167, 600, 60, 34, { bold: true });
  text(s, '次の訪問の目的と、\n一緒に行く人・開催する人を\nどうつなぐか。', 570, 244, 630, 188, 36);
  text(s, '相関は、施策の効果や需要の証明ではない。\n写真・関心・参加意思を記録から推測しない。', 570, 483, 640, 135, 27, { color: MUTED });
  note(s, ['DESIGN.md §8', 'docs/COMMUNITY-SAMPLE-ANALYSIS.md', 'docs/COMMUNITY-RATIONALE.md'],
    '500人と287人は異なる母数。公開・共有への許可や講への需要をデータにない項目から断定しない。再訪の因果効果は未測定。');

  s = slide('利用者・事業者・案内の3役', '出典：設計書 §§3–4／講・案内契約');
  table(s, [['役割', '主な操作', '共有の境界'],
    ['利用者', '投稿・仲間選び・講で相談\n予定と参加を本人が確認', '共有先と持越しを選ぶ'],
    ['事業者', '公開プラン・共有相談\n見積・利用確認・集計', '招待を承諾してから共有'],
    ['案内', '入力条件と登録プランから\n候補・理由・定型応答', '現在はMOC／実AI推論なし']],
    64, 158, 1152, 375, [185, 535, 432], 27);
  text(s, '仲間内の会話・写真は、事業者へ自動共有しない', 72, 565, 1140, 72, 32, { bold: true, color: RED });
  note(s, ['DESIGN.md §§3–4', 'docs/contracts/CIRCLES-CONTRACT.md', 'docs/contracts/AI-MOC-CONTRACT.md'],
    'AIハブという役割をMOCの案内機能で実装。外部API・モデル推論は未使用。相談、見積、割引確保は外部予約や決済の完了を意味しない。');

  s = slide('利用者：仲間と予定を決める', '実画面：保存済みの利用者ホーム・講の会話');
  image(s, a.home, 62, 143, 285, 505, '利用者の日帰り候補画面');
  image(s, a.chat, 377, 143, 285, 505, '承諾した事業者との講の共有会話');
  text(s, '1  写真・日程・料金を比較', 718, 183, 495, 85, 32, { bold: true });
  text(s, '2  講で行き先と共有を決める', 718, 312, 495, 94, 32, { bold: true });
  text(s, '3  承諾した事業者と相談', 718, 454, 495, 88, 32, { bold: true });
  text(s, '相談だけで予約確定にはしない。', 718, 579, 495, 60, 26, { color: MUTED });
  note(s, ['DESIGN.md §4', 'artifacts/video-revisit/screens/visitor-home.jpg', 'artifacts/video-revisit/screens/visitor-chat.jpg'],
    'アプリの保存済み実画面。初期利用者、事業者、会話、価格・日程は機能紹介用の架空データ。仲間の参加承諾と事業者の招待承諾を別管理する。');

  s = slide('事業者：自社とN西市全体を確認', '実操作フレーム：v10 pc-city-112／市集計契約');
  image(s, a.city, 63, 149, 840, 473, 'N西市全体に切り替えた事業者ダッシュボード');
  text(s, '店をまたぐ同じ人を\n重複計上しない', 942, 190, 290, 108, 29, { bold: true });
  text(s, '同日・別店の回遊は\n市への再訪に数えない', 942, 339, 290, 116, 29);
  text(s, '少人数の集計を抑制\n他社の個票は非公開', 942, 493, 290, 111, 29);
  text(s, '画面の人数・推移は架空初期データ。市内の全観光客数や施策の成果ではありません。', 70, 638, 1145, 34, 20, { color: RED });
  note(s, ['docs/CITY-ANALYTICS-CONTRACT.md', 'docs/OPERATIONAL-DATA-PACK.md', 'artifacts/video-revisit/v10/operations/recording.json'],
    '表示母数は登録された事業者確認済み記録。居住地域の現在の共有同意を参照。5人未満等を省略し、未収集を0にしない。期間や更新差分からの完全な匿名性を保証するものではない。');

  s = slide('再訪① 通う旅', '出典：通う旅契約／v10 phone-open-015');
  text(s, '成形 → 絵付け → 受け取り', 70, 165, 805, 85, 40, { bold: true, color: RED });
  text(s, '複数回で一つの目的を進める', 74, 282, 760, 70, 36, { bold: true });
  text(s, '各回の場所・時期・料金を示す。\n別日と工程の順序を守って参加する。\n次に来る目的を、工程として残す。', 74, 385, 760, 176, 31);
  text(s, '予定や登録だけでは達成にしない。', 74, 598, 770, 52, 27, { color: MUTED });
  image(s, a.program, 931, 139, 254, 532, '陶芸3回の工程と確認済みの実施進捗');
  note(s, ['docs/JOURNEY-PROGRAMS-CONTRACT.md', 'artifacts/programs/pytest-final.xml', 'artifacts/video-revisit/v10/operations/phone-open-015.jpg'],
    '専用プランと開催を明示的に紐付け、本人参加、仲間と事業者の確認、別日・順序を検査。取消で進捗を再計算する。画面の7,800円は登録時の参考合計で、予約・決済を完了した金額ではない。');

  s = slide('再訪② 開催を担う先達に加点', '出典：D1ポイント規則／旅階級R2');
  text(s, '参加 100点 ＋ 距離点\n開催の先達は ＋50点', 70, 164, 790, 156, 44, { bold: true, color: RED });
  text(s, '実施確認 → 10の旅階級 → 選べる特典', 74, 350, 790, 85, 31, { bold: true });
  text(s, '同じ人は1日1開催まで。\n金銭特典には事業者の利用確認が必要。\n大先達以上は直近365日の活動で維持。', 74, 458, 790, 145, 29);
  text(s, '開催の「先達」と階級名の「先達」は別。', 74, 623, 790, 35, 24, { color: MUTED });
  image(s, a.rank, 916, 143, 296, 504, '累積点、確認済み開催、維持条件が表示された旅の手帳');
  note(s, ['docs/contracts/DAYTRIP-CONTRACT.md', 'docs/DAYTRIP-RANK-V2.md', 'artifacts/video-revisit/screens/06-rank-phone.jpg'],
    'D1: 100+floor(min(参考往復km,200)/10)+承諾済み先達50。同一参加者1日1回。R2は新客・行者・山伏・先達・大先達・正大先達・前鬼後鬼・別当・大僧正・勧進元。上位維持は365日。自己申告だけの点を割引資格へ使わず、自然な降格で既確保価格を書き換えない。');

  s = slide('再訪③ 20〜40km地域への追加割引', '出典：距離追加割引・有限予算契約');
  text(s, '日帰り圏を、片道20〜40kmと想定', 70, 160, 805, 93, 38, { bold: true, color: RED });
  text(s, '本人が登録した市区町村の参考距離で判定。\n未登録・対象外は基本率を適用。', 74, 290, 800, 116, 30);
  text(s, '事業者が追加率と予算を設定。\n確保・利用分が予算を超える申込は止める。\n未利用取消で枠を戻し、保存済み価格は維持。', 74, 437, 800, 172, 29);
  text(s, '自宅からの実測・確定した交通距離ではない。', 74, 628, 800, 35, 24, { color: MUTED });
  image(s, a.zone, 928, 144, 286, 507, '未登録のため基本率が適用されているクーポン実画面');
  note(s, ['docs/DAYTRIP-ZONE-BENEFITS.md', 'docs/DAYTRIP-ROUTES.md', 'artifacts/zone-benefits/pytest.xml', 'artifacts/video-revisit/screens/07-zone-phone.jpg'],
    '大阪32・吹田24・京都38・神戸40・堺39kmは架空N西市への計画用参考値。追加設定された割合クーポンだけに適用。予算は基本分を含む確保・利用済み割引総額。居住地域の集計共有同意とは別に本人へだけ判定理由を返す。画面は未登録の本人で5%、対象地域の設定は10%。対象外に10%を適用したと示さない。');

  s = slide('実装・検証と、残る指摘', '月くじ追加前の統合測定：root-layout-final／2026-11-10');
  text(s, '363 試験 成功', 70, 152, 570, 98, 56, { bold: true, color: RED });
  text(s, '＋32 subtests（JUnit 395件）', 74, 255, 595, 60, 29);
  text(s, 'React / FastAPI / SQLite\nDockerでローカル動作\n通常起動は外部API・AI推論なし', 74, 367, 590, 156, 29);
  text(s, '判定は review-required\n合計点・満点・認証には換算しない', 74, 571, 590, 83, 27, { bold: true });
  table(s, [['測定項目', '残る指摘'], ['Ruff', '0'], ['Oxlint', '115（前124）'],
    ['Stylelint', '126'], ['複雑度 C901', '14'], ['Bandit', '19 Medium／High 0']],
    705, 150, 510, 435, [250, 260], 24);
  text(s, '測定エラー 0／指摘の新規増加 0', 710, 610, 515, 42, 22, { color: MUTED });
  note(s, ['artifacts/quality/root-layout-final/summary.json', 'artifacts/quality/root-layout-final/tests.log', 'artifacts/quality/root-layout-final/tests.xml', 'docs/DAYTRIP-SECURITY-TRIAGE.md'],
    '363 passed,32 subtests passed(342.66秒)。JUnit395。測定対象には未コミット差分を含み、commit d1bd8f9だけの評価ではない。Bandit19はMedium、High0。静的指摘は未検証の安全性を保証せず、既存だから安全とも扱わない。異種ツールの件数を足して得点化しない。');

  s = slide('追加：現地の月替わりくじ', '追加対象12試験成功／現地コード発行・当選保存・店頭消込を実操作で確認');
  image(s, a.fortune, 80, 145, 205, 430, '月次の正規抽選で保存された100円当選券');
  image(s, a.redeemed, 371, 148, 828, 466, '事業者側で500円の購入確認後に100円券を利用済みにした画面');
  text(s, '無料・月1回／はずれあり／確認済み階級で当たりやすさが変わる', 72, 618, 1140, 38, 24, { bold: true, color: RED });
  text(s, '現地確認は対面コード（GPSではない）。再訪効果・方向センサー実機は未検証。', 72, 654, 1140, 28, 20, { color: MUTED });
  note(s, ['artifacts/omikuji/verification.json', 'artifacts/omikuji/visitor-result.jpg', 'artifacts/omikuji/provider-after-use.jpg', 'artifacts/video-revisit/v11/operations/recording.json'],
    '実装と対象12試験を確認。事業者のコード発行→利用者の箱選択→正規100円当選の保存→500円の購入確認で事業者が消込→利用者の再表示で利用済みをブラウザ確認。画面は架空N西市・初期アカウント。現実の購入や決済を実施したものではない。無料、全事業者共通JST月1回、はずれあり。対面配布10分コードはGPSの証明ではない。対象店のみ30日・換金不可・他割引併用不可、事業者予算内。方向センサーとゴーグルの実機、使いやすさ、実際の再訪、費用対効果は未検証。');

  const sourceHashes = {};
  for (const name of sourceFiles) sourceHashes[name] = sha(await fs.readFile(path.join(ROOT, name)));
  await fs.writeFile(path.join(ASSETS, 'provenance.json'), JSON.stringify({ created: '2026-11-10', assets: manifest }, null, 2));
  const candidate = path.join(BUILD, 'candidate.pptx');
  await (await PresentationFile.exportPptx(p)).save(candidate);
  await fs.writeFile(path.join(BUILD, 'content-manifest.json'), JSON.stringify({ slides: 10, font: FONT, size: SIZE,
    sources: sourceHashes, sourceScriptSha256: sha(await fs.readFile(fileURLToPath(import.meta.url))),
    renderer: 'Artifact Tool; final PNG/PDF inspected through local PowerPoint rendering',
    claims: { measuredRevisitEffect: false, nNishiFictional: true, aiInference: false, monthlyFortuneImplemented: true },
    tests: { passed: 363, subtests: 32 }, qualityPhase: 'root-layout-final' }, null, 2));
  const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')).href);
  const receipt = await finalizePresentation({ workspaceDir: ROOT, candidatePath: candidate, finalPath: OUTPUT,
    explicitTotalSlideCount: 10, requiredNativeTableOwnerSlides: [3, 9], requiredNativeChartOwnerSlides: [],
    pythonExecutable: path.join(RUNTIME, 'python/python.exe'),
    integrityValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_package_integrity.py'),
    layoutValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_layout_geometry.py'),
    layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-heading-fit',
      '--require-native-table-slide', '3', '--require-native-table-slide', '9'],
    fontPolicy: { basis: 'design', families: [FONT] }, verifyArtifactToolImport: true,
    receiptPath: path.join(BUILD, 'validation.json') });
  console.log(JSON.stringify({ output: OUTPUT, slides: 10, receipt }));
}
await main();
