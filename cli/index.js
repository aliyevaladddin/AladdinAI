// NOTICE: This file is protected under RCF-PL
#!/usr/bin/env node

import { Command } from 'commander';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import updateNotifier from 'update-notifier';
import { initCommand } from './commands/init.js';
import {
  upCommand,
  downCommand,
  restartCommand,
  logsCommand,
  updateCommand,
} from './commands/lifecycle.js';
import { doctorCommand } from './commands/doctor.js';
import { runSetupWizard } from './commands/wizard.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pkg = JSON.parse(readFileSync(path.join(__dirname, 'package.json'), 'utf8'));

// Check for updates once per day, show a banner on next run
updateNotifier({ pkg, updateCheckInterval: 1000 * 60 * 60 * 24 }).notify({ defer: false });

const program = new Command();

program
  .name('aladdin-ai')
  .description('Self-hosted AI workspace — agents, memory, CRM, channels.')
  .version(pkg.version);

// ── init (default) ────────────────────────────────────────────────────
program
  .command('init', { isDefault: true })
  .description('Set up a new AladdinAI deployment using prebuilt Docker images')
  .option('-n, --name <name>', 'project directory name')
  .option('-y, --yes', 'accept defaults, skip prompts')
  .option('--skip-start', 'do not run docker compose up after setup')
  .option('--source', 'install from source (git clone + local build, for contributors)')
  .action(initCommand);

// ── lifecycle ─────────────────────────────────────────────────────────
program
  .command('up')
  .description('Start services (docker compose up -d)')
  .option('--build', 'rebuild images before starting')
  .action(upCommand);

program
  .command('down')
  .description('Stop services')
  .option('-v, --volumes', 'also remove volumes (DESTROYS data)')
  .action(downCommand);

program
  .command('restart [service]')
  .description('Restart all services or a specific one (backend, frontend, postgres)')
  .action(restartCommand);

program
  .command('logs [service]')
  .description('Tail service logs (defaults to all)')
  .option('-f, --follow', 'follow log output')
  .option('-t, --tail <lines>', 'number of lines to show from the end', '100')
  .action(logsCommand);

program
  .command('update')
  .description('Pull the latest images and recreate services')
  .action(updateCommand);

// ── diagnostics ───────────────────────────────────────────────────────
program
  .command('doctor')
  .description('Diagnose setup issues: docker, .env, ports, services')
  .action(doctorCommand);

program
  .command('setup')
  .description('Run configuration wizard to set up providers and agents')
  .action(async () => {
    const cwd = process.cwd();
    await runSetupWizard(cwd);
  });

program.parseAsync(process.argv).catch((err) => {
  console.error(err.shortMessage || err.message);
  process.exit(1);
});
