#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import ora from 'ora';
import { execa } from 'execa';
import fs from 'fs-extra';
import path from 'path';

const REPO_URL = 'https://github.com/aliyevaladddin/AladdinAI.git';

const program = new Command();

program
  .name('aladdin-ai')
  .description('Bootstrap a local AladdinAI instance (FastAPI + Next.js)')
  .version('1.3.0')
  .option('-n, --name <name>', 'project directory name')
  .option('-y, --yes', 'accept defaults, skip prompts')
  .option('--skip-install', 'clone only, do not install deps or migrate')
  .action(async (opts) => {
    console.log(chalk.cyan('\nAladdinAI bootstrap'));
    console.log(chalk.dim('Self-hosted AI workspace — agents, memory, CRM, channels.\n'));

    const answers = opts.yes
      ? { projectName: opts.name || 'aladdin-ai', installDeps: !opts.skipInstall }
      : await inquirer.prompt([
          {
            type: 'input',
            name: 'projectName',
            message: 'Project directory:',
            default: opts.name || 'aladdin-ai',
          },
          {
            type: 'confirm',
            name: 'installDeps',
            message: 'Install dependencies and run migrations?',
            default: !opts.skipInstall,
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

    // 2. Copy .env
    const envSpin = ora('Creating .env from template').start();
    try {
      await fs.copy(
        path.join(targetDir, '.env.example'),
        path.join(targetDir, '.env'),
      );
      envSpin.succeed('.env created (edit JWT_SECRET before going to production)');
    } catch (err) {
      envSpin.warn('Could not copy .env.example — do it manually');
    }

    if (answers.installDeps) {
      // 3. Backend deps via make install
      const beSpin = ora('Installing backend dependencies (creates .venv)').start();
      try {
        await execa('make', ['install'], { cwd: targetDir });
        beSpin.succeed('Backend dependencies installed');
      } catch (err) {
        beSpin.fail('make install failed — run it manually after fixing the issue');
        console.error(chalk.dim(err.shortMessage || err.message));
      }

      // 4. Frontend deps
      const feSpin = ora('Installing frontend dependencies').start();
      try {
        await execa('npm', ['install'], { cwd: path.join(targetDir, 'frontend') });
        feSpin.succeed('Frontend dependencies installed');
      } catch (err) {
        feSpin.fail('npm install failed in frontend/');
        console.error(chalk.dim(err.shortMessage || err.message));
      }

      // 5. Migrations
      const mSpin = ora('Applying database migrations').start();
      try {
        await execa('make', ['migrate'], { cwd: targetDir });
        mSpin.succeed('Migrations applied');
      } catch (err) {
        mSpin.fail('make migrate failed — run it manually after fixing the issue');
        console.error(chalk.dim(err.shortMessage || err.message));
      }
    }

    console.log(chalk.green('\nDone.'));
    console.log(`\n  cd ${answers.projectName}`);
    console.log('  make dev-backend    # FastAPI on :8000');
    console.log('  make dev-frontend   # Next.js on :3000');
    console.log(chalk.dim('\nDocs: README.md, docs/ARCHITECTURE.md\n'));
  });

program.parse(process.argv);
