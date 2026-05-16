// Thin wrapper for invoking `docker compose` from any subcommand.

import { execa } from 'execa';
import { checkDocker } from './prereq.js';
import { requireProjectRoot } from './project.js';
import chalk from 'chalk';

export async function compose(args, { cwd, stdio = 'inherit' } = {}) {
  const root = cwd || requireProjectRoot();
  const docker = await checkDocker();
  if (!docker.ok) {
    console.error(chalk.red('✗ ') + docker.message);
    process.exit(1);
  }
  const [bin, prefix] = docker.composeCmd;
  return execa(bin, [...prefix, ...args], { cwd: root, stdio, reject: false });
}
