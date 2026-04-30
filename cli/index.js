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
  .version('1.2.0')
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

        // GitHub Release assets usually follow this pattern
        if (platform === 'darwin') {
          downloadUrl = 'https://github.com/aliyevaladddin/AladdinAI/releases/latest/download/AladdinAI.dmg';
          fileName = 'AladdinAI.dmg';
        } else if (platform === 'win32') {
          // Changed to match electron-builder default naming or redirect
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

        // Use -f to fail on 404, -L to follow redirects
        try {
          await execa('curl', ['-f', '-L', '-o', downloadPath, downloadUrl]);
        } catch (downloadErr) {
          spinner.fail(chalk.red(`\n❌ Failed to download ${fileName}. Possibly the version is not yet available on GitHub Releases.`));
          console.log(chalk.yellow(`\nTry downloading manually from: https://github.com/aliyevaladddin/AladdinAI/releases`));
          return;
        }

        spinner.succeed(chalk.green(`\n✅ Download complete: ${fileName}`));
        console.log(chalk.cyan(`\n👉 Opening ${fileName} for installation...`));

        try {
          if (platform === 'darwin') {
            await execa('open', [downloadPath]);
          } else if (platform === 'win32') {
            // More robust Windows open command using shell
            await execa('powershell', ['-Command', `Start-Process "${downloadPath}"`], { shell: true });
          } else {
            await execa('xdg-open', [downloadPath]);
          }
        } catch (openErr) {
          console.log(chalk.yellow(`\n⚠️  Could not open automatically. Please run ${fileName} manually from this folder.`));
        }

      } catch (err) {
        spinner.fail(chalk.red('An unexpected error occurred during installation.'));
        console.error(err);
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
      await execa('git', ['clone', REPO_URL, targetDir]);
      spinner.succeed(chalk.green('Repository cloned successfully!'));
      await fs.remove(path.join(targetDir, '.git'));

      if (answers.installDeps) {
        const feSpinner = ora('Installing Frontend dependencies...').start();
        await execa('npm', ['install'], { cwd: path.join(targetDir, 'frontend') });
        feSpinner.succeed(chalk.green('Frontend dependencies installed!'));
      }

      console.log(chalk.blue('\n🛡️  RCF Protocol: Your project is pre-marked for RCF compliance.'));
      console.log(chalk.green(`\n🚀 Success! Your AladdinAI platform is ready in ${answers.projectName}`));

    } catch (error) {
      spinner.fail(chalk.red('Failed to bootstrap project.'));
      console.error(error);
    }
  });

program.parse(process.argv);
