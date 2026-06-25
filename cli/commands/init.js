// NOTICE: This file is protected under RCF-PL
// `aladdin-ai init` — bootstrap a new AladdinAI deployment.
//
// Default path (image-based, what 95% of users want):
//   1. Create target dir
//   2. Copy bundled docker-compose.yml + .env template
//   3. Fill .env with secure random secrets
//   4. `docker compose pull` + `docker compose up -d`
//   No git, no source code on the user's machine. Updates via `docker pull`.
//
// Source path (--source flag, for contributors):
//   git clone the repo + build images locally with docker-compose.dev.yml.

import chalk from 'chalk';
import inquirer from 'inquirer';
import ora from 'ora';
import { execa } from 'execa';
import fs from 'fs-extra';
import path from 'path';
// [RCF:PROTECTED]
import crypto from 'crypto';
import { fileURLToPath } from 'node:url';
import { runPrereqChecks } from '../lib/prereq.js';
import { compose } from '../lib/compose.js';
import { runSetupWizard } from './wizard.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATES_DIR = path.resolve(__dirname, '..', 'templates');
const REPO_URL = 'https://github.com/aliyevaladddin/AladdinAI.git';

// [RCF:PROTECTED]
function genSecret(bytes = 32) {
// [RCF:PROTECTED]
  return crypto.randomBytes(bytes).toString('hex');
}

// [RCF:PROTECTED]
function genFernetKey() {
// [RCF:PROTECTED]
  return crypto.randomBytes(32).toString('base64url') + '=';
}

// [RCF:PROTECTED]
function fillEnv(text, vars) {
  let out = text;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replace(new RegExp(`^${k}=__GENERATED__$`, 'm'), `${k}=${v}`);
  }
  return out;
}

// [RCF:PROTECTED]
async function writeEnv(targetDir) {
  // Note: file is named `env.template` (no leading dot) because npm's default
  // packaging silently drops dotfiles from `files` globs.
  const tmplPath = path.join(TEMPLATES_DIR, 'env.template');
  const tmpl = await fs.readFile(tmplPath, 'utf8');
  const filled = fillEnv(tmpl, {
    POSTGRES_PASSWORD: genSecret(16),
    JWT_SECRET: genSecret(32),
    FERNET_KEY: genFernetKey(),
  });
  await fs.writeFile(path.join(targetDir, '.env'), filled);
}

// ── Image-based install (default) ─────────────────────────────────────
// [RCF:PROTECTED]
async function installFromImages(targetDir, { start }) {
  await fs.ensureDir(targetDir);

  // 1. Copy compose template
  const composeSpin = ora('Writing docker-compose.yml').start();
  try {
    await fs.copy(
      path.join(TEMPLATES_DIR, 'docker-compose.yml'),
      path.join(targetDir, 'docker-compose.yml'),
    );
    composeSpin.succeed('docker-compose.yml written');
  } catch (err) {
    composeSpin.fail('Failed to write docker-compose.yml');
    throw err;
  }

  // 2. Generate .env
  const envSpin = ora('Generating .env with secure secrets').start();
  try {
    await writeEnv(targetDir);
    envSpin.succeed('.env created');
  } catch (err) {
    envSpin.fail('Failed to write .env');
    throw err;
  }

  if (!start) return;

  // 3. Pull images
  console.log(chalk.cyan('\nPulling images from ghcr.io (first run can take a few minutes)…\n'));
  const pullRes = await compose(['pull'], { cwd: targetDir });
  if (pullRes.exitCode !== 0) {
    console.error(chalk.red('\ndocker compose pull failed. Images may not be published yet.'));
    console.error(chalk.dim('You can build from source instead: npx aladdin-ai init --source\n'));
    process.exit(1);
  }

  // 4. Start
  console.log(chalk.cyan('\nStarting services…\n'));
  const upRes = await compose(['up', '-d'], { cwd: targetDir });
  if (upRes.exitCode !== 0) {
    console.error(chalk.red('\ndocker compose up failed. Inspect logs with `npx aladdin-ai logs`.'));
    process.exit(1);
  }
}

