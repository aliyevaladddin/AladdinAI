// `aladdin-ai init` — clone repo, configure .env interactively, start with Docker.

import chalk from 'chalk';
import inquirer from 'inquirer';
import ora from 'ora';
import { execa } from 'execa';
import fs from 'fs-extra';
import path from 'path';
import crypto from 'crypto';
import { runPrereqChecks } from '../lib/prereq.js';
import { compose } from '../lib/compose.js';

const REPO_URL = 'https://github.com/aliyevaladddin/AladdinAI.git';

function genSecret(bytes = 32) {
  return crypto.randomBytes(bytes).toString('hex');
}

function genFernetKey() {
  // Fernet keys are 32 random bytes base64-urlsafe encoded
  return crypto.randomBytes(32).toString('base64url') + '=';
}

function patchEnv(envText, vars) {
  let out = envText;
  for (const [k, v] of Object.entries(vars)) {
    const re = new RegExp(`^${k}=.*$`, 'm');
    if (re.test(out)) {
      out = out.replace(re, `${k}=${v}`);
    } else {
      out += `\n${k}=${v}`;
    }
  }
  return out;
}

export async function initCommand(opts) {
  console.log(chalk.cyan('\nAladdinAI bootstrap'));
  console.log(chalk.dim('Self-hosted AI workspace — agents, memory, CRM, channels.\n'));

  await runPrereqChecks({ requireGit: true });

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
          message: 'Start services with Docker Compose after setup?',
          default: defaults.start,
        },
      ]);

  const targetDir = path.resolve(process.cwd(), answers.projectName);
  if (fs.existsSync(targetDir)) {
    console.log(chalk.red(`\nDirectory "${answers.projectName}" already exists. Pick another name or remove it.`));
    process.exit(1);
  }

  // 1. Clone
  const cloneSpin = ora('Cloning repository').start();
  try {
    await execa('git', ['clone', '--depth', '1', REPO_URL, targetDir]);
    await fs.remove(path.join(targetDir, '.git'));
    cloneSpin.succeed('Repository cloned');
  } catch (err) {
    cloneSpin.fail('git clone failed');
    console.error(err.shortMessage || err.message);
    process.exit(1);
  }

  // 2. Generate .env from template + secure secrets
  const envSpin = ora('Creating .env with generated secrets').start();
  try {
    const tmpl = await fs.readFile(path.join(targetDir, '.env.example'), 'utf8');
    const dbPassword = genSecret(16);
    const patched = patchEnv(tmpl, {
      POSTGRES_PASSWORD: dbPassword,
      JWT_SECRET: genSecret(32),
      FERNET_KEY: genFernetKey(),
      // Activate Postgres connection (commented out in template by default)
      DATABASE_URL: `postgresql+asyncpg://aladdin_user:${dbPassword}@postgres:5432/aladdinai`,
    });
    await fs.writeFile(path.join(targetDir, '.env'), patched);
    envSpin.succeed('.env created with secure secrets');
  } catch (err) {
    envSpin.fail('Failed to create .env — copy .env.example manually');
    console.error(chalk.dim(err.message));
  }

  // 3. Start services
  if (answers.start) {
    console.log(chalk.cyan('\nStarting services with Docker Compose…\n'));
    const r = await compose(['up', '-d', '--build'], { cwd: targetDir });
    if (r.exitCode !== 0) {
      console.error(chalk.red('\ndocker compose up failed. Check Docker logs.'));
      process.exit(1);
    }
    console.log(chalk.green('\n✓ Services started'));
    console.log('\n  Backend:  ' + chalk.cyan('http://localhost:8000/api/docs'));
    console.log('  Frontend: ' + chalk.cyan('http://localhost:3000'));
  } else {
    console.log(chalk.green('\nSetup complete (services not started).'));
    console.log(`\n  cd ${answers.projectName}`);
    console.log('  npx aladdin-ai up');
  }

  console.log(chalk.dim('\nDocs: README.md, docs/ARCHITECTURE.md'));
  console.log(chalk.dim('Status check: npx aladdin-ai doctor\n'));
}
