# Changelog

All notable changes to AladdinAI will be documented in this file. This changelog follows the conventional commits specification.

## [Unreleased]

### Bug Fixes

- Update dependency overrides and improve HTML sanitization logic in dashboard preview ([abd0507](https://github.com/aliyevaladddin/AladdinAI/commit/abd05076a3d625daebc29189f3cd44b51dca7785))

## [v2.1.7] - 2026-06-06
## [v2.1.6] - 2026-06-06

### Bug Fixes

- Buffer upstream response body in-memory to prevent stream truncation issues ([4c5ee1e](https://github.com/aliyevaladddin/AladdinAI/commit/4c5ee1e4b7fb6e76e78c46dc722fb0618c6d07df))

- Add error handling for request body reading and refine proxy error reporting ([2ba4955](https://github.com/aliyevaladddin/AladdinAI/commit/2ba4955d9f04bff0028e6340d4b4f6601cdc9b1c))

- Add robust JSON parsing and error handling to API request methods ([a236e70](https://github.com/aliyevaladddin/AladdinAI/commit/a236e70b4aa97bdb868ce0f6d48e924ab2d10959))

- Strip content-length header from upstream responses to prevent stream truncation errors ([5d13b4d](https://github.com/aliyevaladddin/AladdinAI/commit/5d13b4df746a2715154041ad033ec7e2aa1b6878))

- Resolve potential connection handling issues in chat router endpoints ([c23973c](https://github.com/aliyevaladddin/AladdinAI/commit/c23973c2037728bf6b5ba845284a2079559dba7b))

- Update database engine config with WAL mode and busy timeout ([60d4873](https://github.com/aliyevaladddin/AladdinAI/commit/60d48736ba646f28209ac343e1f27aebf74b93eb))

- Remove unused sqlalchemy text import ([297ce14](https://github.com/aliyevaladddin/AladdinAI/commit/297ce14d65ec4e1c1284ad8eced70101467236c1))

- Resolve busy_timeout redundancy and tighten docs regex in cliff ([eee7ce8](https://github.com/aliyevaladddin/AladdinAI/commit/eee7ce801b72dd3b6fe658d2a9bc010b561f223c))

- Resolve race condition, silent merge failure and clarify connect_args ([0d8cdce](https://github.com/aliyevaladddin/AladdinAI/commit/0d8cdceb573184db1dd273d6fd72c6ce63d38656))

- Replace immediate merge with GitHub native auto-merge via GraphQL ([0c7ff8f](https://github.com/aliyevaladddin/AladdinAI/commit/0c7ff8f1b50aec3850c77ea46a9efa4e4ab61394))

- Remove unused pathlib.Path import in media_storage (ruff F401) ([db4f0e9](https://github.com/aliyevaladddin/AladdinAI/commit/db4f0e90982c37983e3368977659f25b4c5ffe09))

- Address security vulnerabilities and bugs in SQL playground ([d11351d](https://github.com/aliyevaladddin/AladdinAI/commit/d11351d0076ea8b95db34162aedb56b9ae660645))

- Prevent ReDoS vulnerability in SQL comment stripping ([9cc238f](https://github.com/aliyevaladddin/AladdinAI/commit/9cc238f9eb15a3871c8a57513e70f5f5515b0208))

- Eliminate remaining ReDoS vulnerabilities in comment stripping ([6ac2edb](https://github.com/aliyevaladddin/AladdinAI/commit/6ac2edbcc72e4b3bc5adccab56d83978e0f3afcf))

- Replace regex with string operations to eliminate ReDoS ([581c156](https://github.com/aliyevaladddin/AladdinAI/commit/581c15631f21b6a7a76d5f2690e2e607ad8901be))

- Disable parallel_tool_calls for NVIDIA NIM compatibility ([019fd16](https://github.com/aliyevaladddin/AladdinAI/commit/019fd16f454a2fd0110ee4f848ae3d980261240e))

- Pass tool_choice=auto explicitly so NIM calls tools autonomously ([8ab8e5e](https://github.com/aliyevaladddin/AladdinAI/commit/8ab8e5eb1e85f3a47212516f1d0c93c629960886))

- Disable inter-agent tools by default to prevent small model hallucination of agent IDs ([145b9ea](https://github.com/aliyevaladddin/AladdinAI/commit/145b9ea556cfedb09c26b7f932905207c9979cc1))

- Revert remoteUser to vscode to preserve safe file ownership ([6c9f7f7](https://github.com/aliyevaladddin/AladdinAI/commit/6c9f7f77495e86102dd835c4c5f884e7360e4ab3))

- Resolve CI failures, test isolation, and test suite issues ([64f1354](https://github.com/aliyevaladddin/AladdinAI/commit/64f1354559ea9b1d944b9fc317dbca7ed8fcb5d8))

- Add backend root path to sys.path in conftest.py ([bc41da2](https://github.com/aliyevaladddin/AladdinAI/commit/bc41da2f6e41ff4a3ee9a3dfac949f88afb1ed11))

- Automatically rewrite postgresql:// scheme to use asyncpg driver ([263eb18](https://github.com/aliyevaladddin/AladdinAI/commit/263eb181b9464a1c239ca81853f1b5954db17cc8))

- Use npx openapi-markdown for API doc generation in CI ([72a3d48](https://github.com/aliyevaladddin/AladdinAI/commit/72a3d48110da385327a159fea5e2738bce3aa714))


### CI

- Drop Node 20 from CI matrix, require Node 22 LTS minimum ([3e63cb0](https://github.com/aliyevaladddin/AladdinAI/commit/3e63cb08a8581f3e94d181a43f4cdcd125ec9880))


### Documentation

- Add INTEGRATIONS.md with memory layer docs and Origin integration ([dd450a6](https://github.com/aliyevaladddin/AladdinAI/commit/dd450a600f34ad9f0af78f25ea4065f41c28949c))

- Fix model name prefix and API route parameter in INTEGRATIONS.md ([f7e920a](https://github.com/aliyevaladddin/AladdinAI/commit/f7e920a25cef48d382892d15cbb3ba5121ce048b))

- Fix vector index filter fields and add npx security notice ([0e57f40](https://github.com/aliyevaladddin/AladdinAI/commit/0e57f4026e4b5f025fecc22cafee3db0f1249a9a))

- Add Operations section covering logs, upgrades, recovery, permissions and agent limits ([6f55365](https://github.com/aliyevaladddin/AladdinAI/commit/6f553654771b39c25a6bb1af6a413bcd4ef2d10c))

- Add security documentation for SQL playground endpoint ([5726e6d](https://github.com/aliyevaladddin/AladdinAI/commit/5726e6dea66552be76c4d2d40f7c153aa4930f80))

- Add nosec annotation for intentional SQL execution ([723986c](https://github.com/aliyevaladddin/AladdinAI/commit/723986ca128270ee39405d07cef3bd49777bd1a0))

- Generate API documentation and OpenAPI specification for the agent orchestration system ([3f444a0](https://github.com/aliyevaladddin/AladdinAI/commit/3f444a0b6ff845f297ee485dab549a491fa2f511))


### Features

- Add existence checks to timestamp migration and expand target table list ([51a9b36](https://github.com/aliyevaladddin/AladdinAI/commit/51a9b3676e839ee680db68c7c375c7f22f05af45))

- Add Notification model and create corresponding database table ([dfab058](https://github.com/aliyevaladddin/AladdinAI/commit/dfab05850593e7265c9a855c756650e2235dec86))

- Allow localhost URLs in development for WAHA integration ([4ecbfd1](https://github.com/aliyevaladddin/AladdinAI/commit/4ecbfd17d76f0f59460343e2b46f48f3e9b4ac99))

- Add email tool, UI improvements, and image generation ([7495056](https://github.com/aliyevaladddin/AladdinAI/commit/7495056f236353beeafb9eb94dd809c632306478))

- Add send_email tool to default agent capabilities ([09fdb73](https://github.com/aliyevaladddin/AladdinAI/commit/09fdb7303a64b35e570bafc342d2013c90b6d35b))

- Add git-cliff config and update changelog workflow ([1bb3018](https://github.com/aliyevaladddin/AladdinAI/commit/1bb3018a6283fa58e2488da8be439bb3e7165cdd))

- MongoDB GridFS media storage + provider-independent models ([96a7437](https://github.com/aliyevaladddin/AladdinAI/commit/96a743718beb0e6f404e77056637fec20da33d1d))

- SQL playground enhancements + storage settings UI ([9e83bb2](https://github.com/aliyevaladddin/AladdinAI/commit/9e83bb26aea98382dfeac6f95c4805bf069dbf65))

- Add agent execution tracing and comprehensive documentation system ([fa42d37](https://github.com/aliyevaladddin/AladdinAI/commit/fa42d373930613550469467ee04d34645e843dfd))

- Add GitHub action for AladdinAI multi-agent deployment ([ad52d30](https://github.com/aliyevaladddin/AladdinAI/commit/ad52d3081cbdd61ea34ed5281f1cab2ef1835fe8))

- Update Docker image to bookworm, add sudo user support, and set remoteUser to root ([8cff2b6](https://github.com/aliyevaladddin/AladdinAI/commit/8cff2b64bfe51bdb65e3fa85d0c45a5de3c8e9b5))


### Refactor

- Migrate database timestamps to timezone-aware format and update SQLAlchemy type mapping ([bdac085](https://github.com/aliyevaladddin/AladdinAI/commit/bdac085d8d50d8cdca2f978d969f114020e874ec))

- Remove unused sqlalchemy import in timestamp migration script ([38ac031](https://github.com/aliyevaladddin/AladdinAI/commit/38ac031ad7354354e170cd963b34b021b182ec03))

- Improve Markdown code block detection and type safety in chat interface ([3eb3ee7](https://github.com/aliyevaladddin/AladdinAI/commit/3eb3ee7bc2d52cc3b9b033c521710791ce7d16ac))

- Make system settings read-only by default and ensure concurrency-safe database persistence with a unique user_id constraint while fixing OpenAI embedding dimension support. ([a95814f](https://github.com/aliyevaladddin/AladdinAI/commit/a95814ff41b5ffc50dddc02894eca7b3310ad7a3))

- Remove unused AsyncSession import and simplify forbidden keyword error string formatting ([7f421c2](https://github.com/aliyevaladddin/AladdinAI/commit/7f421c2639ec042b18d54254cc77c9a47532176a))

- Remove automated version update workflow and dynamically sync API version from CLI package.json ([5c74fdd](https://github.com/aliyevaladddin/AladdinAI/commit/5c74fdde62ec5cdafc8d31b90cd84e63c4787a66))

- Remove unused imports across tests and services and clean up console output formatting ([43dee88](https://github.com/aliyevaladddin/AladdinAI/commit/43dee887c60ed5de508114dce70c382093381050))


### Security

- Mask sensitive API keys with password prompt in setup wizard ([33ddebe](https://github.com/aliyevaladddin/AladdinAI/commit/33ddebe32c9756fb054f43d4eec9acb084390d95))

## [v2.1.5] - 2026-05-31

### Bug Fixes

- Prepend https protocol to Render service hostnames in backend proxy target ([57a849d](https://github.com/aliyevaladddin/AladdinAI/commit/57a849d7dcfe6b8b596493bfffc63d1d9c4d619a))


### Features

- Add Render configuration for AladdinAI-frontend service with environment variable bindings ([6ac400a](https://github.com/aliyevaladddin/AladdinAI/commit/6ac400a5b09a8c36be5b2c3839ca5db2b5036980))

- Replace build-time rewrites with a runtime API proxy route handler to support dynamic environment variables ([95fe05b](https://github.com/aliyevaladddin/AladdinAI/commit/95fe05b9cdec2df2cc97af80cf5faae98e907395))

## [v2.1.4] - 2026-05-31

### Bug Fixes

- Update dockerfilePath from /backend/Dockerfile to Dockerfile ([8e92bea](https://github.com/aliyevaladddin/AladdinAI/commit/8e92beaa2b35ea4dbb45ebcb5f1cd07b54eb04b4))

- Replace preDeployCommand with startCommand for SQLite migrations (#125) ([1bdeee1](https://github.com/aliyevaladddin/AladdinAI/commit/1bdeee1023a6831d77e963ebbbff104471a2bdad))

- Move alembic migrations to preDeployCommand, remove multi-region ([ce7b05e](https://github.com/aliyevaladddin/AladdinAI/commit/ce7b05e8f136d38a22016f892b8ff90e332de222))

- Replace preDeployCommand with startCommand for SQLite migrations ([453c1e0](https://github.com/aliyevaladddin/AladdinAI/commit/453c1e0c6e6f1e7deae9b287e589dcba79df719d))

- Correct alembic migration chain and move to startCommand for SQLite ([0126ac7](https://github.com/aliyevaladddin/AladdinAI/commit/0126ac788b341d8ab21744237c1c81bb09464dc0))

- Move railway.json to repo root with correct paths ([e06f119](https://github.com/aliyevaladddin/AladdinAI/commit/e06f1199f740c20343a2e12ee0d574bd2811894d))

- Add dockerContext to railway.json ([770164b](https://github.com/aliyevaladddin/AladdinAI/commit/770164b18a31dfdfa76b4a3b6e659ba09edd8542))

- Remove dockerContext from railway.json to prevent double backend/ path lookup ([e8090f5](https://github.com/aliyevaladddin/AladdinAI/commit/e8090f56a01b58642d9b8f25102ec37cd5f256c7))

- Use sync postgresql driver for Alembic migrations on Render ([dc6238d](https://github.com/aliyevaladddin/AladdinAI/commit/dc6238dcb66e6eff174126e5d712e0b7c1b76400))

- Add psycopg2-binary for Alembic sync migrations ([3b8d080](https://github.com/aliyevaladddin/AladdinAI/commit/3b8d0801faacb36b52140897f06358b199dd849f))

- Add verbose logging to render_init.sh for debugging migrations ([77ca475](https://github.com/aliyevaladddin/AladdinAI/commit/77ca475221de6b7e7f31490be0076896f2d22084))

- Force Docker rebuild and upgrade pip to fix PyJWT import ([833fa8d](https://github.com/aliyevaladddin/AladdinAI/commit/833fa8d6bea798aedea1faf5166fca9850034352))


### Features

- Configure Render deployment with Postgres and async driver conversion ([8dad10e](https://github.com/aliyevaladddin/AladdinAI/commit/8dad10ec36f436d0825f4e4c5dd5c0421741bfa3))

## [v2.1.3] - 2026-05-30
## [v2.1.2] - 2026-05-30

### Bug Fixes

- Verify GitHub webhook signature against raw body bytes ([c8a8ea2](https://github.com/aliyevaladddin/AladdinAI/commit/c8a8ea2c8599ff540ac8f361afb881016afa09a7))

- Improve security and error handling in webhook handler ([af4a852](https://github.com/aliyevaladddin/AladdinAI/commit/af4a8522323603f7c115c0d5fb3c0d4be240ff3c))


### Build

- Remove Node.js 18.x from CI build matrix ([15312ad](https://github.com/aliyevaladddin/AladdinAI/commit/15312adc46bbf9fa63f81d2e14b1fbfc3fff4d3a))

- Bump next from 16.2.4 to 16.2.6 in /frontend ([fc27ef6](https://github.com/aliyevaladddin/AladdinAI/commit/fc27ef6a11fca684d1670caf82f5dbe244144b7a))

- Bump python-jose from 3.3.0 to 3.4.0 in /backend ([75a8cee](https://github.com/aliyevaladddin/AladdinAI/commit/75a8ceed6b19e1edab69e1e1e146e187b419df7f))

- Bump sqlalchemy from 2.0.35 to 2.0.50 ([c8092ae](https://github.com/aliyevaladddin/AladdinAI/commit/c8092ae53be1c65d4a40d202fdc37b522b696c22))

- Bump actions/checkout from 4 to 6 ([53f4bd2](https://github.com/aliyevaladddin/AladdinAI/commit/53f4bd236322e782abe1ab90224a29c2db8e0e72))

- Bump python-multipart from 0.0.12 to 0.0.29 ([d059ee4](https://github.com/aliyevaladddin/AladdinAI/commit/d059ee4d177ed32f5654276b910bec4c670179c2))

- Bump pyjwt from 2.8.0 to 2.13.0 ([14ce10d](https://github.com/aliyevaladddin/AladdinAI/commit/14ce10d0bef2a9eaa93b210da1b4131319adfd50))

- Bump httpx from 0.27.0 to 0.28.1 ([2de2791](https://github.com/aliyevaladddin/AladdinAI/commit/2de2791be1f87ab5fb56ac20da44aa1f0304d8df))

- Bump fastapi from 0.115.0 to 0.136.3 ([501ff69](https://github.com/aliyevaladddin/AladdinAI/commit/501ff695800bc3c284dfd64713370995f42a3a16))

- Bump actions/setup-node from 4 to 6 ([6d607f1](https://github.com/aliyevaladddin/AladdinAI/commit/6d607f1e2b61c324033d6e90dba32724a3b48f38))

- Bump actions/setup-python from 5 to 6 ([07d6e22](https://github.com/aliyevaladddin/AladdinAI/commit/07d6e2251409458b238fd0f1d3afdbb868359097))


### CI

- Update webpack workflow to install dependencies and build from frontend directory ([0b48d00](https://github.com/aliyevaladddin/AladdinAI/commit/0b48d003d0758318248e94524b7475a82097c775))


### Documentation

- Update CONTRIBUTING.md with actual setup commands and conventional commits ([6391a27](https://github.com/aliyevaladddin/AladdinAI/commit/6391a273077321172ab43f108852fbeb8c7b5ce5))

- Restore CODE_OF_CONDUCT link and fix backend venv setup ([0b6a498](https://github.com/aliyevaladddin/AladdinAI/commit/0b6a4988162009392f586a87c0fda3e6020cb31a))

- Fix CLI language and clarify changelog commit types ([35d74bf](https://github.com/aliyevaladddin/AladdinAI/commit/35d74bf100a78c4ebe6e0cbd21b27a0f95ee2da0))

- Add docstrings and comments for secret field changes ([9258452](https://github.com/aliyevaladddin/AladdinAI/commit/92584521cc4a1be5fd71f58aeb97d5df130745ca))

- Add Privacy Policy and Terms of Service for GitHub Marketplace ([36367c5](https://github.com/aliyevaladddin/AladdinAI/commit/36367c551f0beb6034f9718cb8b7ddefc566f255))

- Add MongoDB for Startups badge and credits info ([788519e](https://github.com/aliyevaladddin/AladdinAI/commit/788519e83686ad40f785f21515e969350c35f369))


### Features

- Add Cloudflare Functions for GitHub bot webhook ([5c9d283](https://github.com/aliyevaladddin/AladdinAI/commit/5c9d28349d970e2147123fe55c5005dad1de63f6))

- Increase secret field lengths for GitHub App token format change ([ea4d62a](https://github.com/aliyevaladddin/AladdinAI/commit/ea4d62a91b47c65f27ab16951c16f64a6a72099a))

- Add descriptive metadata and parameter schemas to GitHub tools ([50724dc](https://github.com/aliyevaladddin/AladdinAI/commit/50724dc2fbe8343ec76427a061145f2e8c142429))


### Refactor

- Update Cloudflare Functions env variable names ([715ab34](https://github.com/aliyevaladddin/AladdinAI/commit/715ab348b329648bd81b20f95cd9cde133bd0965))

## [v2.1.1] - 2026-05-28

### Bug Fixes

- Fix readme ([eb05ec5](https://github.com/aliyevaladddin/AladdinAI/commit/eb05ec5fbffb8b6f622263e2f2e3506528b1fa3b))

- Replace git-cliff-action with direct binary ([5a62536](https://github.com/aliyevaladddin/AladdinAI/commit/5a62536cc14d94ba376c26076e5fb7a3ce020ee8))

- Add write permissions to changelog workflow ([43351d4](https://github.com/aliyevaladddin/AladdinAI/commit/43351d487c13feaddd3709993913eb41b008d5d3))

- Add validation for GitHub tools parameters per code review feedback ([3de2583](https://github.com/aliyevaladddin/AladdinAI/commit/3de25834b4d85f1114aa77e17ee1636d479845b6))

- Improve error message for empty installation_id ([1e99697](https://github.com/aliyevaladddin/AladdinAI/commit/1e9969774cb32fe10735a585cf99397d52f78f87))

- Add token validation and improve repo format regex per code review ([1407562](https://github.com/aliyevaladddin/AladdinAI/commit/1407562c14d5e2da5009451056833b1b1fff0ba1))

- Move imports inside function to resolve ruff E402 ([e620ee7](https://github.com/aliyevaladddin/AladdinAI/commit/e620ee7593e66252f1a7b37f0b9bb0e45afeb505))

- Add input validation and logging per code review suggestions ([30795c0](https://github.com/aliyevaladddin/AladdinAI/commit/30795c0ed412c2c34be7307e0fc2b36755746994))

- Add logging for unhandled event types ([d7cb663](https://github.com/aliyevaladddin/AladdinAI/commit/d7cb6638dae7011fe3320fc2b9b8e9cacda34059))

- Add explicit HTTP error handling with logging ([c68b025](https://github.com/aliyevaladddin/AladdinAI/commit/c68b02542ae899816009af35a7da5c04f9885df5))

- Add error handling and logging to AladdinAI bot ([ea8a8cf](https://github.com/aliyevaladddin/AladdinAI/commit/ea8a8cf02f64376bc8778ba099f76346606bf209))

- Remove unused settings import in autonomous_bot_scheduler ([c7af3b9](https://github.com/aliyevaladddin/AladdinAI/commit/c7af3b966ce2c11121fa8fc6c12fdeb575b96526))

- Update changelog workflow to use AladdinAI bot and create PRs ([beb141f](https://github.com/aliyevaladddin/AladdinAI/commit/beb141f54daf50e4ba91b45b25966918d6722af7))

- Correct indentation and add owner parameter to _get_user_context ([e95d9ba](https://github.com/aliyevaladddin/AladdinAI/commit/e95d9ba21b4519604ee395bcf10224780c32a9ef))


### Documentation

- Rewrite Quick start around npx aladdin-ai ([3457018](https://github.com/aliyevaladddin/AladdinAI/commit/345701851873b78986b6d45b88392d1804e8371a))

- Add project structure documentation for backend modules and update environment configuration reference. ([0fc54cc](https://github.com/aliyevaladddin/AladdinAI/commit/0fc54cce6f97c03f8bbe85c2d2fae1c5574693b4))

- Redesign and update README with improved project branding and documentation structure ([173a978](https://github.com/aliyevaladddin/AladdinAI/commit/173a978135747838f478e004d6ab4075673bd0e6))


### Features

- Implement Operational Control Center theme system and UI shell ([8caf39b](https://github.com/aliyevaladddin/AladdinAI/commit/8caf39b79d8f19ec2996896a9dfaa56bf7ad16f8))

- Implement control center, theme switcher and terminal provider ([de8e5c2](https://github.com/aliyevaladddin/AladdinAI/commit/de8e5c2fa11febf28f347f98fd05e10539e40084))

- Implement modular plug-and-play terminal system ([4e1d4fc](https://github.com/aliyevaladddin/AladdinAI/commit/4e1d4fc7f5d7f79df996499860ad663e84a07d69))

- Terminal UI fixes, router resolver, and encryption updates ([2d5610e](https://github.com/aliyevaladddin/AladdinAI/commit/2d5610e2af62123fcdb0d14353b38f6cecb85201))

- Initialize session tracking file and configure Claude proxy model routes ([17b2412](https://github.com/aliyevaladddin/AladdinAI/commit/17b2412789a6472e70f0f590a8a0246ecaefcf86))

- Refactor terminal system with multi-session support and configure Docker-in-Docker for local development. ([8dc6e06](https://github.com/aliyevaladddin/AladdinAI/commit/8dc6e064d0f57dcc249944658593f9c5822581a4))

- Implement Wetty terminal adapter with SSH support and configurable Traefik routing ([d547942](https://github.com/aliyevaladddin/AladdinAI/commit/d54794213bd508759062db2987d74f3048b2b586))

- Refactor terminal adapters, introduce registry, lifecycle management, and setup scripts ([b19e5c2](https://github.com/aliyevaladddin/AladdinAI/commit/b19e5c2641948bbde6e5f4fe3932eb97b956d3db))

- Add project feedback links to README and setup script, and ignore blog architecture documentation ([945f138](https://github.com/aliyevaladddin/AladdinAI/commit/945f1383ae493efcae436f1d6fb6ee22329ac48f))

- Add CI, changelog, render deploy ([abf5185](https://github.com/aliyevaladddin/AladdinAI/commit/abf518560f4e827d884b57ee06ec52fbf41848c0))

- Implement multi-agent orchestration framework and add suite of specialized agents with automated workflow triggers ([fafd2f8](https://github.com/aliyevaladddin/AladdinAI/commit/fafd2f884ff566421f096d16223123d167a20c86))

- Add documentation for demo agents and clean up proactive reminder service imports ([83d4502](https://github.com/aliyevaladddin/AladdinAI/commit/83d4502f14a85256e2432def8f69068666afb12b))

- Refine code review agent prompt and add bot commit workflow demo ([9afe5d3](https://github.com/aliyevaladddin/AladdinAI/commit/9afe5d3cc9b3bba68f0edfc978f77d5e8626f5a1))

- Add bot-commits workflow for GitHub App demo ([6d4f7a4](https://github.com/aliyevaladddin/AladdinAI/commit/6d4f7a47bb7f43c7f06991e86f699c667a50a84c))

- Add auto-merge for bot PRs ([a35ab06](https://github.com/aliyevaladddin/AladdinAI/commit/a35ab06b0e95963d30d59d5e21af5ec36f07a92c))

- Integrate GitHub App bots into backend with tools and auth service ([2ac13a5](https://github.com/aliyevaladddin/AladdinAI/commit/2ac13a5f7ff62dc3c8b0a63b97984cc0feb31468))

- Add GitHub webhook handler with event processing ([3a66503](https://github.com/aliyevaladddin/AladdinAI/commit/3a66503eaf4c92450e40321b959a44f3dcc7ab46))

- Add AladdinAI bot with reactions and Telegram notifications ([0e5d47e](https://github.com/aliyevaladddin/AladdinAI/commit/0e5d47ed26b9f581f79309fe79374522bfc6b79a))

- Add issue milestone celebrations, mention handling, random PR roasts, and automated reviewer assignment ([efa686b](https://github.com/aliyevaladddin/AladdinAI/commit/efa686bc7b2fa5ee4f7494333ef9e960233f451a))

- Add autonomous AI personality and advanced features to AladdinAI bot ([c19956b](https://github.com/aliyevaladddin/AladdinAI/commit/c19956b43d1f3c4907226afc9a5c34c4c107d37b))

- Add autonomous bot scheduler with morning standup and Friday recap ([637bc4a](https://github.com/aliyevaladddin/AladdinAI/commit/637bc4ab644cb4a66a441c7ca7f8b9efd5e8fc25))

- Add automatic issue assignment functionality for the aladdinai bot ([c372744](https://github.com/aliyevaladddin/AladdinAI/commit/c3727445c7a1af7733516b9a7601e8baa573d370))

- Add user interaction tracking with personalized bot responses ([bdf162c](https://github.com/aliyevaladddin/AladdinAI/commit/bdf162c65a4dfe4a402ce42da6ebadb8bbc29bf5))

- Add repository owner recognition with special treatment ([1c78f25](https://github.com/aliyevaladddin/AladdinAI/commit/1c78f252cc2a7b07448d5c29b796f346ff892af8))


### Refactor

- Migrate terminal routing to Traefik file-provider and unify session management ([11ce753](https://github.com/aliyevaladddin/AladdinAI/commit/11ce7532984b27103384d8ddcc11fac624d8907c))

- Export terminal adapters in init, fix database event import, and remove unused variable in dashboard router ([db99793](https://github.com/aliyevaladddin/AladdinAI/commit/db99793ba82cc3a5e1f8e5f78401739c24b36630))

- Migrate code review agent to use NIM and update generation parameters ([7475fcf](https://github.com/aliyevaladddin/AladdinAI/commit/7475fcfe427b0156c364dd5c0c6cbec22b531c35))

- Update code review agent to use NVIDIA NIM, add file filtering, structured review summaries, and migrate to GitHub App authentication ([b824704](https://github.com/aliyevaladddin/AladdinAI/commit/b8247043367ce68dea121e31cfc4e30326a2bf03))


### Style

- Update README CI and deployment badges to use consistent shield styles ([4f9d65e](https://github.com/aliyevaladddin/AladdinAI/commit/4f9d65e32b9ecd66285c5621c41a40b513ea8ad4))


### Testing

- Add file with intentional issues to trigger code review bot ([deeafb5](https://github.com/aliyevaladddin/AladdinAI/commit/deeafb51ca65e1bb4120fbb9e3be662dfb818565))

- Trigger webhook for AladdinAI bot ([f433b46](https://github.com/aliyevaladddin/AladdinAI/commit/f433b46156df868171de9c8b95067b1db105be6c))

## [v2.0.0] - 2026-05-18

### Bug Fixes

- Prepend venv activation to remote shell commands and restyle terminal container for full-screen layout ([4716399](https://github.com/aliyevaladddin/AladdinAI/commit/47163998252d211249c780cb854ee9ec2d92ed6c))

- Resolve nested buttons in chat and de-duplicate model lists in agents/gates/safety panels ([aadc15a](https://github.com/aliyevaladddin/AladdinAI/commit/aadc15afb4b59b5abdd8cd6eb30d7094f017ec2a))

- PII phases, shared visibility for user facts, NIM timeout ([c3e04e1](https://github.com/aliyevaladddin/AladdinAI/commit/c3e04e17d2f4982ae71a6ea5bd685a9f92ad050d))

- Add exception handling to migration for password_encrypted column in vm_connections ([a5bcf76](https://github.com/aliyevaladddin/AladdinAI/commit/a5bcf76293b990e8c95602edef22324e792f8718))

- Verify signatures on incoming channel webhooks ([a68a79f](https://github.com/aliyevaladddin/AladdinAI/commit/a68a79fd3318d1ddc1262198e2c8dcf509f498c7))

- Block SSRF via user-configured waha_url (#23) ([ab79b14](https://github.com/aliyevaladddin/AladdinAI/commit/ab79b14186b3c96f5da5cf257e62b8ad1967c713))

- Robustness pass on email sync, telegram poller, orchestrator (#24) ([4576d38](https://github.com/aliyevaladddin/AladdinAI/commit/4576d387ce1424fb8dffe72ccf7a18ab4b356402))

- Add contact_id to local Activity interface in crm/[id]/page ([c66cb64](https://github.com/aliyevaladddin/AladdinAI/commit/c66cb64c7442db76bd746b7a9fce8003a01f0775))


### Documentation

- Comprehensive documentation overhaul and CLI refactor ([6df7cfe](https://github.com/aliyevaladddin/AladdinAI/commit/6df7cfeb644505e37218948afb051f30ced171b4))

- Revamp README and ARCHITECTURE for partner outreach; polish login UI ([19d9cad](https://github.com/aliyevaladddin/AladdinAI/commit/19d9cad2f3ba40ecbea960ef81ac0d7e927d38d6))


### Features

- Stabilize terminal lifecycle, fix BentoML deploy & enhance network diagnostics ([f9f40c7](https://github.com/aliyevaladddin/AladdinAI/commit/f9f40c719477b416d19cdfe8e4fd07544af90695))

- Feat: redesign comms/crm/agents pages and add VM password migration
  - Replace mock cyberpunk UI on /comms, /crm, /agents with real API-driven views
  - Match design system used by /channels, /deals (shadcn Button, border-border, muted-foreground)
  - /comms now shows connected messaging channels and email accounts with Test/Sync
  - /crm becomes Contacts list with create form, search, tags, source
  - /agents lists real agents with Start/Stop/Delete and provider join
  - Add Alembic migration adding password_encrypted column to vm_connections ([2d481f0](https://github.com/aliyevaladddin/AladdinAI/commit/2d481f0c16966b68c831e2ea8b1ed8d151625c4d))

- Replace alert() with sonner toasts across dashboard ([e1c7b00](https://github.com/aliyevaladddin/AladdinAI/commit/e1c7b00babf114b3e0de36b4dc61023b7c028aef))

- Replace alert() with sonner toasts in dashboard pages ([f72485d](https://github.com/aliyevaladddin/AladdinAI/commit/f72485dad63d2343d3769feee276291b0e867392))

- Add BentoML deployment schema and implement unified general chat mode in UI ([ced8eac](https://github.com/aliyevaladddin/AladdinAI/commit/ced8eac2a8b89fd23ab1bb42800792e685b2ec78))

- Implement multi-agent delegation system and tool-calling infrastructure ([0dc4f3c](https://github.com/aliyevaladddin/AladdinAI/commit/0dc4f3c1f648201dda6b1ec1dde69cc905884afe))

- Implement gate decision logging and moderation gates ([10f8b15](https://github.com/aliyevaladddin/AladdinAI/commit/10f8b158f59b11f77e59470107bf35edde06b385))

- Per-message extraction, shared-context injection, safety UI, recommended models ([eae42dd](https://github.com/aliyevaladddin/AladdinAI/commit/eae42dd754cb2611ba12bff0f93a9f23651327fd))

- Add user profile endpoint ([e630c86](https://github.com/aliyevaladddin/AladdinAI/commit/e630c86368602248e51d8590bf5ead6c9b2223ac))

- UI panel to list/search/add/delete agent memories ([20e4299](https://github.com/aliyevaladddin/AladdinAI/commit/20e42999744b072695c52c158f8e5f579fdf26aa))

- Cron-scheduled agent tasks via APScheduler ([a2da780](https://github.com/aliyevaladddin/AladdinAI/commit/a2da780c742d4bcd8b45752891904a3143ae4b7b))

- Add automated CLI publishing workflow with version verification ([fef1e82](https://github.com/aliyevaladddin/AladdinAI/commit/fef1e8200dc4db3aab54b7f00eb001072568b787))

- Implement sovereign WhatsApp integration via WAHA with in-dashboard QR code ([05d76e9](https://github.com/aliyevaladddin/AladdinAI/commit/05d76e9e9c8e9bfbc19aea59cd6526b75daa2c06))

- Complete sovereign messaging setup (TG/WA) and security hardening ([21c3647](https://github.com/aliyevaladddin/AladdinAI/commit/21c3647a68590435c723781ffbf61cb54840fb80))

- Add multimodal support for telegram attachments and implement image handling in the orchestrator and agent runner. ([d9f255d](https://github.com/aliyevaladddin/AladdinAI/commit/d9f255df112938c2697092c84773938a77eef5bd))

- Implement scalable image tools and ToolContext.extra channel logic ([a247658](https://github.com/aliyevaladddin/AladdinAI/commit/a24765874c59a869829e2935526deb5153c489a7))

- Implement AI-driven reply suggestions, add search router, and introduce CLI lifecycle and doctor commands. ([2fae7a1](https://github.com/aliyevaladddin/AladdinAI/commit/2fae7a117fbbba9b05606a6a496f95dbb5ef5732))

- Docker-first install via GHCR images ([a6c0a48](https://github.com/aliyevaladddin/AladdinAI/commit/a6c0a480b7c4868d07d96405949bfc50861af443))


### Refactor

- Update BentoML deployment logic and add repository documentation files ([203dd7c](https://github.com/aliyevaladddin/AladdinAI/commit/203dd7cabe41a0eaec9939284f412993edc0a50f))

## [v1.2.0] - 2026-04-30

### Bug Fixes

- Improve CLI download robustness, update cross-platform open command, and bump package versions to 1.2.0 ([827295f](https://github.com/aliyevaladddin/AladdinAI/commit/827295fcc48856d4cc4201353c84d274626b34bd))

## [v1.1.9] - 2026-04-30

### Bug Fixes

- Resolve Windows installation path opening issue and bump version to 1.1.8 ([1e12b27](https://github.com/aliyevaladddin/AladdinAI/commit/1e12b2755355785a42413a8a2a8098dd7943a416))

## [v1.1.7] - 2026-04-30

### Features

- Add publish-cli workflow to automate npm releases ([3ef4a36](https://github.com/aliyevaladddin/AladdinAI/commit/3ef4a36826a9407af4d9f65a0cd835ba10e776f2))

## [v1.1.6] - 2026-04-30

### Bug Fixes

- Clean up workflows and prepare for final release v1.1.6 ([63466b4](https://github.com/aliyevaladddin/AladdinAI/commit/63466b4667601e9b557173f6af091398556506c4))

## [v1.1.5] - 2026-04-30

### CI

- Add ubuntu support and consolidate electron build and artifact collection process ([ba8f12c](https://github.com/aliyevaladddin/AladdinAI/commit/ba8f12c2de611d71e40fa0cd819bb74b18927a0c))

## [v1.1.2] - 2026-04-30

### Bug Fixes

- Final build cleanup - remove deprecated next export command ([1c719ba](https://github.com/aliyevaladddin/AladdinAI/commit/1c719bac5d52aa647e989408b3a1b0ea434c8bf0))

## [v1.1.1] - 2026-04-30

### Bug Fixes

- Final build hardening (TS generics, null token support, CSS native patterns) ([2c6b2a4](https://github.com/aliyevaladddin/AladdinAI/commit/2c6b2a4b01de88e5b397b62e9e2738597254315b))

## [v1.1.0] - 2026-04-30

### Bug Fixes

- Add token management methods to api client ([511dfb7](https://github.com/aliyevaladddin/AladdinAI/commit/511dfb7a34ffced1ff5499e12d24b738689a7e8b))

## [v1.0.9] - 2026-04-30

### Bug Fixes

- Make API body optional for POST/PUT and support all CRUD methods ([c74c354](https://github.com/aliyevaladddin/AladdinAI/commit/c74c35416021aa92ced0d100a24e98fa905ae27a))

## [v1.0.8] - 2026-04-30

### Features

- Implement full CRUD support in api utility by adding post, put, and delete methods ([2e6d672](https://github.com/aliyevaladddin/AladdinAI/commit/2e6d6728721e51597b9d8441933d7f81b0f4a807))

## [v1.0.7] - 2026-04-30

### Bug Fixes

- Add generic support to api client to resolve TS errors ([eccaa28](https://github.com/aliyevaladddin/AladdinAI/commit/eccaa2845e7b5d6e3c3e113fcb43da9350a4842a))

## [v1.0.6] - 2026-04-30

### Bug Fixes

- Move selection styles to native CSS for Tailwind v4 compatibility ([1c6d4f2](https://github.com/aliyevaladddin/AladdinAI/commit/1c6d4f25c851d14907d0e9c328c9768870c14f20))

## [v1.0.5] - 2026-04-30

### Ix

- Final resolve for Tailwind v4 CSS build errors ([2779da4](https://github.com/aliyevaladddin/AladdinAI/commit/2779da467e86fdb6a053cc2f12714d800cd9efde))

## [v1.0.4] - 2026-04-30

### Bug Fixes

- Resolve Tailwind v4 utility errors and rename Sidebar to SovereignSidebar ([d7ef76a](https://github.com/aliyevaladddin/AladdinAI/commit/d7ef76a07a7951e1375ed54684bbb918e631a724))

## [v1.0.3] - 2026-04-30

### Features

- Export api compatibility object and update CI to use npm install ([ea1dc00](https://github.com/aliyevaladddin/AladdinAI/commit/ea1dc00c8c5b94f28f6945742e19994f8b1f45fb))

## [v1.0.2] - 2026-04-30

### Bug Fixes

- Use rcf-cli audit command instead of scan ([9146fcb](https://github.com/aliyevaladddin/AladdinAI/commit/9146fcb2b8ec0c0b2a0ce5cbbeba56597e9d6ec7))

- Add publishConfig for npm ([58ffc6b](https://github.com/aliyevaladddin/AladdinAI/commit/58ffc6b7626f2d038611968618350adf05ea5ef7))

- Use correct npm scope @aladdinaliyev ([88cb8ca](https://github.com/aliyevaladddin/AladdinAI/commit/88cb8ca3268b195c3230b88464f16a3f3062451f))


### CI

- Allow npm publish from feature branch for testing ([9b4de16](https://github.com/aliyevaladddin/AladdinAI/commit/9b4de16e7a9662515ac4f51c364559d4102237de))

- Trigger npm publish workflow on changes to its own configuration file ([1769cb5](https://github.com/aliyevaladddin/AladdinAI/commit/1769cb5efa1405f49cd332b9b5cbd44752ca2455))

- Sync npm publish config with working rcf-protocol setup ([0bb6d3b](https://github.com/aliyevaladddin/AladdinAI/commit/0bb6d3b6f6d602177d00fdf588aff91eef1e8fd3))

- Update npm publish workflow to target typescript SDK and add release trigger ([2177ec2](https://github.com/aliyevaladddin/AladdinAI/commit/2177ec2cc3ad3562f65db4dbbcc4316b8e91a1c0))

- Switch RCF audit to npm rcf-protocol ([875022d](https://github.com/aliyevaladddin/AladdinAI/commit/875022de301d46418d1374836555f6cb3c96c428))


### Documentation

- Update README with project badges, feature list, and contribution guidelines, and finalize LICENSE copyright notice ([7f08f0d](https://github.com/aliyevaladddin/AladdinAI/commit/7f08f0d74b838892630c7124cef97fe6a94a441c))

- Update quick start command and add native desktop app benefits to README ([cc09841](https://github.com/aliyevaladddin/AladdinAI/commit/cc0984118547cbea1227b4c44a7c31062c98f3a7))


### Features

- Project structure initialization (FastAPI backend and Next.js frontend) ([bcde134](https://github.com/aliyevaladddin/AladdinAI/commit/bcde134b5600893fbdf198581eb99e8c8514e401))

- Feat: real VM SSH connect & LLM provider API connect/disconnect
- Replace TODO SSH stub with asyncssh.connect() real connection
- Add POST /vms/{id}/connect and /disconnect endpoints
- Persist VM status (connected/disconnected) in DB after SSH test
- Replace provider test stub with real GET /v1/models API call
- Persist provider status and models_available in DB on success
- Add POST /providers/{id}/connect and /disconnect endpoints
- Frontend: Connect/Disconnect toggle buttons based on real DB status
- Frontend: Live inline feedback (success/error/loading) per card
- Frontend: SSH private key textarea in VM form
- Add asyncssh==2.18.0 to requirements.txt ([5acf073](https://github.com/aliyevaladddin/AladdinAI/commit/5acf073656487a1ef97b817ab306485068959660))

- Add dynamic model loading, persistent chat sessions, and visual router config ([a94fc3b](https://github.com/aliyevaladddin/AladdinAI/commit/a94fc3bbf03dac958142361ff42c4c510d707bbd))

- Implement RCF Protocol (Restricted Correlation) and Outgoing Webhooks ([cc543f4](https://github.com/aliyevaladddin/AladdinAI/commit/cc543f4ebd3013099b22c9662f9a590072003403))

- Integrate Electron for desktop support and upgrade aladdin-ai CLI installer ([2e08faa](https://github.com/aliyevaladddin/AladdinAI/commit/2e08faa34159432650cd920ece99144cb0647e76))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([f92b971](https://github.com/aliyevaladddin/AladdinAI/commit/f92b971bd9157856183b3f18e8306ae709914192))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([63a2087](https://github.com/aliyevaladddin/AladdinAI/commit/63a20871402a6518d0c78ec4a5097f6ede1cfb2c))

- Rename package to aladdin-ai for clean npx command ([e008f43](https://github.com/aliyevaladddin/AladdinAI/commit/e008f43385fb3b019310dfa32545f21e99e2a330))

- Complete SOVEREIGN_CMD transformation (UI, Backend Stats, Desktop Build) ([d70dd1a](https://github.com/aliyevaladddin/AladdinAI/commit/d70dd1a9623b75e101de301ccbf4bf2d95e8338c))


### Hore

- Publish under @auroraaccess organization ([d275662](https://github.com/aliyevaladddin/AladdinAI/commit/d275662f5ccf80dddaae66614517938be158ce95))

<!-- Generated by git-cliff -->
