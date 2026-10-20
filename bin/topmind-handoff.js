#!/usr/bin/env node
/**
 * Install or update the topmind-handoff skill directory.
 *
 *   npx @topmindspace/topmind-handoff install
 *   npx @topmindspace/topmind-handoff update
 *   npx @topmindspace/topmind-handoff install --to ~/.claude/skills
 *
 * The copy lands in <skills>/<name>/ so the host can see SKILL.md.
 * A same version is left as it is. An older copy is replaced in place.
 * A newer local copy is left as it is unless --force is set.
 * Nothing is uploaded. No backup directory is kept beside the skill.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const SKILL_ID = 'topmind-handoff';
const FILES = ['SKILL.md', 'README.md', 'LICENSE', 'CHANGELOG.md', 'package.json'];
const DIRS = ['references', 'assets', 'examples', 'topmind_handoff'];
const NESTED = ['scripts/compile_memory.py'];

function die(msg, code = 1) {
  console.error(msg);
  process.exit(code);
}

function readJsonVersion(dir) {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8'));
    return String(pkg.version || '');
  } catch {
    return '';
  }
}

function readSkillVersion(dir) {
  try {
    const text = fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8');
    const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!fm) return '';
    const meta = fm[1].match(/^[ \t]+version:\s*["']?([^"'\n]+)["']?\s*$/m);
    const top = fm[1].match(/^version:\s*["']?([^"'\n]+)["']?\s*$/m);
    return (meta || top || [])[1] ? String((meta || top)[1]).trim() : '';
  } catch {
    return '';
  }
}

function readSkillName(dir) {
  try {
    const text = fs.readFileSync(path.join(dir, 'SKILL.md'), 'utf8');
    const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!fm) return '';
    const name = fm[1].match(/^name:\s*["']?([^"'\n]+)["']?\s*$/m);
    return name ? name[1].trim() : '';
  } catch {
    return '';
  }
}

function packageVersion() {
  return readSkillVersion(ROOT) || readJsonVersion(ROOT);
}

/** Negative when a < b, 0 when equal, positive when a > b. null when either side is not x.y.z. */
function cmpVer(a, b) {
  const parse = (v) => {
    const parts = String(v || '').trim().split('.');
    if (!parts.length || parts.some((n) => !/^\d+$/.test(n))) return null;
    return parts.map((n) => Number(n));
  };
  const pa = parse(a);
  const pb = parse(b);
  if (!pa || !pb) return null;
  const n = Math.max(pa.length, pb.length);
  for (let i = 0; i < n; i++) {
    const da = pa[i] || 0;
    const db = pb[i] || 0;
    if (da !== db) return da > db ? 1 : -1;
  }
  return 0;
}

/**
 * exists false → install.
 * missing or older installed version → upgrade.
 * same → current.
 * installed newer → refuse, or force when the user asked.
 */
function decide(installed, incoming, { exists, force }) {
  if (!exists) return 'install';
  const cmp = cmpVer(installed, incoming);
  if (cmp === null || cmp < 0) return 'upgrade';
  if (cmp === 0) return 'current';
  return force ? 'force' : 'refuse';
}

function globalSkillRoots(home) {
  const base = home || os.homedir();
  return [
    path.join(base, '.agents', 'skills'),
    path.join(base, '.claude', 'skills'),
    path.join(base, '.codex', 'skills'),
    path.join(base, '.cursor', 'skills'),
  ];
}

function normPath(p) {
  const s = path.resolve(p);
  return process.platform === 'win32' ? s.toLowerCase() : s;
}

function realOrResolved(p) {
  let cur = path.resolve(p);
  const tail = [];
  for (;;) {
    try {
      return path.join(fs.realpathSync(cur), ...tail);
    } catch {
      const parent = path.dirname(cur);
      if (parent === cur) return path.join(cur, ...tail);
      tail.unshift(path.basename(cur));
      cur = parent;
    }
  }
}

function assertDestOutsideSource(dest) {
  const src = normPath(realOrResolved(ROOT));
  const abs = normPath(realOrResolved(dest));
  if (abs === src || abs.startsWith(src + path.sep) || src.startsWith(abs + path.sep)) {
    die(
      `Refusing to install into the package directory.\n  package: ${src}\n  destination: ${abs}`
    );
  }
}

function skipEntry(name) {
  return name === '__pycache__' || name === 'node_modules' || name.endsWith('.pyc');
}

function copyFile(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (skipEntry(entry.name)) continue;
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(from, to);
    else if (entry.isFile()) copyFile(from, to);
  }
}

function copyPayload(dest) {
  for (const name of FILES) {
    const src = path.join(ROOT, name);
    if (!fs.existsSync(src)) die(`Package is missing ${name}`);
    copyFile(src, path.join(dest, name));
  }
  for (const name of DIRS) {
    const src = path.join(ROOT, name);
    if (!fs.existsSync(src)) die(`Package is missing ${name}/`);
    copyDir(src, path.join(dest, name));
  }
  for (const rel of NESTED) {
    const src = path.join(ROOT, rel);
    if (!fs.existsSync(src)) die(`Package is missing ${rel}`);
    copyFile(src, path.join(dest, rel));
  }
}