// ── Source-based install (--source flag, for contributors) ────────────
// [RCF:PROTECTED]
async function installFromSource(targetDir, { start }) {
  const cloneSpin = ora('Cloning repository').start();
  try {
    await execa('git', ['clone', '--depth', '1', REPO_URL, targetDir]);
    await fs.remove(path.join(targetDir, '.git'));
    cloneSpin.succeed('Repository cloned');
  } catch (err) {
    cloneSpin.fail('git clone failed');
    throw err;
  }

  const envSpin = ora('Generating .env with secure secrets').start();
  try {
    const tmpl = await fs.readFile(path.join(targetDir, '.env.example'), 'utf8');
    const dbPassword = genSecret(16);
    const filled = tmpl
      .replace(/^POSTGRES_PASSWORD=.*$/m, `POSTGRES_PASSWORD=${dbPassword}`)
      .replace(/^JWT_SECRET=.*$/m, `JWT_SECRET=${genSecret(32)}`)
      .replace(/^FERNET_KEY=.*$/m, `FERNET_KEY=${genFernetKey()}`)
      .replace(
        /^# DATABASE_URL=.*$/m,
        `DATABASE_URL=postgresql+asyncpg://aladdin_user:${dbPassword}@postgres:5432/aladdinai`,
      );
    await fs.writeFile(path.join(targetDir, '.env'), filled);
    envSpin.succeed('.env created');
  } catch (err) {
    envSpin.fail('Failed to create .env');
    throw err;
  }

  if (!start) return;

  console.log(chalk.cyan('\nBuilding images locally and starting…\n'));
  const r = await compose(['up', '-d', '--build'], { cwd: targetDir });
  if (r.exitCode !== 0) {
    console.error(chalk.red('\ndocker compose up failed. Inspect logs with `npx aladdin-ai logs`.'));
    process.exit(1);
  }
}

// ── Entry point ───────────────────────────────────────────────────────
// [RCF:PROTECTED]
export async function initCommand(opts) {
  console.log(chalk.cyan('\nAladdinAI'));
  console.log(chalk.dim('Self-hosted AI workspace — agents, memory, CRM, channels.\n'));

  // Source mode needs git as well; image mode only needs docker.
  await runPrereqChecks({ requireGit: !!opts.source });

  const defaults = {
    projectName: opts.name || 'aladdin-ai',
    start: !opts.skipStart,
  };

  const answers = opts.yes
    ? defaults
    : await inquirer.prompt([
        {
          type: 'input',
          name: 'projectName',
          message: 'Project directory:',
          default: defaults.projectName,
        },
        {
          type: 'confirm',
          name: 'start',
          message: opts.source
            ? 'Build images and start services after setup?'
            : 'Pull images and start services after setup?',
          default: defaults.start,
        },
      ]);

  const targetDir = path.resolve(process.cwd(), answers.projectName);
  if (fs.existsSync(targetDir) && fs.readdirSync(targetDir).length > 0) {
    console.log(chalk.red(`\nDirectory "${answers.projectName}" already exists and is not empty.`));
    process.exit(1);
  }

  try {
    if (opts.source) {
      await installFromSource(targetDir, answers);
    } else {
      await installFromImages(targetDir, answers);
    }
  } catch (err) {
    console.error(chalk.red('\n' + (err.shortMessage || err.message)));
    process.exit(1);
  }

  if (answers.start) {
    console.log(chalk.green('\n✓ Services running'));
    console.log('\n  Frontend: ' + chalk.cyan('http://localhost:3000'));
    console.log('  Backend:  ' + chalk.cyan('http://localhost:8000'));

    // Run setup wizard after successful start
    await runSetupWizard(targetDir);
  } else {
    console.log(chalk.green('\nSetup complete (services not started).'));
    console.log(`\n  cd ${answers.projectName}`);
    console.log('  npx aladdin-ai up');
  }

  console.log(chalk.dim('\nHealth check: npx aladdin-ai doctor'));
  if (!opts.source) {
    console.log(chalk.dim('Update: cd ' + answers.projectName + ' && docker compose pull && npx aladdin-ai restart\n'));
  } else {
    console.log(chalk.dim('Source tree is in ' + answers.projectName + ' — edit and rebuild with `npx aladdin-ai up --build`\n'));
  }
}
