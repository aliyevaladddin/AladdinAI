// Setup wizard — runs after first install to configure LLM providers and create first agent
import chalk from 'chalk';
import inquirer from 'inquirer';
import ora from 'ora';
import { execa } from 'execa';

const PROVIDER_CONFIGS = {
  nim: {
    name: 'NVIDIA NIM',
    description: 'Free tier available, best performance',
    baseUrl: 'https://integrate.api.nvidia.com/v1',
    env: {
      NIM_API_KEY: 'Get from: https://build.nvidia.com',
      NIM_BASE_URL: 'https://integrate.api.nvidia.com/v1',
      NIM_MODEL: 'meta/llama-3.1-70b-instruct',
    },
  },
  openai: {
    name: 'OpenAI',
    description: 'GPT-4, GPT-3.5 Turbo',
    baseUrl: 'https://api.openai.com/v1',
    env: {
      OPENAI_API_KEY: 'Get from: https://platform.openai.com/api-keys',
    },
  },
  anthropic: {
    name: 'Anthropic',
    description: 'Claude 3.5 Sonnet, Opus, Haiku',
    baseUrl: 'https://api.anthropic.com',
    env: {
      ANTHROPIC_API_KEY: 'Get from: https://console.anthropic.com/settings/keys',
    },
  },
  local: {
    name: 'Local (BentoML)',
    description: 'Self-hosted models',
    baseUrl: 'http://localhost:3000',
    env: {},
  },
};

async function setupProviders() {
  console.log(chalk.cyan('\n📡 LLM Provider Setup\n'));
  console.log(chalk.dim('Select which LLM providers you want to configure.\n'));

  const { providers } = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'providers',
      message: 'Select providers (Space to select, Enter to continue):',
      choices: [
        {
          name: `${chalk.green('●')} NVIDIA NIM (Recommended) - Free tier, 70B+ models`,
          value: 'nim',
          checked: true,
        },
        {
          name: `  OpenAI - GPT-4, GPT-3.5 Turbo`,
          value: 'openai',
        },
        {
          name: `  Anthropic - Claude 3.5 Sonnet, Opus`,
          value: 'anthropic',
        },
        {
          name: `  Local (BentoML) - Self-hosted models`,
          value: 'local',
        },
      ],
    },
  ]);

  if (providers.length === 0) {
    console.log(chalk.yellow('\n⚠ No providers selected. You can configure them later in Settings.\n'));
    return {};
  }

  const envUpdates = {};

  for (const provider of providers) {
    const config = PROVIDER_CONFIGS[provider];
    console.log(chalk.cyan(`\n── ${config.name} ──`));

    if (Object.keys(config.env).length > 0) {
      const { shouldConfigure } = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'shouldConfigure',
          message: `Configure ${config.name} now?`,
          default: true,
        },
      ]);

      if (shouldConfigure) {
        for (const [key, hint] of Object.entries(config.env)) {
          const isSecret = key.toLowerCase().includes('key') || key.toLowerCase().includes('secret') || key.toLowerCase().includes('password') || key.toLowerCase().includes('token');
          const { value } = await inquirer.prompt([
            {
              type: isSecret ? 'password' : 'input',
              name: 'value',
              message: `${key}:`,
              mask: isSecret ? '*' : undefined,
              validate: (input) => input.length > 0 || 'Required',
            },
          ]);
          envUpdates[key] = value;
        }
      } else {
        console.log(chalk.dim(`  ${hint}`));
      }
    } else {
      console.log(chalk.dim('  No configuration needed - will use local endpoint'));
    }
  }

  return envUpdates;
}

async function setupMongoDB() {
  console.log(chalk.cyan('\n🗄️  MongoDB Atlas Setup\n'));
  console.log(chalk.dim('MongoDB Atlas is used for vector memory and media storage.\n'));

  const { useMongoDB } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'useMongoDB',
      message: 'Configure MongoDB Atlas now?',
      default: true,
    },
  ]);

  if (!useMongoDB) {
    console.log(chalk.yellow('⚠ Skipping MongoDB - memory features will be disabled'));
    console.log(chalk.dim('  Get free $500 credits: https://www.mongodb.com/startups\n'));
    return {};
  }

  console.log(chalk.dim('\nGet connection string from:'));
  console.log(chalk.dim('1. https://cloud.mongodb.com'));
  console.log(chalk.dim('2. Connect → Drivers → Connection string\n'));

  const { mongoUrl } = await inquirer.prompt([
    {
      type: 'input',
      name: 'mongoUrl',
      message: 'MongoDB connection string:',
      default: 'mongodb+srv://user:pass@cluster.mongodb.net/',
      validate: (input) =>
        input.startsWith('mongodb://') || input.startsWith('mongodb+srv://') || 'Must be a valid MongoDB URL',
    },
  ]);

  return { MONGODB_URL: mongoUrl };
}

