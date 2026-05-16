// `aladdin-ai doctor` — diagnose common setup issues.

import chalk from 'chalk';
import fs from 'fs-extra';
import net from 'node:net';
import path from 'path';
import { execa } from 'execa';
import { findProjectRoot } from '../lib/project.js';
import { checkDocker, checkGit } from '../lib/prereq.js';

const ok = (msg) => console.log(chalk.green('  ✓ ') + msg);
const bad = (msg, hint) => {
  console.log(chalk.red('  ✗ ') + msg);
  if (hint) console.log(chalk.dim('    → ' + hint));
};
const warn = (msg, hint) => {
  console.log(chalk.yellow('  ! ') + msg);
  if (hint) console.log(chalk.dim('    → ' + hint));
};

// Probe whether anything is listening on a port (true = something is there).
// We try to connect rather than bind because Docker port mappings show up
// from the host as connectable TCP endpoints.
async function isPortInUse(port) {
  return new Promise((resolve) => {
    const sock = new net.Socket();
    const done = (val) => { sock.destroy(); resolve(val); };
    sock.setTimeout(500);
    sock.once('connect', () => done(true));
    sock.once('timeout', () => done(false));
    sock.once('error', () => done(false));
    sock.connect(port, '127.0.0.1');
  });
}

async function fetchWithTimeout(url, ms = 3000) {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctl.signal });
    return r;
  } catch {
    return null;
  } finally {
    clearTimeout(t);
  }
}

export async function doctorCommand() {
  let failures = 0;
  console.log(chalk.cyan('\nAladdinAI doctor\n'));

  // ── Tooling ──────────────────────────────────────────────────────
  console.log(chalk.bold('Tooling'));
  const git = await checkGit();
  git.ok ? ok('git installed') : (bad('git missing', 'install: https://git-scm.com/downloads'), failures++);

  const docker = await checkDocker();
  if (docker.ok) {
    ok('docker + compose available, daemon running');
  } else {
    bad('docker not ready', docker.message);
    failures++;
    // Without docker we can't go further on services
    console.log(chalk.red('\nFix Docker first; re-run `npx aladdin-ai doctor`.'));
    process.exit(1);
  }

  // ── Project ──────────────────────────────────────────────────────
  console.log(chalk.bold('\nProject'));
  const root = findProjectRoot();
  if (!root) {
    warn('not inside an AladdinAI project',
      'run `npx aladdin-ai init` or cd into the project directory');
    console.log(chalk.dim('\nSkipping project-level checks.\n'));
    process.exit(failures > 0 ? 1 : 0);
  }
  ok(`project root: ${root}`);

  const envPath = path.join(root, '.env');
  if (!fs.existsSync(envPath)) {
    bad('.env missing', 'copy .env.example to .env and fill in secrets');
    failures++;
  } else {
    const env = await fs.readFile(envPath, 'utf8');
    const need = ['JWT_SECRET', 'FERNET_KEY', 'POSTGRES_PASSWORD'];
    const placeholders = [
      ['JWT_SECRET', 'change-me-in-production'],
      ['POSTGRES_PASSWORD', 'replace_with_secure_password'],
      ['FERNET_KEY', 'your-secret-fernet-key-here'],
    ];
    let envOk = true;
    for (const k of need) {
      if (!new RegExp(`^${k}=\\S`, 'm').test(env)) {
        bad(`.env missing ${k}`);
        envOk = false;
        failures++;
      }
    }
    for (const [k, bad_val] of placeholders) {
      if (new RegExp(`^${k}=${bad_val.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}\\s*$`, 'm').test(env)) {
        warn(`.env: ${k} still uses the default placeholder`,
          'generate a real value before exposing this instance');
      }
    }
    if (envOk) ok('.env has required keys');
  }

  // ── Ports ────────────────────────────────────────────────────────
  console.log(chalk.bold('\nPorts'));
  for (const [port, label] of [[3000, 'frontend'], [8000, 'backend'], [5432, 'postgres']]) {
    const inUse = await isPortInUse(port);
    if (inUse) {
      ok(`port ${port} (${label}) listening`);
    } else {
      warn(`port ${port} (${label}) nothing listening`,
        'service may not be running — try `npx aladdin-ai up`');
    }
  }

  // ── Compose services ─────────────────────────────────────────────
  console.log(chalk.bold('\nServices'));
  const [bin, prefix] = docker.composeCmd;
  const psRes = await execa(bin, [...prefix, 'ps', '--format', 'json'], {
    cwd: root,
    reject: false,
  });
  if (psRes.exitCode !== 0) {
    bad('docker compose ps failed', psRes.stderr?.slice(0, 200));
    failures++;
  } else {
    const lines = psRes.stdout.split('\n').filter(Boolean);
    if (lines.length === 0) {
      warn('no compose services running', 'run `npx aladdin-ai up`');
    } else {
      for (const line of lines) {
        try {
          const svc = JSON.parse(line);
          const name = svc.Service || svc.Name;
          const state = svc.State || svc.Status;
          if (state === 'running' || /Up/.test(state || '')) ok(`${name}: ${state}`);
          else { bad(`${name}: ${state}`); failures++; }
        } catch {
          // ignore malformed line
        }
      }
    }
  }

  // ── HTTP reachability ────────────────────────────────────────────
  console.log(chalk.bold('\nReachability'));
  const beRes = await fetchWithTimeout('http://localhost:8000/');
  if (beRes && beRes.status < 500) ok(`backend responding on http://localhost:8000 (HTTP ${beRes.status})`);
  else { warn('backend not responding on :8000', 'check `npx aladdin-ai logs backend`'); }

  const feRes = await fetchWithTimeout('http://localhost:3000');
  if (feRes && feRes.status < 500) {
    ok(`frontend responding on http://localhost:3000 (HTTP ${feRes.status})`);
  } else {
    warn('frontend not responding on :3000', 'check `npx aladdin-ai logs frontend`');
  }

  // ── Summary ──────────────────────────────────────────────────────
  console.log();
  if (failures === 0) {
    console.log(chalk.green('All critical checks passed.\n'));
    process.exit(0);
  } else {
    console.log(chalk.red(`${failures} issue${failures === 1 ? '' : 's'} found.\n`));
    process.exit(1);
  }
}
