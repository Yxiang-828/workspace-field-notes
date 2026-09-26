#!/usr/bin/env node

import { readFile, readdir, stat } from "node:fs/promises";
import { resolve, join, extname } from "node:path";

const root = resolve(process.argv[2] ?? process.cwd());
const ignored = new Set([".git", "node_modules", "dist", "dist-electron", "out", "release"]);
const sourceExts = new Set([".css", ".scss", ".ts", ".tsx", ".js", ".jsx", ".html", ".htm"]);

async function walk(directory, files = []) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (ignored.has(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) await walk(path, files);
    else if (sourceExts.has(extname(entry.name))) files.push(path);
  }
  return files;
}

const findings = { errors: [], warnings: [], checks: [] };
let packageJson;
let staticProject = false;
try {
  packageJson = JSON.parse(await readFile(join(root, "package.json"), "utf8"));
} catch (error) {
  if (error.code === "ENOENT") {
    staticProject = true;
    findings.checks.push("No package.json - static HTML/CSS project; Motion React checks skipped.");
  } else {
    findings.errors.push(`package.json could not be read: ${error.message}`);
  }
}

if (packageJson) {
  const deps = { ...(packageJson.dependencies ?? {}), ...(packageJson.devDependencies ?? {}) };
  const motionPackage = deps.motion ? "motion" : deps["framer-motion"] ? "framer-motion" : null;
  if (!motionPackage) findings.errors.push("Install `motion` (preferred) or `framer-motion`.");
  else findings.checks.push(`Motion dependency found: ${motionPackage}`);
}

let files = [];
try {
  if ((await stat(root)).isDirectory()) files = await walk(root);
} catch (error) {
  findings.errors.push(`Project directory could not be scanned: ${error.message}`);
}

const contents = [];
for (const file of files) contents.push({ file, text: await readFile(file, "utf8") });
const withoutComments = (text) => text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:])\/\/.*$/gm, "$1");
const joined = contents.map(({ text }) => withoutComments(text)).join("\n");

if (!staticProject) {
  if (!/(?:from\s+["'](?:motion\/react|framer-motion)["']|require\(["'](?:motion\/react|framer-motion)["']\))/.test(joined)) {
    findings.errors.push("No Motion React import was found in source files.");
  } else {
    findings.checks.push("Motion React import found.");
  }
}

if (!/(?:@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)|useReducedMotion\s*\()/.test(joined)) {
  findings.errors.push("Add a reduced-motion path with `prefers-reduced-motion` or `useReducedMotion`.");
} else {
  findings.checks.push("Reduced-motion handling found.");
}

if (!/:focus-visible/.test(joined)) {
  findings.warnings.push("No `:focus-visible` style was found.");
} else {
  findings.checks.push("Visible keyboard focus styling found.");
}

for (const { file, text } of contents) {
  const source = withoutComments(text);
  if (/transition\s*:\s*all\b/i.test(source)) findings.warnings.push(`${file}: avoid \`transition: all\`.`);
  if (/scale\s*\(\s*0\s*\)/i.test(source)) findings.warnings.push(`${file}: animate from a nearby visible scale, not scale(0).`);
  if (/\bease-in\b/i.test(source) && !/ease-in-out/i.test(source)) findings.warnings.push(`${file}: avoid ease-in for UI responses.`);
  const longDurations = [...source.matchAll(/(?:duration\s*:\s*|transition-duration\s*:\s*)(\d+(?:\.\d+)?)\s*(ms|s)\b/gi)]
    .filter((match) => (match[2].toLowerCase() === "s" ? Number(match[1]) * 1000 : Number(match[1])) > 300);
  if (longDurations.length) findings.warnings.push(`${file}: review UI durations over 300 ms; reserve them for rare explanatory moments.`);
}

console.log(JSON.stringify({ root, ...findings }, null, 2));
process.exitCode = findings.errors.length ? 1 : 0;
