'use strict';

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const test = require('node:test');

const ROOT = path.resolve(__dirname, '..');
const BIN = path.join(ROOT, 'bin', 'topmind-handoff.js');
const { cmpVer, decide, packageVersion } = require(BIN);

function tempHome() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'handoff-home-'));
}

function run(args, home) {
  return spawnSync(process.execPath, [BIN, ...args], {
    encoding: 'utf8',
    cwd: ROOT,
    env: { ...process.env, HOME: home },
  });
}

function writeInstalled(dir, version) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, 'SKILL.md'),
    `---\nname: topmind-handoff\nmetadata:\n  version: "${version}"\n---\n\n# old\n`,
    'utf8'
  );
  fs.writeFileSync(path.join(dir, 'kept-note.txt'), 'local extra\n', 'utf8');
}

test('version order', () => {
  assert.equal(cmpVer('0.6.5', '0.7.0'), -1);
  assert.equal(cmpVer('0.7.0', '0.7.0'), 0);
  assert.equal(cmpVer('0.8.0', '0.7.0'), 1);
  assert.equal(cmpVer('unknown', '0.7.0'), null);
  assert.equal(decide('', '0.7.0', { exists: false, force: false }), 'install');
  assert.equal(decide('0.6.5', '0.7.0', { exists: true, force: false }), 'upgrade');
  assert.equal(decide('0.7.0', '0.7.0', { exists: true, force: false }), 'current');
  assert.equal(decide('unknown', '0.7.0', { exists: true, force: false }), 'upgrade');
  assert.equal(decide('9.0.0', '0.7.0', { exists: true, force: false }), 'refuse');
  assert.equal(decide('9.0.0', '0.7.0', { exists: true, force: true }), 'force');
});

test('install copies the skill and a second run stays current', () => {
  const home = tempHome();
  const dest = path.join(home, '.agents', 'skills', 'topmind-handoff');
  const first = run(['install'], home);
  assert.equal(first.status, 0, first.stderr);
  assert.match(first.stdout, new RegExp(`Installed topmind-handoff ${packageVersion()}`));
  assert.equal(fs.existsSync(path.join(dest, 'SKILL.md')), true);
  assert.equal(fs.existsSync(path.join(dest, 'scripts', 'compile_memory.py')), true);
  assert.equal(fs.existsSync(path.join(dest, 'examples', 'README.md')), true);
  assert.equal(fs.existsSync(path.join(dest, 'topmind_handoff', 'cli.py')), true);
  assert.equal(fs.existsSync(path.join(dest, 'tests')), false);
  assert.equal(fs.existsSync(path.join(dest, 'bin')), false);
  const again = run(['install'], home);
  assert.equal(again.status, 0, again.stderr);
  assert.match(again.stdout, new RegExp(`Already up to date: topmind-handoff ${packageVersion()}`));
});

test('update upgrades an older copy and refuses a newer one', () => {
  const home = tempHome();
  const agents = path.join(home, '.agents', 'skills', 'topmind-handoff');
  const claude = path.join(home, '.claude', 'skills', 'topmind-handoff');
  writeInstalled(agents, '0.0.1');
  writeInstalled(claude, '9.0.0');
  const sibling = path.join(home, '.agents', 'skills', 'other-skill', 'SKILL.md');
  fs.mkdirSync(path.dirname(sibling), { recursive: true });
  fs.writeFileSync(sibling, '---\nname: other-skill\n---\n', 'utf8');

  const result = run(['update'], home);
  assert.equal(result.status, 1);
  assert.match(result.stdout, /Upgraded topmind-handoff 0\.0\.1 -> /);
  assert.match(result.stderr, /Refusing to downgrade topmind-handoff 9\.0\.0/);
  assert.equal(fs.readFileSync(path.join(claude, 'SKILL.md'), 'utf8').includes('9.0.0'), true);
  assert.equal(fs.existsSync(path.join(agents, 'kept-note.txt')), false);
  assert.equal(fs.existsSync(path.join(agents, 'scripts', 'compile_memory.py')), true);
  assert.equal(fs.existsSync(path.join(path.dirname(agents), 'topmind-handoff.bak')), false);
  assert.match(fs.readFileSync(sibling, 'utf8'), /other-skill/);
});

test('update with no copy tells the user to install', () => {
  const home = tempHome();
  const result = run(['update'], home);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /No installed copy found/);
});

test('refuses a destination inside the package', () => {
  const home = tempHome();
  const result = run(['install', '--to', path.join(ROOT, 'tests')], home);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Refusing to install into the package directory/);
});

test('--to installs into that skills directory', () => {
  const home = tempHome();
  const root = path.join(home, 'custom-skills');
  const result = run(['install', '--to', root], home);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(fs.existsSync(path.join(root, 'topmind-handoff', 'SKILL.md')), true);
  assert.equal(fs.existsSync(path.join(home, '.agents', 'skills')), false);
});
