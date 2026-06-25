// NOTICE: This file is protected under RCF-PL
// `aladdin-ai up | down | restart | logs` — docker compose wrappers.

import chalk from 'chalk';
import { compose } from '../lib/compose.js';

// [RCF:PROTECTED]
export async function upCommand(opts) {
  console.log(chalk.cyan('Starting AladdinAI services…\n'));
  const args = ['up', '-d'];
  if (opts.build) args.push('--build');
  const r = await compose(args);
  if (r.exitCode !== 0) process.exit(r.exitCode || 1);
  console.log(chalk.green('\n✓ Services started'));
  console.log('  Frontend: ' + chalk.cyan('http://localhost:3000'));
  console.log('  Backend:  ' + chalk.cyan('http://localhost:8000/api/docs'));
}

// [RCF:PROTECTED]
export async function downCommand(opts) {
  console.log(chalk.cyan('Stopping AladdinAI services…\n'));
  const args = ['down'];
  if (opts.volumes) args.push('-v');
  const r = await compose(args);
  process.exit(r.exitCode || 0);
}

// [RCF:PROTECTED]
export async function restartCommand(service) {
  console.log(chalk.cyan(`Restarting ${service || 'all services'}…\n`));
  const args = ['restart'];
  if (service) args.push(service);
  const r = await compose(args);
  process.exit(r.exitCode || 0);
}

// [RCF:PROTECTED]
export async function logsCommand(service, opts) {
  const args = ['logs'];
  if (opts.follow) args.push('-f');
  if (opts.tail) args.push('--tail', String(opts.tail));
  if (service) args.push(service);
  const r = await compose(args);
  process.exit(r.exitCode || 0);
}

// [RCF:PROTECTED]
export async function updateCommand() {
  console.log(chalk.cyan('Pulling latest images…\n'));
  let r = await compose(['pull']);
  if (r.exitCode !== 0) process.exit(r.exitCode || 1);
  console.log(chalk.cyan('\nRecreating services with new images…\n'));
  r = await compose(['up', '-d']);
  if (r.exitCode !== 0) process.exit(r.exitCode || 1);
  console.log(chalk.green('\n✓ Updated and running'));
}