async function createFirstAgent() {
  console.log(chalk.cyan('\n🤖 Create Your First Agent\n'));

  const { shouldCreate } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'shouldCreate',
      message: 'Create a starter agent now?',
      default: true,
    },
  ]);

  if (!shouldCreate) {
    console.log(chalk.dim('  You can create agents later from the dashboard\n'));
    return;
  }

  const answers = await inquirer.prompt([
    {
      type: 'list',
      name: 'template',
      message: 'Choose agent template:',
      choices: [
        {
          name: '💬 General Assistant - Helpful chatbot for general tasks',
          value: 'general',
        },
        {
          name: '📊 CRM Assistant - Sales and contact management',
          value: 'crm',
        },
        {
          name: '📧 Email Assistant - Email drafting and responses',
          value: 'email',
        },
        {
          name: '🔍 Research Assistant - Web search and analysis',
          value: 'research',
        },
      ],
    },
    {
      type: 'input',
      name: 'name',
      message: 'Agent name (lowercase, no spaces):',
      default: (answers) => answers.template + '_agent',
      validate: (input) => /^[a-z0-9_]+$/.test(input) || 'Only lowercase letters, numbers, and underscores',
    },
  ]);

  const templates = {
    general: {
      display_name: 'General Assistant',
      system_prompt: 'You are a helpful AI assistant. Answer questions clearly and concisely.',
      tools: [],
    },
    crm: {
      display_name: 'CRM Assistant',
      system_prompt:
        'You are a CRM assistant. Help manage contacts, deals, and activities. Always search the CRM before creating new records.',
      tools: ['search_contacts', 'create_contact', 'create_deal', 'add_activity'],
    },
    email: {
      display_name: 'Email Assistant',
      system_prompt: 'You are an email assistant. Draft professional emails and help with correspondence.',
      tools: ['send_email', 'search_contacts'],
    },
    research: {
      display_name: 'Research Assistant',
      system_prompt: 'You are a research assistant. Search for information and provide detailed analysis.',
      tools: ['web_search', 'analyze_image'],
    },
  };

  const agentConfig = {
    name: answers.name,
    ...templates[answers.template],
    model: 'meta/llama-3.1-70b-instruct',
    memory_enabled: true,
  };

  console.log(chalk.dim(`\n  Agent will be created after services start\n`));

  return agentConfig;
}

export async function runSetupWizard(targetDir) {
  console.log(chalk.bold.cyan('\n✨ AladdinAI Setup Wizard\n'));
  console.log(chalk.dim('Configure your AI workspace in a few steps.\n'));

  const { shouldRun } = await inquirer.prompt([
    {
      type: 'confirm',
      name: 'shouldRun',
      message: 'Run setup wizard?',
      default: true,
    },
  ]);

  if (!shouldRun) {
    console.log(chalk.dim('  You can configure everything later from the dashboard\n'));
    return;
  }

  // Step 1: Providers
  const providerEnv = await setupProviders();

  // Step 2: MongoDB
  const mongoEnv = await setupMongoDB();

  // Step 3: First agent
  const agentConfig = await createFirstAgent();

  // Update .env file
  if (Object.keys({ ...providerEnv, ...mongoEnv }).length > 0) {
    const spinner = ora('Updating .env with your configuration').start();
    try {
      const fs = await import('fs-extra');
      const path = await import('path');
      const envPath = path.join(targetDir, '.env');
      let envContent = await fs.readFile(envPath, 'utf8');

      for (const [key, value] of Object.entries({ ...providerEnv, ...mongoEnv })) {
        const regex = new RegExp(`^${key}=.*$`, 'm');
        if (regex.test(envContent)) {
          envContent = envContent.replace(regex, `${key}=${value}`);
        } else {
          envContent += `\n${key}=${value}`;
        }
      }

      await fs.writeFile(envPath, envContent);
      spinner.succeed('Configuration saved to .env');
    } catch (err) {
      spinner.fail('Failed to update .env');
      console.error(chalk.red(err.message));
    }
  }

  // Save agent config for post-startup
  if (agentConfig) {
    const fs = await import('fs-extra');
    const path = await import('path');
    await fs.writeJson(path.join(targetDir, '.aladdin-setup.json'), { agentConfig }, { spaces: 2 });
  }

  console.log(chalk.green('\n✓ Setup wizard complete!\n'));
}