function placePayload(dest) {
  const stage = fs.mkdtempSync(path.join(os.tmpdir(), 'topmind-handoff-'));
  try {
    copyPayload(stage);
    fs.rmSync(dest, { recursive: true, force: true });
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    copyDir(stage, dest);
  } finally {
    fs.rmSync(stage, { recursive: true, force: true });
  }
}

function skillDest(root) {
  return path.join(path.resolve(root), SKILL_ID);
}

function applyOne(skillsRoot, { force }) {
  const dest = skillDest(skillsRoot);
  assertDestOutsideSource(dest);
  const exists = fs.existsSync(dest);
  if (exists) {
    if (!fs.statSync(dest).isDirectory() || readSkillName(dest) !== SKILL_ID) {
      die(`Refusing to replace ${dest}\n  it is not an installed ${SKILL_ID} skill.`);
    }
  }
  const incoming = packageVersion();
  if (!incoming) die('This package has no version in SKILL.md or package.json.');
  const installed = exists ? readSkillVersion(dest) || readJsonVersion(dest) : '';
  const action = decide(installed, incoming, { exists, force });
  if (action === 'current') {
    console.log(`Already up to date: ${SKILL_ID} ${incoming}`);
    console.log(`  at: ${dest}`);
    return;
  }
  if (action === 'refuse') {
    console.error(
      `Refusing to downgrade ${SKILL_ID} ${installed} to ${incoming}. Pass --force to overwrite.\n  at: ${dest}`
    );
    return 1;
  }
  fs.mkdirSync(skillsRoot, { recursive: true });
  placePayload(dest);
  if (action === 'install') {
    console.log(`Installed ${SKILL_ID} ${incoming}`);
  } else if (action === 'force') {
    console.log(`Downgraded ${SKILL_ID} ${installed || 'unknown'} -> ${incoming}`);
  } else {
    console.log(`Upgraded ${SKILL_ID} ${installed || 'unknown'} -> ${incoming}`);
  }
  console.log(`  at: ${dest}`);
  return 0;
}

function installedRoots(home) {
  return globalSkillRoots(home).filter((root) => {
    const dest = skillDest(root);
    return fs.existsSync(path.join(dest, 'SKILL.md')) && readSkillName(dest) === SKILL_ID;
  });
}

function usageText() {
  return `topmind-handoff — install this skill into an agent skills directory

Usage:
  topmind-handoff install [--to <dir>] [--force]
  topmind-handoff update [--to <dir>] [--force]
  topmind-handoff help

install   copies the skill to <dir>/${SKILL_ID}/.
          Default <dir> is ~/.agents/skills (created when missing).
update    refreshes a copy that is already there.
          With no --to, each of these that already has the skill:
          ~/.agents/skills  ~/.claude/skills  ~/.codex/skills  ~/.cursor/skills

Same version prints:  Already up to date: ${SKILL_ID} <version>
Older copy prints:    Upgraded ${SKILL_ID} <old> -> <new>
Newer local copy stays, unless --force. No backup directory is left behind.

Examples:
  npx @topmindspace/topmind-handoff@latest install
  npx @topmindspace/topmind-handoff@latest update
  npx @topmindspace/topmind-handoff@latest install --to ~/.claude/skills
  npx @topmindspace/topmind-handoff@latest install --to ~/.codex/skills
  npx @topmindspace/topmind-handoff@latest install --to ~/.cursor/skills

The installer only copies files. It does not phone home.
`;
}

function parseFlags(args) {
  let to = null;
  let force = false;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--to' || args[i] === '-t') {
      to = args[++i];
      if (!to) die('Option --to requires a directory path.');
    } else if (args[i] === '--force' || args[i] === '-f') {
      force = true;
    } else {
      die(`Unknown option: ${args[i]}\n\n${usageText()}`);
    }
  }
  return { to, force };
}

function main(argv, home) {
  const args = argv.slice(2);
  const cmd = args[0];
  if (!cmd || cmd === 'help' || cmd === '--help' || cmd === '-h') {
    console.log(usageText());
    return;
  }
  if (cmd !== 'install' && cmd !== 'update') die(`Unknown command: ${cmd}\n\n${usageText()}`);
  const flags = parseFlags(args.slice(1));
  if (cmd === 'install') {
    const root = flags.to
      ? path.resolve(flags.to)
      : path.join(home || os.homedir(), '.agents', 'skills');
    const code = applyOne(root, flags);
    if (code) process.exit(code);
    return;
  }
  const roots = flags.to ? [path.resolve(flags.to)] : installedRoots(home);
  if (!roots.length) {
    die(
      `No installed copy found.\nInstall with:\n  npx @topmindspace/${SKILL_ID}@latest install\n  npx @topmindspace/${SKILL_ID}@latest install --to ~/.claude/skills`
    );
  }
  let failed = 0;
  for (const root of roots) {
    const code = applyOne(root, flags);
    if (code) failed = code;
  }
  if (failed) process.exit(failed);
}

if (require.main === module) {
  main(process.argv, process.env.HOME || os.homedir());
}

module.exports = {
  cmpVer,
  decide,
  main,
  packageVersion,
  SKILL_ID,
};
