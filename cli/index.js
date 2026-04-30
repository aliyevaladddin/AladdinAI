#!/usr/bin/env node

// NOTICE: This file is protected under RCF-PL v1.2.8
// [RCF:PROTECTED]

import { Command } from 'commander';
import chalk from 'chalk';
import inquirer from 'inquirer';
import ora from 'ora';
import { execa } from 'execa';
import fs from 'fs-extra';
import path from 'path';

const program = new Command();

const REPO_URL = 'https://github.com/aliyevaladddin/AladdinAI.git';

console.log(chalk.cyan(`
   ╔══════════════════════════════════════════════════════════╗
   ║                                                          ║
   ║   ✨  WELCOME TO ALADDIN AI PLATFORM INITIALIZER  ✨   ║
   ║        Powered by RCF Protocol v2.0.3                    ║
   ║                                                          ║
   ╚══════════════════════════════════════════════════════════╝
`));

program
  .name('aladdin-ai')
  .description('Bootstrap your own AladdinAI instance')
  .version('2.0.3')
  .action(async () => {
    const { mode } = await inquirer.prompt([
      {
        type: 'list',
        name: 'mode',
        message: 'What would you like to do?',
        choices: [
          { name: '🚀 Install Desktop App (Recommended)', value: 'desktop' },
          { name: '💻 Clone Source Code (For Developers)', value: 'source' }
        ]
      }
    ]);

    if (mode === 'desktop') {
      const spinner = ora('Preparing Desktop App download...').start();
      try {
        const platform = process.platform;
        let downloadUrl = '';
        let fileName = '';

        if (platform === 'darwin') {
          downloadUrl = 'https://github.com/aliyevaladddin/AladdinAI/releases/latest/download/AladdinAI.dmg';
          fileName = 'AladdinAI.dmg';
        } else if (platform === 'win32') {
          downloadUrl = 'https://github.com/aliyevaladddin/AladdinAI/releases/latest/download/AladdinAI.exe';
          fileName = 'AladdinAI.exe';
        } else if (platform === 'linux') {
          downloadUrl = 'https://github.com/aliyevaladddin/AladdinAI/releases/latest/download/AladdinAI.AppImage';
          fileName = 'AladdinAI.AppImage';
        } else {
          spinner.fail(chalk.red('Platform not supported for desktop direct install.'));
          return;
        }

        spinner.text = `Downloading ${fileName} for ${platform}...`;
        const downloadPath = path.join(process.cwd(), fileName);
        
        await execa('curl', ['-L', '-o', downloadPath, downloadUrl]);
        spinner.succeed(chalk.green(`\n✅ Download complete: ${fileName}`));
        
        console.log(chalk.cyan(`\n👉 Opening ${fileName} for installation...`));
        
        // Cross-platform open command
        const openCmd = platform === 'darwin' ? 'open' : platform === 'win32' ? 'start' : 'xdg-open';
        await execa(openCmd, [downloadPath]);

      } catch (err) {
        spinner.fail(chalk.red('Failed to download Desktop App. Check your internet or GitHub release.'));
      }
      return;
    }

    const answers = await inquirer.prompt([
      {
        type: 'input',
        name: 'projectName',
        message: 'What is your project name?',
        default: 'my-aladdin-ai'
      },
      {
        type: 'confirm',
        name: 'installDeps',
        message: 'Would you like to install dependencies automatically?',
        default: true
      }
    ]);

    const targetDir = path.join(process.cwd(), answers.projectName);

    if (fs.existsSync(targetDir)) {
      console.log(chalk.red(`\n❌ Error: Directory ${answers.projectName} already exists.`));
      process.exit(1);
    }

    const spinner = ora('Cloning AladdinAI repository...').start();

    try {
      // Clone the repo
      await execa('git', ['clone', REPO_URL, targetDir]);
      spinner.succeed(chalk.green('Repository cloned successfully!'));

      // Remove .git from the new project to start fresh
      await fs.remove(path.join(targetDir, '.git'));

      if (answers.installDeps) {
        // Install Frontend
        const feSpinner = ora('Installing Frontend dependencies...').start();
        await execa('npm', ['install'], { cwd: path.join(targetDir, 'frontend') });
        feSpinner.succeed(chalk.green('Frontend dependencies installed!'));

        // Backend setup suggestion
        console.log(chalk.yellow('\n💡 Note: To set up the Backend, make sure you have Python 3.10+ and run:'));
        console.log(chalk.cyan(`   cd ${answers.projectName}/backend && pip install -r requirements.txt`));
      }

      // RCF Initialization notice
      console.log(chalk.blue('\n🛡️  RCF Protocol: Your project is pre-marked for RCF compliance.'));
      console.log(chalk.blue('   Run `npx rcf-cli audit .` to verify your installation.'));

      console.log(chalk.green(`\n🚀 Success! Your AladdinAI platform is ready in ${answers.projectName}`));
      console.log(chalk.white('\nNext steps:'));
      console.log(chalk.cyan(`  1. cd ${answers.projectName}`));
      console.log(chalk.cyan(`  2. Configure your .env files in /backend and /frontend`));
      console.log(chalk.cyan(`  3. Run 'npm run dev' in /frontend`));
      console.log(chalk.cyan(`  4. Start the backend with 'uvicorn app.main:app --reload'`));

    } catch (error) {
      spinner.fail(chalk.red('Failed to bootstrap project.'));
      console.error(error);
    }
  });

program.parse(process.argv);
