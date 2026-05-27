# Changelog


### Bug fixes

- Replace git-cliff-action with direct binary ([5a62536](https://github.com/aliyevaladddin/AladdinAI/commit/5a62536cc14d94ba376c26076e5fb7a3ce020ee8))

- Add write permissions to changelog workflow ([43351d4](https://github.com/aliyevaladddin/AladdinAI/commit/43351d487c13feaddd3709993913eb41b008d5d3))


### Docs

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


### Refactor

- Migrate terminal routing to Traefik file-provider and unify session management ([11ce753](https://github.com/aliyevaladddin/AladdinAI/commit/11ce7532984b27103384d8ddcc11fac624d8907c))

- Export terminal adapters in init, fix database event import, and remove unused variable in dashboard router ([db99793](https://github.com/aliyevaladddin/AladdinAI/commit/db99793ba82cc3a5e1f8e5f78401739c24b36630))


### Bug fixes

- Prepend venv activation to remote shell commands and restyle terminal container for full-screen layout ([4716399](https://github.com/aliyevaladddin/AladdinAI/commit/47163998252d211249c780cb854ee9ec2d92ed6c))

- Resolve nested buttons in chat and de-duplicate model lists in agents/gates/safety panels ([aadc15a](https://github.com/aliyevaladddin/AladdinAI/commit/aadc15afb4b59b5abdd8cd6eb30d7094f017ec2a))

- PII phases, shared visibility for user facts, NIM timeout ([c3e04e1](https://github.com/aliyevaladddin/AladdinAI/commit/c3e04e17d2f4982ae71a6ea5bd685a9f92ad050d))

- Add exception handling to migration for password_encrypted column in vm_connections ([a5bcf76](https://github.com/aliyevaladddin/AladdinAI/commit/a5bcf76293b990e8c95602edef22324e792f8718))

- Verify signatures on incoming channel webhooks ([a68a79f](https://github.com/aliyevaladddin/AladdinAI/commit/a68a79fd3318d1ddc1262198e2c8dcf509f498c7))

- Block SSRF via user-configured waha_url (#23) ([ab79b14](https://github.com/aliyevaladddin/AladdinAI/commit/ab79b14186b3c96f5da5cf257e62b8ad1967c713))

- Robustness pass on email sync, telegram poller, orchestrator (#24) ([4576d38](https://github.com/aliyevaladddin/AladdinAI/commit/4576d387ce1424fb8dffe72ccf7a18ab4b356402))

- Add contact_id to local Activity interface in crm/[id]/page ([c66cb64](https://github.com/aliyevaladddin/AladdinAI/commit/c66cb64c7442db76bd746b7a9fce8003a01f0775))


### Docs

- Comprehensive documentation overhaul and CLI refactor ([6df7cfe](https://github.com/aliyevaladddin/AladdinAI/commit/6df7cfeb644505e37218948afb051f30ced171b4))

- Revamp README and ARCHITECTURE for partner outreach; polish login UI ([19d9cad](https://github.com/aliyevaladddin/AladdinAI/commit/19d9cad2f3ba40ecbea960ef81ac0d7e927d38d6))


### Features

- Stabilize terminal lifecycle, fix BentoML deploy & enhance network diagnostics ([f9f40c7](https://github.com/aliyevaladddin/AladdinAI/commit/f9f40c719477b416d19cdfe8e4fd07544af90695))

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


### Bug fixes

- Improve CLI download robustness, update cross-platform open command, and bump package versions to 1.2.0 ([827295f](https://github.com/aliyevaladddin/AladdinAI/commit/827295fcc48856d4cc4201353c84d274626b34bd))


### Bug fixes

- Resolve Windows installation path opening issue and bump version to 1.1.8 ([1e12b27](https://github.com/aliyevaladddin/AladdinAI/commit/1e12b2755355785a42413a8a2a8098dd7943a416))


### Features

- Add publish-cli workflow to automate npm releases ([3ef4a36](https://github.com/aliyevaladddin/AladdinAI/commit/3ef4a36826a9407af4d9f65a0cd835ba10e776f2))


### Bug fixes

- Clean up workflows and prepare for final release v1.1.6 ([63466b4](https://github.com/aliyevaladddin/AladdinAI/commit/63466b4667601e9b557173f6af091398556506c4))


### Ci

- Add ubuntu support and consolidate electron build and artifact collection process ([ba8f12c](https://github.com/aliyevaladddin/AladdinAI/commit/ba8f12c2de611d71e40fa0cd819bb74b18927a0c))


### Bug fixes

- Final build cleanup - remove deprecated next export command ([1c719ba](https://github.com/aliyevaladddin/AladdinAI/commit/1c719bac5d52aa647e989408b3a1b0ea434c8bf0))


### Bug fixes

- Final build hardening (TS generics, null token support, CSS native patterns) ([2c6b2a4](https://github.com/aliyevaladddin/AladdinAI/commit/2c6b2a4b01de88e5b397b62e9e2738597254315b))


### Bug fixes

- Add token management methods to api client ([511dfb7](https://github.com/aliyevaladddin/AladdinAI/commit/511dfb7a34ffced1ff5499e12d24b738689a7e8b))


### Bug fixes

- Make API body optional for POST/PUT and support all CRUD methods ([c74c354](https://github.com/aliyevaladddin/AladdinAI/commit/c74c35416021aa92ced0d100a24e98fa905ae27a))


### Features

- Implement full CRUD support in api utility by adding post, put, and delete methods ([2e6d672](https://github.com/aliyevaladddin/AladdinAI/commit/2e6d6728721e51597b9d8441933d7f81b0f4a807))


### Bug fixes

- Add generic support to api client to resolve TS errors ([eccaa28](https://github.com/aliyevaladddin/AladdinAI/commit/eccaa2845e7b5d6e3c3e113fcb43da9350a4842a))


### Bug fixes

- Move selection styles to native CSS for Tailwind v4 compatibility ([1c6d4f2](https://github.com/aliyevaladddin/AladdinAI/commit/1c6d4f25c851d14907d0e9c328c9768870c14f20))


### Ix

- Final resolve for Tailwind v4 CSS build errors ([2779da4](https://github.com/aliyevaladddin/AladdinAI/commit/2779da467e86fdb6a053cc2f12714d800cd9efde))


### Bug fixes

- Resolve Tailwind v4 utility errors and rename Sidebar to SovereignSidebar ([d7ef76a](https://github.com/aliyevaladddin/AladdinAI/commit/d7ef76a07a7951e1375ed54684bbb918e631a724))


### Features

- Export api compatibility object and update CI to use npm install ([ea1dc00](https://github.com/aliyevaladddin/AladdinAI/commit/ea1dc00c8c5b94f28f6945742e19994f8b1f45fb))


### Bug fixes

- Use rcf-cli audit command instead of scan ([9146fcb](https://github.com/aliyevaladddin/AladdinAI/commit/9146fcb2b8ec0c0b2a0ce5cbbeba56597e9d6ec7))

- Add publishConfig for npm ([58ffc6b](https://github.com/aliyevaladddin/AladdinAI/commit/58ffc6b7626f2d038611968618350adf05ea5ef7))

- Use correct npm scope @aladdinaliyev ([88cb8ca](https://github.com/aliyevaladddin/AladdinAI/commit/88cb8ca3268b195c3230b88464f16a3f3062451f))


### Ci

- Allow npm publish from feature branch for testing ([9b4de16](https://github.com/aliyevaladddin/AladdinAI/commit/9b4de16e7a9662515ac4f51c364559d4102237de))

- Trigger npm publish workflow on changes to its own configuration file ([1769cb5](https://github.com/aliyevaladddin/AladdinAI/commit/1769cb5efa1405f49cd332b9b5cbd44752ca2455))

- Sync npm publish config with working rcf-protocol setup ([0bb6d3b](https://github.com/aliyevaladddin/AladdinAI/commit/0bb6d3b6f6d602177d00fdf588aff91eef1e8fd3))

- Update npm publish workflow to target typescript SDK and add release trigger ([2177ec2](https://github.com/aliyevaladddin/AladdinAI/commit/2177ec2cc3ad3562f65db4dbbcc4316b8e91a1c0))

- Switch RCF audit to npm rcf-protocol ([875022d](https://github.com/aliyevaladddin/AladdinAI/commit/875022de301d46418d1374836555f6cb3c96c428))


### Docs

- Update README with project badges, feature list, and contribution guidelines, and finalize LICENSE copyright notice ([7f08f0d](https://github.com/aliyevaladddin/AladdinAI/commit/7f08f0d74b838892630c7124cef97fe6a94a441c))

- Update quick start command and add native desktop app benefits to README ([cc09841](https://github.com/aliyevaladddin/AladdinAI/commit/cc0984118547cbea1227b4c44a7c31062c98f3a7))


### Features

- Project structure initialization (FastAPI backend and Next.js frontend) ([bcde134](https://github.com/aliyevaladddin/AladdinAI/commit/bcde134b5600893fbdf198581eb99e8c8514e401))

- Add dynamic model loading, persistent chat sessions, and visual router config ([a94fc3b](https://github.com/aliyevaladddin/AladdinAI/commit/a94fc3bbf03dac958142361ff42c4c510d707bbd))

- Implement RCF Protocol (Restricted Correlation) and Outgoing Webhooks ([cc543f4](https://github.com/aliyevaladddin/AladdinAI/commit/cc543f4ebd3013099b22c9662f9a590072003403))

- Integrate Electron for desktop support and upgrade aladdin-ai CLI installer ([2e08faa](https://github.com/aliyevaladddin/AladdinAI/commit/2e08faa34159432650cd920ece99144cb0647e76))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([f92b971](https://github.com/aliyevaladddin/AladdinAI/commit/f92b971bd9157856183b3f18e8306ae709914192))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([63a2087](https://github.com/aliyevaladddin/AladdinAI/commit/63a20871402a6518d0c78ec4a5097f6ede1cfb2c))

- Rename package to aladdin-ai for clean npx command ([e008f43](https://github.com/aliyevaladddin/AladdinAI/commit/e008f43385fb3b019310dfa32545f21e99e2a330))

- Complete SOVEREIGN_CMD transformation (UI, Backend Stats, Desktop Build) ([d70dd1a](https://github.com/aliyevaladddin/AladdinAI/commit/d70dd1a9623b75e101de301ccbf4bf2d95e8338c))


### Hore

- Publish under @auroraaccess organization ([d275662](https://github.com/aliyevaladddin/AladdinAI/commit/d275662f5ccf80dddaae66614517938be158ce95))

