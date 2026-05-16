// Check for required tools on the user's machine.

import { execa } from 'execa';
import chalk from 'chalk';

async function has(cmd, args = ['--version']) {
  try {
    const r = await execa(cmd, args, { reject: false });
    return r.exitCode === 0;
  } catch {
    return false;
  }
}

export async function checkDocker() {
  if (!(await has('docker'))) {
    return { ok: false, message: 'Docker not found. Install: https://docs.docker.com/get-docker/' };
  }
  // `docker compose` (v2) or legacy `docker-compose`
  const v2 = await has('docker', ['compose', 'version']);
  const v1 = await has('docker-compose');
  if (!v2 && !v1) {
    return { ok: false, message: 'docker compose plugin not found. Upgrade Docker Desktop to v20+.' };
  }
  // Daemon running?
  const info = await execa('docker', ['info'], { reject: false });
  if (info.exitCode !== 0) {
    return { ok: false, message: 'Docker daemon is not running. Start Docker Desktop.' };
  }
  return { ok: true, composeCmd: v2 ? ['docker', ['compose']] : ['docker-compose', []] };
}

export async function checkGit() {
  if (!(await has('git'))) {
    return { ok: false, message: 'git not found. Install: https://git-scm.com/downloads' };
  }
  return { ok: true };
}

export async function runPrereqChecks({ requireGit = false } = {}) {
  const docker = await checkDocker();
  if (!docker.ok) {
    console.error(chalk.red('✗ ') + docker.message);
    process.exit(1);
  }
  if (requireGit) {
    const git = await checkGit();
    if (!git.ok) {
      console.error(chalk.red('✗ ') + git.message);
      process.exit(1);
    }
  }
  return docker; // exposes composeCmd
}
