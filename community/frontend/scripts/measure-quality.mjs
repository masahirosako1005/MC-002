import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const phase = process.argv[2] || "current";
if (!/^[a-z0-9-]+$/.test(phase)) throw new Error("Invalid measurement name");
const evidence = resolve(root, "../artifacts/frontend-quality");
mkdirSync(evidence, { recursive: true });
const image = "node:24-alpine@sha256:a34ab6d7f6f4813f4d0c5469d74685604b962fbdbf5793a7bc7b4998ecb867c8";
const runtime = resolve(evidence, "tool-runtime");
const files = readdirSync(resolve(root, "src"), { recursive: true })
  .filter((name) => /\.(?:tsx?|css)$/.test(name))
  .sort();
const hashes = Object.fromEntries(files.map((name) => [name.replaceAll("\\", "/"), createHash("sha256").update(readFileSync(resolve(root, "src", name))).digest("hex")]));
const commands = [
  ["oxlint", "docker", ["run", "--rm", "--network", "none", "--cpus", "1", "--memory", "512m",
    "--env", "PATH=/tools/node_modules/.bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    "--env", "NODE_PATH=/tools/node_modules",
    "--mount", `type=bind,source=${root},target=/work,readonly`,
    "--mount", `type=bind,source=${runtime},target=/tools,readonly`,
    "-w", "/work", image, "node", "/tools/node_modules/oxlint/bin/oxlint",
    "--threads", "1", "--no-ignore", "--type-aware", "--deny-warnings", "--format", "json", "src"]],
  ["stylelint", process.execPath, ["node_modules/stylelint/bin/stylelint.mjs", "src/**/*.css", "--formatter", "json", "--max-warnings", "0"]],
  ["tsc", process.execPath, ["node_modules/typescript/bin/tsc", "--noEmit", "--pretty", "false"]],
];
const results = {};
for (const [name, executable, args] of commands) {
  const started = performance.now();
  const run = spawnSync(executable, args, { cwd: root, encoding: "utf8", maxBuffer: 12 * 1024 * 1024, timeout: 120000 });
  const jsonOnStderr = name === "stylelint" && run.stderr?.trimStart().startsWith("[");
  writeFileSync(resolve(evidence, `${phase}-${name}.${name === "tsc" ? "txt" : "json"}`), (jsonOnStderr ? run.stderr : run.stdout) || "");
  writeFileSync(resolve(evidence, `${phase}-${name}-stderr.txt`), (jsonOnStderr ? "" : run.stderr) || String(run.error || ""));
  results[name] = { exit: run.status, milliseconds: Math.round(performance.now() - started) };
  console.log(`${name}: exit ${run.status}`);
}
writeFileSync(resolve(evidence, `${phase}-manifest.json`), JSON.stringify({ phase, image, scope: relative(resolve(root, "../.."), resolve(root, "src")), files: hashes, configs: Object.fromEntries([".oxlintrc.json", ".stylelintrc.json", "tsconfig.json"].map((name) => [name, createHash("sha256").update(readFileSync(resolve(root, name))).digest("hex")])), results }, null, 2) + "\n");
process.exitCode = Object.values(results).some((result) => result.exit !== 0) ? 1 : 0;
