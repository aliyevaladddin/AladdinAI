# Changelog

All notable changes to AladdinAI will be documented in this file. This changelog follows the conventional commits specification.

## [Unreleased]

### Bug Fixes

- Remove 16 of 19 type: ignore suppressions in backend ([d704540](https://github.com/aliyevaladddin/AladdinAI/commit/d70454019c891aa4506060d55e1c30b21dbcc50a))

- Replace 23 of 26 any types with proper TypeScript types (#714) ([5f450c6](https://github.com/aliyevaladddin/AladdinAI/commit/5f450c6f3a8a1cbe0a12efffca384eb3267cec94))

- Repair C terminal JSON parsing — key leak and \uXXXX esc… (#737) ([9799aa0](https://github.com/aliyevaladddin/AladdinAI/commit/9799aa0601d541be89c7c18132bfc9165965eb31))

- Content-Disposition injection + rate limits on upload/MCP test (#752) ([7321117](https://github.com/aliyevaladddin/AladdinAI/commit/7321117c5037cd8b804a955324211612c3cf53d2))

- Remove duplicate modal state declarations in files page (#764) ([1caafed](https://github.com/aliyevaladddin/AladdinAI/commit/1caafed012b3e4070748860d05536bad812bd065))


### CI

- Test NIM model upgrade to llama-3.3 (#755) ([5ffa5d5](https://github.com/aliyevaladddin/AladdinAI/commit/5ffa5d501dcf38a37f7de0e7c369d4a737719e62))


### Dependencies

- Bump python-docx from 1.1.2 to 1.2.0 (#766) ([453a921](https://github.com/aliyevaladddin/AladdinAI/commit/453a921529d99ca1b625cf785eb7a4a849f968ab))

- Bump pypdf from 6.15.0 to 6.16.2 (#767) ([c538243](https://github.com/aliyevaladddin/AladdinAI/commit/c53824382663631aa696660042bb60009263ceb6))

- Bump the security-patches group across 1 directory with 6 updates (#768) ([2fae7ad](https://github.com/aliyevaladddin/AladdinAI/commit/2fae7adbcf344a4a32c41ebdda9d8a7804bd58ae))

- Bump shadcn from 4.17.0 to 4.19.0 in /frontend (#771) ([2f36ac6](https://github.com/aliyevaladddin/AladdinAI/commit/2f36ac6bd7c481eeda8eebd0718d8f920271b398))

- Bump lucide-react from 1.31.0 to 1.34.0 in /frontend (#772) ([9c4c45b](https://github.com/aliyevaladddin/AladdinAI/commit/9c4c45b2486695bdd5443e52fd01b3609cd5e33c))


### Documentation

- Update API documentation [skip ci] (#713) ([43cce1c](https://github.com/aliyevaladddin/AladdinAI/commit/43cce1cf0cb41fbd95e395d2753769615f519c5a))

- Add guides for SQL playground, terminal system, web search, triggers (#731) ([3337dbe](https://github.com/aliyevaladddin/AladdinAI/commit/3337dbea1bc99ba312d2c3b402292f42e67dbec1))

- Update API documentation [skip ci] (#744) ([605c429](https://github.com/aliyevaladddin/AladdinAI/commit/605c429000e8e8726111da2ba8c06256ba6caa8e))

- Add File Workspace documentation, architectural design record, and README links (#745) ([4bb0fbd](https://github.com/aliyevaladddin/AladdinAI/commit/4bb0fbdf88779132f623648729708675e160d19f))

- Update API documentation [skip ci] (#749) ([2fdf077](https://github.com/aliyevaladddin/AladdinAI/commit/2fdf077ba7a459e3aeabc7ff2089f30851bc25d6))

- Add MCP Servers guide (#750) ([cb7aea7](https://github.com/aliyevaladddin/AladdinAI/commit/cb7aea7cb180c030c72c271b4f4dee202799489b))

- Update API documentation [skip ci] (#760) ([6e0ba62](https://github.com/aliyevaladddin/AladdinAI/commit/6e0ba62c8ae76b87901b4ee9ff67eb18db0bf54d))

- Update API documentation [skip ci] (#763) ([f5e02c0](https://github.com/aliyevaladddin/AladdinAI/commit/f5e02c063ba7cc70b18ce329ed74de04dc7248af))


### Features

- Add error boundaries and loading skeletons to all dashboard pages (#723) ([fd2f865](https://github.com/aliyevaladddin/AladdinAI/commit/fd2f865f0c732c499b2ad04cdf03491e9fb1f0ec))

- Native C binaries in prod image, Settings tab, tests (#733) ([34b8e5f](https://github.com/aliyevaladddin/AladdinAI/commit/34b8e5fe5a0cb428b840269671185273612896d3))

- File workspace — spaces, append-only versions, audit tim… (#742) ([5a21a44](https://github.com/aliyevaladddin/AladdinAI/commit/5a21a44234770ab9cf2509836451e0291ba0c38f))

- Native MCP client, per-agent server picker, and server catalog (#747) ([1d1fb65](https://github.com/aliyevaladddin/AladdinAI/commit/1d1fb65319fffbfdfd110d9e531189625fe5f019))

- Batch polish — modals, boundaries, 72 tests, SSH key, pagination (#757) ([13d4f8d](https://github.com/aliyevaladddin/AladdinAI/commit/13d4f8d21cfba31db12b405543fa19680c735cbe))

- Add WRT editor and embedding model fallback chains (#790) ([babe7bc](https://github.com/aliyevaladddin/AladdinAI/commit/babe7bc34bf0b5780381d6fec6b07fcf2461d2e2))


### Maintenance

- Bump version to 2.2.5 and update deps [skip ci] ([f2f404c](https://github.com/aliyevaladddin/AladdinAI/commit/f2f404cf94bca10ea83f5574e4a91fd1d03bb5ff))

- Update changelog [skip ci] (#712) ([3a19f0f](https://github.com/aliyevaladddin/AladdinAI/commit/3a19f0ffa398033c6c7b25c4cc3ab9e889582f05))

- Update changelog [skip ci] (#715) ([0894613](https://github.com/aliyevaladddin/AladdinAI/commit/0894613da95e53efbd170d4ba7755958e6698233))

- Update changelog [skip ci] (#724) ([2de0bf6](https://github.com/aliyevaladddin/AladdinAI/commit/2de0bf686fc95fc011d8563e1dcb020e83aa3bd0))

- Update changelog [skip ci] (#726) ([bd24036](https://github.com/aliyevaladddin/AladdinAI/commit/bd24036ac12bf31cdcb1fd92ac9dcc454d7f1c39))

- Update changelog [skip ci] (#728) ([d7d5357](https://github.com/aliyevaladddin/AladdinAI/commit/d7d5357c6d67676e9c0b87767b204ce26d43943d))

- Update changelog [skip ci] (#730) ([031d18b](https://github.com/aliyevaladddin/AladdinAI/commit/031d18b7c24b188c132a8dad5bbd806a404971b0))

- Update changelog [skip ci] (#732) ([5c986a9](https://github.com/aliyevaladddin/AladdinAI/commit/5c986a9a9fe06c4e392bf390505abd919dacd276))

- Update changelog [skip ci] (#734) ([1079001](https://github.com/aliyevaladddin/AladdinAI/commit/1079001b751b63fd6150db85eab2701c99b30ada))

- Update changelog [skip ci] (#735) ([c5242d7](https://github.com/aliyevaladddin/AladdinAI/commit/c5242d72ea089babe6bdc62a48890bfdd1360670))

- Update changelog [skip ci] (#738) ([7d30898](https://github.com/aliyevaladddin/AladdinAI/commit/7d30898a32bb08b85f49683a8fbe9e0237deb766))

- Update changelog (#736) ([f2b1609](https://github.com/aliyevaladddin/AladdinAI/commit/f2b1609d98bf9204a995a64e29117709e87a3b16))

- Update changelog [skip ci] (#739) ([883c04f](https://github.com/aliyevaladddin/AladdinAI/commit/883c04f244990dc122e0282f6a95ba657071baa9))

- Update changelog [skip ci] (#743) ([13695d3](https://github.com/aliyevaladddin/AladdinAI/commit/13695d3877032a6d048ca4d5885b1045512de195))

- Update changelog [skip ci] (#746) ([a2b0266](https://github.com/aliyevaladddin/AladdinAI/commit/a2b02660ddcf28edd8bca653d731c0401dc38efa))

- Update changelog [skip ci] (#748) ([ddb6d24](https://github.com/aliyevaladddin/AladdinAI/commit/ddb6d24439871455f8d513a8c81b62b8cd1390a9))

- Update changelog [skip ci] (#751) ([2cd1f48](https://github.com/aliyevaladddin/AladdinAI/commit/2cd1f489c7ff8c1c99ebba26a2f4518756843c3a))

- Update changelog [skip ci] (#754) ([ce112ef](https://github.com/aliyevaladddin/AladdinAI/commit/ce112ef4478e938795f8f99f523d9c2ad3b94234))

- Update changelog [skip ci] (#756) ([23c00d4](https://github.com/aliyevaladddin/AladdinAI/commit/23c00d43c4c38a621db46eda5239129e0bc29380))

- Update changelog [skip ci] (#759) ([72e6109](https://github.com/aliyevaladddin/AladdinAI/commit/72e61095ff1439027c1c6b8d06f49c4c121468a9))

- Update changelog [skip ci] (#762) ([0a1c5e3](https://github.com/aliyevaladddin/AladdinAI/commit/0a1c5e3ff3eafc4830fe9ac5a0a1ac554106544f))

- Update changelog [skip ci] (#765) ([4278818](https://github.com/aliyevaladddin/AladdinAI/commit/427881880ff35c83870f64588333760b0ef6e22f))

- Bump electron from 43.4.0 to 44.0.0 in /frontend (#773) ([c90e87f](https://github.com/aliyevaladddin/AladdinAI/commit/c90e87fd4ab93cbe0d8a863c81331538fecfe986))

- Update package-lock.json dependencies (#775) ([06a9f62](https://github.com/aliyevaladddin/AladdinAI/commit/06a9f62cf4d0f7447ae9c867b32506a4ed32deae))

- Bump eslint from 10.8.1 to 10.9.1 in /frontend (#769) ([e9ed7be](https://github.com/aliyevaladddin/AladdinAI/commit/e9ed7be8b0018a5d99318d252574bd274f424cb6))

- Bump @types/node from 26.2.0 to 26.3.0 in /frontend (#770) ([d338525](https://github.com/aliyevaladddin/AladdinAI/commit/d338525f6d143a2d71c1eb99c45aff14a4d57263))

- Update lockfile dependencies (#782) ([7e30fe4](https://github.com/aliyevaladddin/AladdinAI/commit/7e30fe4483d5f9a9140117f16086ed3d9cfea082))

- Update lockfile dependencies for frontend package-lock.json (#785) ([14e1af9](https://github.com/aliyevaladddin/AladdinAI/commit/14e1af9d50c6bec2742f2093b64191a276a3245c))

- Update lockfile dependencies (#788) ([c79191d](https://github.com/aliyevaladddin/AladdinAI/commit/c79191d3514a239a0777178552ee8a8c00ae88db))

- Update changelog [skip ci] (#789) ([3f73c05](https://github.com/aliyevaladddin/AladdinAI/commit/3f73c05b5c3d0ee9de7e198fa584bd901d097aa4))


### Refactor

- Unified TerminalBackend abstraction (stage A) ([a238145](https://github.com/aliyevaladddin/AladdinAI/commit/a238145a77eb351e0dec245f1b40229382f53537))

## [v2.2.5] - 2026-08-21

### Bug Fixes

- VoicePlayer tokens, terminal TabBar, code block hex, reports colors, blob cache ([5c1c452](https://github.com/aliyevaladddin/AladdinAI/commit/5c1c4523db4be2a6864285087446f644bf7137ef))

- Remove false positive CodeQL URL-substring warning in test ([dbe68a6](https://github.com/aliyevaladddin/AladdinAI/commit/dbe68a683b604b21412a55af29b17211fb369198))

- Add python symlink and env for node-gyp in Docker build ([fa25dc5](https://github.com/aliyevaladddin/AladdinAI/commit/fa25dc55141436888f2b03c03ef06f7364d71251))

- Critical security and reliability issues (#668) ([0d3a0a6](https://github.com/aliyevaladddin/AladdinAI/commit/0d3a0a6ebac18934752d8081316968c9ebe4c987))

- Critical production issues — hardcoded port, blocking event loop, readiness probe (#672) ([1ece654](https://github.com/aliyevaladddin/AladdinAI/commit/1ece654f72a1caab45206a5693661441b736c3ad))

- Add loading states, OpenAPI tags, silent-except logging, and internal links (#675) ([82f536f](https://github.com/aliyevaladddin/AladdinAI/commit/82f536f6483010ad4fee293ce34f2a64f36784f5))

- Pydantic V2 ConfigDict, silent exceptions, json.loads safety, input validation ([d6408b0](https://github.com/aliyevaladddin/AladdinAI/commit/d6408b0441f813793f09d1257e8156da441cb425))

- Hydration error — nested buttons in trace panels ([0cc6a2f](https://github.com/aliyevaladddin/AladdinAI/commit/0cc6a2f021c21909e5d9e92a8cfab4b7b8c20061))

- Move logging import after other imports (ruff E402) ([ad71e2d](https://github.com/aliyevaladddin/AladdinAI/commit/ad71e2d248e7bef602345656a662005dcce553c4))

- Invalidate API cache on PUT/PATCH/DELETE mutations ([1063e41](https://github.com/aliyevaladddin/AladdinAI/commit/1063e4146a0225a6b316391365342f8a9500b819))

- Also invalidate cache on POST (new resource creation) ([736c43e](https://github.com/aliyevaladddin/AladdinAI/commit/736c43e0c8cb7947f0ff812b8157aa0c59547a01))

- Remove Gates 24h from status bar (always 0 when gates disabled) ([9d49e1f](https://github.com/aliyevaladddin/AladdinAI/commit/9d49e1f2a87d3aa11f7e6af5e2017703756c949a))

- Critical security and reliability issues ([8bd9f72](https://github.com/aliyevaladddin/AladdinAI/commit/8bd9f726884062daed18c078d614622bc919e941))

- Error boundaries, rate limiting, and print→log ([f7bc51d](https://github.com/aliyevaladddin/AladdinAI/commit/f7bc51d338be9e21aca11ba00366f30bcdff2b77))

- DuckDuckGo search returning 0 web results ([158ed28](https://github.com/aliyevaladddin/AladdinAI/commit/158ed28d31be905640b5e23b6666b34b5bed6b6c))

- Move log import after all imports in terminal_providers (ruff E402) ([31877db](https://github.com/aliyevaladddin/AladdinAI/commit/31877dbd028abe8ee296d663bd64b5c6e4dedc7a))

- Add loading states, OpenAPI tags, silent-except logging, and internal links ([2b69790](https://github.com/aliyevaladddin/AladdinAI/commit/2b69790da72a42119e045787133a8ec77b89d7ff))

- Correct changelog bot noreply identity for contributor attribution ([ada866e](https://github.com/aliyevaladddin/AladdinAI/commit/ada866e57737d3cc9d2ff21224ebc065586ad341))

- Critical production issues — hardcoded port, blocking event loop, readiness probe ([1fc6bb6](https://github.com/aliyevaladddin/AladdinAI/commit/1fc6bb6bc1c72ce4a6b0ad2ad199227c09d9d696))

- Replace known_hosts=None with TOFU verification (issue #356) ([46040d7](https://github.com/aliyevaladddin/AladdinAI/commit/46040d7166cbf049b14c13f297d466d7d0a11ab3))

- Telegram photo bytes, doctor DB check, add Cursor contributor ([7b80c00](https://github.com/aliyevaladddin/AladdinAI/commit/7b80c00b3615cc29b369b777a77dcb7e5a12e556))

- Nested button hydration error in agent traces panel ([172e909](https://github.com/aliyevaladddin/AladdinAI/commit/172e9094a450ec44aa158a1339380f6fb1b5661a))

- Direct push to main so bot appears in contributors ([2e3faba](https://github.com/aliyevaladddin/AladdinAI/commit/2e3faba8c8bb75c5324bfcb764d47b55eed79f62))

- Resolve bot ID via public /users endpoint ([874a640](https://github.com/aliyevaladddin/AladdinAI/commit/874a640e1320b834f0c7a2156d2f7efbe681efc0))


### Documentation

- Update API documentation [skip ci] (#639) ([93bccb8](https://github.com/aliyevaladddin/AladdinAI/commit/93bccb8e5554dd51e6383f145c1a2a3a12bf1ac9))

- UI polish, chat perf, tracing & forging guide ([30eb502](https://github.com/aliyevaladddin/AladdinAI/commit/30eb502b457a67bf9cc118a3e51baacdca2798db))

- Update API documentation [skip ci] (#644) ([77414fe](https://github.com/aliyevaladddin/AladdinAI/commit/77414fe84fecbf12b741ff233db57fb8812ffadb))

- Update API documentation [skip ci] (#650) ([e4637fe](https://github.com/aliyevaladddin/AladdinAI/commit/e4637feb0c7dc0245b71e10e9ba12a37543d521a))

- Add agent sandbox architecture guide ([f24c117](https://github.com/aliyevaladddin/AladdinAI/commit/f24c1178d72380f95369b40945a3f7d132da5350))

- Update API documentation [skip ci] (#674) ([85272b0](https://github.com/aliyevaladddin/AladdinAI/commit/85272b0d136958a9455c77151b999cb741e70cf1))

- Update API documentation [skip ci] (#677) ([d50fc14](https://github.com/aliyevaladddin/AladdinAI/commit/d50fc143115e8c1a7ad560d4401d6a62a4f5d093))

- Add Antigravity to contributors list ([7828c8e](https://github.com/aliyevaladddin/AladdinAI/commit/7828c8e40259328571aebac15ba00d6ddeb2898f))

- Add visual contributors table with avatars in README ([c19855d](https://github.com/aliyevaladddin/AladdinAI/commit/c19855d5d6da8a91d7dbe75dce5a04330ccf77af))

- Update architecture, testing, and backend docs ([2bf490e](https://github.com/aliyevaladddin/AladdinAI/commit/2bf490e72a2321b711d2911dae1382776a7f2177))

- Add Antigravity contributor profile with link in README ([a22c2e7](https://github.com/aliyevaladddin/AladdinAI/commit/a22c2e764edd3b359f2d895689abe75ca691e6a9))

- Update API documentation [skip ci] (#691) ([974067d](https://github.com/aliyevaladddin/AladdinAI/commit/974067d01750a3746c4c8134b6bc66aaa82bcbda))

- Update dashboard-nav comment to reflect moved tabs ([d9932dc](https://github.com/aliyevaladddin/AladdinAI/commit/d9932dcbd5577aa5c4a8d6b2b8128c1dc65d90a8))


### Features

- Per-turn agent trace view in the UI (#637) ([2253c23](https://github.com/aliyevaladddin/AladdinAI/commit/2253c2333c9e1f54868c1878281893c8debb980c))

- Tracing toggle, global traces page, trace feedback, Self-Forging UI (#642) ([9e03385](https://github.com/aliyevaladddin/AladdinAI/commit/9e03385982e73cec9b9a78d7b9443fba7088c4e4))

- Add Traefik health checks to Docker services and include SOFA usage documentation ([ac6c057](https://github.com/aliyevaladddin/AladdinAI/commit/ac6c057474ad12d9227ac76e0a01f1c0b7ab6e83))

- Add Qwen bot activity job and fix bot commit attribution ([a2b0b16](https://github.com/aliyevaladddin/AladdinAI/commit/a2b0b16d5f94f9f212b86672fa2387f02790fdf8))

- Per-turn agent trace view in the UI ([7b6e7cc](https://github.com/aliyevaladddin/AladdinAI/commit/7b6e7cc840fa807f22c40b08144035067dfc5634))

- Tracing toggle, global traces page, trace feedback, Self-Forging UI ([a5c4cbe](https://github.com/aliyevaladddin/AladdinAI/commit/a5c4cbe12eb690b1ec68813b7a4950e3b5add783))

- Fix broken design tokens and polish dashboard UI ([c35e4d0](https://github.com/aliyevaladddin/AladdinAI/commit/c35e4d0842052362266bf255cd56d6fb1f4cb908))


### Maintenance

- Bump version to 2.2.4 and update deps [skip ci] ([b316572](https://github.com/aliyevaladddin/AladdinAI/commit/b316572996e5eaef139c2334a14c3b44bb59f159))

- Update changelog [skip ci] (#638) ([61f2f21](https://github.com/aliyevaladddin/AladdinAI/commit/61f2f21bcda66e4638dfef12293822bb0eb10338))

- Update changelog [skip ci] (#641) ([fe3b1c0](https://github.com/aliyevaladddin/AladdinAI/commit/fe3b1c0534f6cfcb43e111e4ea1112bdea1ff69a))

- Update changelog [skip ci] (#643) ([64f1afb](https://github.com/aliyevaladddin/AladdinAI/commit/64f1afbe83eec8bc4fa847797023d9a0a20bb212))

- Update changelog [skip ci] (#646) ([4fad802](https://github.com/aliyevaladddin/AladdinAI/commit/4fad802fef3574f9e4f504a808c7ae5062c474d1))

- Update changelog [skip ci] (#649) ([3dedc75](https://github.com/aliyevaladddin/AladdinAI/commit/3dedc754a52d57eb55546d65a8bcac4f71abb1d0))

- Update changelog [skip ci] (#652) ([e0a0a6c](https://github.com/aliyevaladddin/AladdinAI/commit/e0a0a6c34d17dd6ea191eaab8376a2e31a5f5219))

- Update changelog [skip ci] (#653) ([91c4f05](https://github.com/aliyevaladddin/AladdinAI/commit/91c4f05946aa6fbc26e957ac7650ed550f80778a))

- Update changelog [skip ci] (#654) ([7d4a2ae](https://github.com/aliyevaladddin/AladdinAI/commit/7d4a2aebe53874f9f944299a4088356114e19a33))

- Update changelog [skip ci] (#655) ([5864d5e](https://github.com/aliyevaladddin/AladdinAI/commit/5864d5e048010823482e45eb87ecfb9901a0b77b))

- Update changelog [skip ci] (#656) ([49b3225](https://github.com/aliyevaladddin/AladdinAI/commit/49b3225d1f9fbbcfef67dc380917e4d5a47239cc))

- Update changelog [skip ci] (#667) ([0ccf937](https://github.com/aliyevaladddin/AladdinAI/commit/0ccf93754187edc729858cc8cc77b5f3eb1d32c6))

- Update changelog [skip ci] (#669) ([1d34b3b](https://github.com/aliyevaladddin/AladdinAI/commit/1d34b3bae726fc6bd473aefe11879a088c467818))

- Update changelog [skip ci] (#671) ([813a7cd](https://github.com/aliyevaladddin/AladdinAI/commit/813a7cdc0de8501cce6600d710610f9485cd4b74))

- Update changelog [skip ci] (#673) ([10f7c69](https://github.com/aliyevaladddin/AladdinAI/commit/10f7c6943d71fce185646763767c6c48de5a371b))

- Update changelog [skip ci] (#679) ([c8d75de](https://github.com/aliyevaladddin/AladdinAI/commit/c8d75de853e7db04205f24ea8a94f753095fa09d))

- Update changelog [skip ci] (#683) ([122f8de](https://github.com/aliyevaladddin/AladdinAI/commit/122f8ded3a732e7a5b328ad7aa901dd81c9f38b8))

- Ignore frontend coverage directory in git ([d0fe0c9](https://github.com/aliyevaladddin/AladdinAI/commit/d0fe0c9cd69746b46788516b507684cf63c2966f))

- Update changelog [skip ci] (#689) ([79d199e](https://github.com/aliyevaladddin/AladdinAI/commit/79d199e95d3d8d2576bfc9596989a78b07a7c5ab))

- Update changelog [skip ci] (#690) ([a4c9bf7](https://github.com/aliyevaladddin/AladdinAI/commit/a4c9bf7dcef8af0be59ec955348c83ed77a93f33))

- Update changelog [skip ci] (#693) ([ad5cb1e](https://github.com/aliyevaladddin/AladdinAI/commit/ad5cb1e2233e23d6148d4c8f4b6637ba597adce0))

- Remove unused Activity and FlaskConical imports from dashboard-nav ([24d17fc](https://github.com/aliyevaladddin/AladdinAI/commit/24d17fc3ee1d4c55e60c960acc8b319b1873ae1e))

- Update changelog [skip ci] (#698) ([5762e31](https://github.com/aliyevaladddin/AladdinAI/commit/5762e311d83839cc367754fd4f6f8bf7a68942fd))

- Update bot activity log (#700) ([562a25e](https://github.com/aliyevaladddin/AladdinAI/commit/562a25e56b68fde38ba043604863b7c2baa8aa22))

- Update nvidia bot activity log (#701) ([37cd302](https://github.com/aliyevaladddin/AladdinAI/commit/37cd302bd2f98909ec7e514c56f5c5c01102de18))

- Update changelog [skip ci] (#703) ([996327d](https://github.com/aliyevaladddin/AladdinAI/commit/996327df967dbb6fbde7abee45d4965c12207d40))

- Update bot activity log (#704) ([663bb8a](https://github.com/aliyevaladddin/AladdinAI/commit/663bb8abca73072ed7896d3eaaee0c0a4c5459a4))

- Update changelog [skip ci] (#707) ([9a2d1c2](https://github.com/aliyevaladddin/AladdinAI/commit/9a2d1c248bf8b675e5b69f54d6378aab6aab7b53))

- Update activity log [skip ci] ([db5f763](https://github.com/aliyevaladddin/AladdinAI/commit/db5f7639d8fb84257bc6788f0643d74b08c92bcb))

- Update nvidia bot activity log (#708) ([013dff9](https://github.com/aliyevaladddin/AladdinAI/commit/013dff9a537b188352d7b4818c5f0a9aeb6bf13a))

- Update bot activity log (#709) ([82800cc](https://github.com/aliyevaladddin/AladdinAI/commit/82800cce23e2d1902d98f6dfeb9f118df700d49b))

- Update changelog [skip ci] (#711) ([430485c](https://github.com/aliyevaladddin/AladdinAI/commit/430485cb46208d69a494fd108bd670741d07ec5c))


### Performance

- Stream chat updates without re-rendering the whole message list ([4193a53](https://github.com/aliyevaladddin/AladdinAI/commit/4193a5334dfdd34bc44dc3966e093b395b9ab04d))


### Refactor

- Extract SQL playground into sub-components (1255→454 lines) (#678) ([8113898](https://github.com/aliyevaladddin/AladdinAI/commit/811389827bd7195d5a9e7bbce2d74f0e2f5f5ab3))

- Clean up error handling, fix f-string usage, and reorganize imports across agents and tools ([720da99](https://github.com/aliyevaladddin/AladdinAI/commit/720da997a693ee99598de049daecaf131c7e4a1c))

- Replace broad exception handling with specific exception types in agents and simplify readiness check logging ([276fea3](https://github.com/aliyevaladddin/AladdinAI/commit/276fea3b7fca1022dcc9385e4407a58c091e5520))

- Move Traces and Self-Forging from sidebar to Settings tabs (#648) ([691849d](https://github.com/aliyevaladddin/AladdinAI/commit/691849dee1e1c637234e968e0fb444099ee8f153))

- Remove unused pytest import in crm test suite ([bca6328](https://github.com/aliyevaladddin/AladdinAI/commit/bca632821471949d73982ba7664cb96adfe64dbb))

- Extract invalidateMutated helper + convention comment ([6646c7e](https://github.com/aliyevaladddin/AladdinAI/commit/6646c7ee76423f8bd7302b78ba74433a4da5dd36))

- Move Traces and Self-Forging from sidebar to Settings tabs ([4a929b5](https://github.com/aliyevaladddin/AladdinAI/commit/4a929b553553ee82d65faf31fc5ebd3d2fd59d85))

- Remove unused os and tempfile imports in ssh known hosts test ([3aa51f4](https://github.com/aliyevaladddin/AladdinAI/commit/3aa51f4dadd55a6cca1c0b04d71d69455ca6354a))

- Extract SQL playground into sub-components (1255→454 lines) ([1431664](https://github.com/aliyevaladddin/AladdinAI/commit/1431664dec66263d41e662b32c26313afa09b737))

- Move Traces from sidebar to Settings > Observability ([079f592](https://github.com/aliyevaladddin/AladdinAI/commit/079f592103895a40e66b99ee687b4079fcf7d9ea))

- Move Self-Forging from sidebar to Settings > Training ([b52a365](https://github.com/aliyevaladddin/AladdinAI/commit/b52a36546c85211fc44367aa4c272c4d61723477))


### Testing

- Add CRM router tests (contacts, deals, products, orders) ([21947cd](https://github.com/aliyevaladddin/AladdinAI/commit/21947cdf53b78f4fec6db1572612d5e8489e8c5b))

- Update webhook test documentation and clean up formatting in guides README ([e9c7864](https://github.com/aliyevaladddin/AladdinAI/commit/e9c786436dc2d1ab90208a8110c4a8dfe1dd3a9c))

- Remove unused datetime import from global traces test suite ([51506fa](https://github.com/aliyevaladddin/AladdinAI/commit/51506fa51a7db97b8d65e9726a8a25c018370c0d))


### Merge

- Fix/pydantic-exceptions-validation into main ([1dcc7c9](https://github.com/aliyevaladddin/AladdinAI/commit/1dcc7c92d840c501e0bc75179340cebac261a585))

- Fix/critical-issues into main ([d2d0ff5](https://github.com/aliyevaladddin/AladdinAI/commit/d2d0ff555efaf8eb554ead28edb638290e57c152))

- Fix/important-issues into main ([88ca1a0](https://github.com/aliyevaladddin/AladdinAI/commit/88ca1a091d47741a8f0889cd72dabe8538d86493))

- Fix/ui-loading-states-and-cleanup into main ([4898d27](https://github.com/aliyevaladddin/AladdinAI/commit/4898d27a29a45791f434dd39720756bf46001121))

- Fix/changelog-bot-attribution into main ([f485096](https://github.com/aliyevaladddin/AladdinAI/commit/f4850964ac7e111555f57df60a1491904f49777b))

- Feat/qwen-bot-activity into main ([5e6261a](https://github.com/aliyevaladddin/AladdinAI/commit/5e6261a2d65bea51beeec38c6a3daff47e7f3bc0))

- Feat/webhooks-agents-edit-test into main ([25124eb](https://github.com/aliyevaladddin/AladdinAI/commit/25124eb71e6865e21bdd3dbefb21896097418975))

- Fix/move-traces-forging-to-settings into main ([d0e6be1](https://github.com/aliyevaladddin/AladdinAI/commit/d0e6be115dced0e67d06ff21442be847db2ccbaa))

- Fix/critical-hardcoded-port-async-block into main (resolved conflict) ([22d4bf5](https://github.com/aliyevaladddin/AladdinAI/commit/22d4bf5b26a072dbcfa3b706a441f0f5eb47f73c))

- Fix/ssh-known-hosts-tofu into main (resolved conflict, kept CodeQL-safe test data) ([494306c](https://github.com/aliyevaladddin/AladdinAI/commit/494306c5025cffc23f5604892f31353afa144f00))

- Feat/agent-trace-view into main (resolved conflicts, took branch version) ([dae4f78](https://github.com/aliyevaladddin/AladdinAI/commit/dae4f78f95fc6845e655ac7c558b620f9b3f3b04))

- Feat/traces-forging-ui into main (resolved conflicts — kept validation + accessibility, took branch UX for tracing toggle) ([20fd20f](https://github.com/aliyevaladddin/AladdinAI/commit/20fd20fcf49d5edabf2e4206144acb9bc937cb10))

- Feat/ui-polish-chat-perf into main (resolved conflicts — kept theme tokens, count badges, removed Gates) ([6fd16cc](https://github.com/aliyevaladddin/AladdinAI/commit/6fd16cc0cf46694f3f7b4291e861f136accfe1e1))

- Fix/remaining-issues into main ([8c36715](https://github.com/aliyevaladddin/AladdinAI/commit/8c36715190b84745333fd9bbaa67752ca7bbcdc5))

## [v2.2.4] - 2026-08-18

### Bug Fixes

- Update package overrides for axios, ws, uuid and hono node-server ([f468d5e](https://github.com/aliyevaladddin/AladdinAI/commit/f468d5ebbcc9365208ad37b2b61031d734acfbce))

- Update package-lock.json ([5327b33](https://github.com/aliyevaladddin/AladdinAI/commit/5327b334ce5010ce987d3bf3b6caca5fa730957d))

- Close approval-gate bypass and scope approvals by owner (#529) ([857e735](https://github.com/aliyevaladddin/AladdinAI/commit/857e73587754f5c1a416dce7af4ab8903f119b5a))

- Separate uploaded documents from facts (#532) ([b134117](https://github.com/aliyevaladddin/AladdinAI/commit/b13411764f70c7865a8b7cb40e6e81b7fe210855))

- Retry transient LLM provider errors with backoff (#578) ([6f44a09](https://github.com/aliyevaladddin/AladdinAI/commit/6f44a094661e20e41d01a7e70cb9ebaa42aff9b8))

- Send generated images to Telegram when media store is GridFS (#615) ([5d03b59](https://github.com/aliyevaladddin/AladdinAI/commit/5d03b59894d8b41bb1906621ade07f9be1f65e43))

- Correct changelog bot noreply identity for contributor attribution (#629) ([cdb9d12](https://github.com/aliyevaladddin/AladdinAI/commit/cdb9d126c743a9242c73b8d6f4474b08c392e704))


### Dependencies

- Bump actions/setup-python from 6 to 7 (#469) ([b71daf8](https://github.com/aliyevaladddin/AladdinAI/commit/b71daf856567ea21bce1a7f20a8a04c37987c645))

- Bump builder-util-runtime and electron-builder in /frontend (#502) ([fbcc8b0](https://github.com/aliyevaladddin/AladdinAI/commit/fbcc8b0b877d20f2567f4572cd3eddf9653bf65f))

- Bump x402 and x402-fetch in /frontend (#504) ([fa87139](https://github.com/aliyevaladddin/AladdinAI/commit/fa8713931e1031e330bfedd5d33e1088e538d141))

- Bump lucide-react from 1.26.0 to 1.27.0 in /frontend (#518) ([b87745a](https://github.com/aliyevaladddin/AladdinAI/commit/b87745ac90f7767c685c8be47e8745d4d1495771))

- Bump uvicorn from 0.51.0 to 0.52.0 (#512) ([df6186b](https://github.com/aliyevaladddin/AladdinAI/commit/df6186bd363af002448e3a5b1d31ddf4d65d76d3))

- Bump fastapi from 0.140.0 to 0.141.0 (#513) ([19af08e](https://github.com/aliyevaladddin/AladdinAI/commit/19af08e2d1781460c271d19faefefb6e5988f03d))

- Bump shadcn from 4.15.0 to 4.16.0 in /frontend (#515) ([0e4f2f4](https://github.com/aliyevaladddin/AladdinAI/commit/0e4f2f40d3ee804182ec81117cc21cf9e206b36f))

- Bump framer-motion from 12.42.2 to 12.43.0 in /frontend (#516) ([49fdb90](https://github.com/aliyevaladddin/AladdinAI/commit/49fdb906d43d910c0a730cc1702e3fe53c8b5d1b))

- Bump fast-uri from 3.1.4 to 3.1.5 in /frontend (#533) ([4378c5d](https://github.com/aliyevaladddin/AladdinAI/commit/4378c5d8fd95a11e0f4e6d65016fd0afd11d1be6))

- Bump @tanstack/react-table in /frontend (#548) ([32b953c](https://github.com/aliyevaladddin/AladdinAI/commit/32b953c3df08c4a5f4e991f98736f4bc9b300e4d))

- Bump @base-ui/react from 1.6.0 to 1.7.0 in /frontend (#547) ([0268623](https://github.com/aliyevaladddin/AladdinAI/commit/02686237d054b0b8b6a744cd5c8ddfbc88c949db))

- Bump framer-motion from 12.43.0 to 13.0.0 in /frontend (#545) ([464b6e5](https://github.com/aliyevaladddin/AladdinAI/commit/464b6e5c8f52342ed59a67c4cefbb1e65c895e3a))

- Bump next from 16.2.12 to 16.3.0 in /frontend (#544) ([63266d3](https://github.com/aliyevaladddin/AladdinAI/commit/63266d3b3dce64e239c7239f904603f95c51daef))

- Bump lucide-react from 1.27.0 to 1.28.0 in /frontend (#543) ([b6a7654](https://github.com/aliyevaladddin/AladdinAI/commit/b6a7654b2665c1c23c6e235a3b753373c6f97d8a))

- Bump the security-patches group across 1 directory with 4 updates (#556) ([7acd8c4](https://github.com/aliyevaladddin/AladdinAI/commit/7acd8c4ce01f2a6358dcacec5424b488178320eb))

- Bump alembic from 1.18.5 to 1.19.0 (#541) ([acb8967](https://github.com/aliyevaladddin/AladdinAI/commit/acb896783405af93d7696de3cf88c2c103bf88f7))

- Bump fastapi from 0.141.0 to 0.141.1 (#540) ([4319c22](https://github.com/aliyevaladddin/AladdinAI/commit/4319c2271a9da54de37c4c287c52afdbf9d9e394))

- Bump uvicorn from 0.51.0 to 0.52.1 (#539) ([e7304b9](https://github.com/aliyevaladddin/AladdinAI/commit/e7304b9dab9f6b915e569f1154613a1a3150c2c0))

- Bump playwright from 1.61.0 to 1.62.0 (#538) ([858e57d](https://github.com/aliyevaladddin/AladdinAI/commit/858e57db6c1395c1e1ec81e65b72ee8277c62ff2))

- Bump ip-address from 10.2.0 to 10.5.0 in /frontend (#563) ([5fdf334](https://github.com/aliyevaladddin/AladdinAI/commit/5fdf334df14901b68c0348362b6a187cb18d5aeb))

- Bump pypdf from 6.14.2 to 6.15.0 in /backend (#567) ([1e6a882](https://github.com/aliyevaladddin/AladdinAI/commit/1e6a8821b9fda28913c716f4d50339b87a39aa59))

- Bump alembic from 1.19.0 to 1.19.1 (#583) ([579cc31](https://github.com/aliyevaladddin/AladdinAI/commit/579cc31be9cd90971773d529b87ea3b6c242da9b))

- Bump pydantic-settings from 2.14.2 to 2.15.0 (#584) ([a34f01d](https://github.com/aliyevaladddin/AladdinAI/commit/a34f01d16197889f4e7f4c3cbc30925bd622f6b8))

- Bump sqlalchemy from 2.0.51 to 2.0.52 (#585) ([d54769b](https://github.com/aliyevaladddin/AladdinAI/commit/d54769bd9fcdc782ecde20547145c0117d876213))

- Bump fastapi from 0.141.0 to 0.141.1 (#586) ([8751687](https://github.com/aliyevaladddin/AladdinAI/commit/8751687bd1677e31dd6cc29dfd9a889ae6e6963e))

- Bump the security-patches group in /frontend with 3 updates (#587) ([ba964ae](https://github.com/aliyevaladddin/AladdinAI/commit/ba964aec067f9e6960a576404e2bbe4089c764b2))

- Bump lucide-react from 1.28.0 to 1.31.0 in /frontend (#589) ([0e69af1](https://github.com/aliyevaladddin/AladdinAI/commit/0e69af126e054c3370d7419acea8db4e7331b2d5))

- Bump shadcn from 4.16.2 to 4.17.0 in /frontend (#594) ([435e528](https://github.com/aliyevaladddin/AladdinAI/commit/435e5287c46ffbaefb7628a552055956135b84bf))

- Bump framer-motion from 13.0.0 to 13.1.0 in /frontend (#593) ([632f766](https://github.com/aliyevaladddin/AladdinAI/commit/632f7661fff6fdfa09ef14077dd7a3d5afe02741))

- Bump @tanstack/react-table from 9.0.0 to 9.1.2 in /frontend (#591) ([2b4d99c](https://github.com/aliyevaladddin/AladdinAI/commit/2b4d99c48ca12f5b62c17b2f6f5a07621dae0de1))

- Bump sqlparse from 0.5.5 to 0.6.0 in /backend (#632) ([1c76b9b](https://github.com/aliyevaladddin/AladdinAI/commit/1c76b9b62fe0e43d556adc8cd1cf11f36f52ebc8))


### Documentation

- Update API documentation [skip ci] (#531) ([e9824d1](https://github.com/aliyevaladddin/AladdinAI/commit/e9824d1f418227d8b175389581c655cb0aac4e5f))

- Update API documentation [skip ci] (#573) ([6efe4d6](https://github.com/aliyevaladddin/AladdinAI/commit/6efe4d693cc6e9ffdef4cd8dda8409ca4cc8eb27))

- Update API documentation [skip ci] (#582) ([78b90b3](https://github.com/aliyevaladddin/AladdinAI/commit/78b90b3f7040f9816e2fd19ea278832fcad66419))

- Update API documentation [skip ci] (#621) ([84e86bb](https://github.com/aliyevaladddin/AladdinAI/commit/84e86bbe9a48d2da6ea9c6371af1a8a65d593831))

- Update API documentation [skip ci] (#636) ([1f942c9](https://github.com/aliyevaladddin/AladdinAI/commit/1f942c94019fe00e7a073ac92ac431392a0112cf))


### Features

- Docker-per-agent isolated execution environment (#485) ([2d49c90](https://github.com/aliyevaladddin/AladdinAI/commit/2d49c9050c59eeefc1dda43da5a66b7b914105d6))

- Provision Atlas vector indexes from code (#571) ([27b350e](https://github.com/aliyevaladddin/AladdinAI/commit/27b350ebd88b09b94885c420c649ebd56fa14f6a))

- Migrate terminal approval state to Postgres to support multi-worker environments (#574) ([3b8e77a](https://github.com/aliyevaladddin/AladdinAI/commit/3b8e77a1789792238d5b4a3fbe54973d8f2be134))

- Add JSONL export of the golden set for fine-tuning (#579) ([175ca43](https://github.com/aliyevaladddin/AladdinAI/commit/175ca43e67bb1e8da5d9e40edecec0808defb78f))

- Pluggable image-gen backends, transport retries, attachment dedupe (#612) ([3c482b5](https://github.com/aliyevaladddin/AladdinAI/commit/3c482b5b47b8a45fa9e9f39dbd56ccb011bf3eff))

- Implement full-screen image lightbox and hover interaction cards for attachments ([b3da123](https://github.com/aliyevaladddin/AladdinAI/commit/b3da1238c7c0d4dfd34d915d6c4019b21605ecb1))

- Rename, regenerate, smart scroll, drafts, auto-titles (#619) ([983e93a](https://github.com/aliyevaladddin/AladdinAI/commit/983e93acfac15ac83e6ebcf7c8d95882c6f43d78))

- Product catalog UI and safe product delete (#622) ([982a1a8](https://github.com/aliyevaladddin/AladdinAI/commit/982a1a81a7bce66cd176ac627c62dbf533713b64))

- Add Qwen bot activity job and fix bot commit attribution (#626) ([f7324ca](https://github.com/aliyevaladddin/AladdinAI/commit/f7324cad07263abf482a87b5c0a26860a5c39325))

- Agents can see and fire webhooks; edit & test in settings UI (#634) ([dfb2870](https://github.com/aliyevaladddin/AladdinAI/commit/dfb2870b67e557fa081b14a2279dd13405a6c18d))


### Maintenance

- Update changelog (#483) ([a0daa4d](https://github.com/aliyevaladddin/AladdinAI/commit/a0daa4da6c29bcb645b2c6ca9f7725d966297cd7))

- Update changelog [skip ci] (#503) ([5cbff68](https://github.com/aliyevaladddin/AladdinAI/commit/5cbff68228fe3af13d4391c6a46578febfa703d9))

- Update changelog [skip ci] (#505) ([077ea20](https://github.com/aliyevaladddin/AladdinAI/commit/077ea205a1d3885360d04d6efa01e7af29322e14))

- Update changelog [skip ci] (#508) ([6ec66b4](https://github.com/aliyevaladddin/AladdinAI/commit/6ec66b492de0181234c50f2539962e040ded352e))

- Add uuid and ws dependencies to frontend package.json ([077f96a](https://github.com/aliyevaladddin/AladdinAI/commit/077f96a1c892c9ee881d172b064feccf5d8603aa))

- Update axios dependency, add scroll behavior attribute, and configure allowed dev origins in next config ([e24dd44](https://github.com/aliyevaladddin/AladdinAI/commit/e24dd44466d00880ffd3cc007ca29a2a8ddc821f))

- Update changelog [skip ci] (#511) ([12a1980](https://github.com/aliyevaladddin/AladdinAI/commit/12a1980ff06d867e3b5473c7f92b5f6058aa4a3f))

- Update dependencies in package-lock.json ([077a161](https://github.com/aliyevaladddin/AladdinAI/commit/077a161c54b033113a2d9a72fe91416e8f1460b5))

- Bump the security-patches group (#514) ([fa8e82d](https://github.com/aliyevaladddin/AladdinAI/commit/fa8e82dbb59fc9350881782d43a5e39c8eacb00e))

- Bump eslint-config-next in /frontend (#517) ([1332d06](https://github.com/aliyevaladddin/AladdinAI/commit/1332d06880793b1df1ba52d7f42d78894fc0f918))

- Update changelog [skip ci] (#530) ([bd89f6c](https://github.com/aliyevaladddin/AladdinAI/commit/bd89f6c69187d1709286cae88adb9b338dd0c015))

- Update package-lock.json to sync with package.json ([98b7949](https://github.com/aliyevaladddin/AladdinAI/commit/98b79498e3f9e81209da1db79b92ea1572d18db9))

- Force regenerate package-lock.json from scratch ([24e3b4f](https://github.com/aliyevaladddin/AladdinAI/commit/24e3b4fdded82449c86c2b12e737c3d04c806cc0))

- Update lockfile to reflect frontend dependency changes ([9a9fe36](https://github.com/aliyevaladddin/AladdinAI/commit/9a9fe36ce3de7b95c48341c017d429610b64338e))

- Update changelog [skip ci] (#537) ([fe583fa](https://github.com/aliyevaladddin/AladdinAI/commit/fe583fa349a58dd3c2c215258c186aa62de426dd))

- Bump eslint-config-next in /frontend (#549) ([917fceb](https://github.com/aliyevaladddin/AladdinAI/commit/917fceba5957d2431af1b43ea768e7f8d6639a80))

- Bump electron from 43.1.1 to 43.3.0 in /frontend (#546) ([8cb9a7a](https://github.com/aliyevaladddin/AladdinAI/commit/8cb9a7a3fc98a13d87b87bfdf37401954584b87a))

- Update changelog [skip ci] (#561) ([3426be6](https://github.com/aliyevaladddin/AladdinAI/commit/3426be62b2fa98eb130d666e17da1a2970e70596))

- Update changelog [skip ci] (#560) ([7d450cc](https://github.com/aliyevaladddin/AladdinAI/commit/7d450cc8a209af0244ef28271b340c9e6464a017))

- Update dependencies in package-lock.json ([7610c2f](https://github.com/aliyevaladddin/AladdinAI/commit/7610c2fe3919454de1863b890bc98792d3e7606e))

- Update changelog [skip ci] (#562) ([d80a6d2](https://github.com/aliyevaladddin/AladdinAI/commit/d80a6d23df4a0d6ff6098904059659db82b6fff5))

- Update dependency tree in package-lock.json ([1a797b6](https://github.com/aliyevaladddin/AladdinAI/commit/1a797b632078041757fbac7eaf550de998821539))

- Update changelog [skip ci] (#566) ([6615400](https://github.com/aliyevaladddin/AladdinAI/commit/661540012840f519a68e09d110b4ff97ac523e35))

- Update changelog [skip ci] (#568) ([abff400](https://github.com/aliyevaladddin/AladdinAI/commit/abff400fcb1c12cc83c951505c3cf0be46183224))

- Upgrade ws package to version 8.21.0 ([ef1f08e](https://github.com/aliyevaladddin/AladdinAI/commit/ef1f08e73069369965c97b061f4b7d3c215fd47e))

- Update changelog [skip ci] (#569) ([152d2ad](https://github.com/aliyevaladddin/AladdinAI/commit/152d2ad7dfcb7e0e5cb7ab32745a6b61212d3e07))

- Upgrade @hono/node-server to version 2.0.10 ([99bf3e5](https://github.com/aliyevaladddin/AladdinAI/commit/99bf3e56deb987f617fc82ebcabeb8d4e2b35623))

- Update changelog [skip ci] (#570) ([6d5f504](https://github.com/aliyevaladddin/AladdinAI/commit/6d5f50417d8fde3a2ef2c2ec6bef7bb0c3e4003c))

- Update changelog [skip ci] (#572) ([6fa5bc5](https://github.com/aliyevaladddin/AladdinAI/commit/6fa5bc54d7d4b2794b5096c0d9fc47f8a5e6feff))

- Update changelog [skip ci] (#575) ([37a598b](https://github.com/aliyevaladddin/AladdinAI/commit/37a598b2b0f3b782a7107bce897ea83230e6c3fc))

- Update changelog [skip ci] (#577) ([c66cd49](https://github.com/aliyevaladddin/AladdinAI/commit/c66cd49358491579e71e420f62ec7633ef4a958b))

- Update changelog [skip ci] (#580) ([9c4f3a2](https://github.com/aliyevaladddin/AladdinAI/commit/9c4f3a2078d6a60b4d5991cf4011481a49e43342))

- Update changelog [skip ci] (#581) ([7fabe24](https://github.com/aliyevaladddin/AladdinAI/commit/7fabe241b02a42eb1efa5d2adace590413ea238f))

- Bump eslint from 10.7.0 to 10.8.1 in /frontend (#588) ([c0d7f70](https://github.com/aliyevaladddin/AladdinAI/commit/c0d7f70093d4235d9dee3feca2b6331ecfd48cbc))

- Update lockfile to reflect latest frontend dependencies ([945e404](https://github.com/aliyevaladddin/AladdinAI/commit/945e404643365d57722378054d07d4f72511dbcb))

- Update frontend dependencies in package-lock.json ([a18e8c4](https://github.com/aliyevaladddin/AladdinAI/commit/a18e8c45b01db162e193856f50f786abed29a890))

- Update lockfile dependencies ([dd23ba2](https://github.com/aliyevaladddin/AladdinAI/commit/dd23ba2ac54d23e3c7ee34a4acd9874f7586ab55))

- Bump @types/node from 26.1.2 to 26.2.0 in /frontend (#592) ([182ba60](https://github.com/aliyevaladddin/AladdinAI/commit/182ba60f87159dc26789e050f4b219ba21076135))

- Bump electron from 43.3.0 to 43.4.0 in /frontend (#590) ([fdedabe](https://github.com/aliyevaladddin/AladdinAI/commit/fdedabecf4218d8263f2b548d6b15103f8665254))

- Update frontend dependencies in package-lock.json ([9e06de6](https://github.com/aliyevaladddin/AladdinAI/commit/9e06de6ceccd494763edd94d74c41d5c3f243219))

- Update lockfile dependencies for frontend project ([9ced25c](https://github.com/aliyevaladddin/AladdinAI/commit/9ced25c7e8ba182c48213e394417cb7ce394f7e5))

- Update changelog [skip ci] (#611) ([42f4023](https://github.com/aliyevaladddin/AladdinAI/commit/42f4023ad85502e610cc0af45f9198fb91a39b7f))

- Update changelog [skip ci] (#613) ([c166d42](https://github.com/aliyevaladddin/AladdinAI/commit/c166d426a29d6045f870eb7ffbc363d694813ae4))

- Update changelog [skip ci] (#616) ([cc9c5f4](https://github.com/aliyevaladddin/AladdinAI/commit/cc9c5f415374c0890f25b50bf26769310ec865d0))

- Update frontend dependencies in package-lock.json ([d6f9863](https://github.com/aliyevaladddin/AladdinAI/commit/d6f9863b36816b506c6919637f02eb408469a060))

- Bump frontend version to 2.2.3 ([7fefdeb](https://github.com/aliyevaladddin/AladdinAI/commit/7fefdeb261787890cc8057c075ba746cdd390ee1))

- Update changelog [skip ci] (#618) ([022f4c2](https://github.com/aliyevaladddin/AladdinAI/commit/022f4c23cd5ef06ff6e36902db73ab98ab485f5f))

- Update changelog [skip ci] (#620) ([f76acfb](https://github.com/aliyevaladddin/AladdinAI/commit/f76acfbf613ae20ab5f1e3dc8d09bcbc8eb4971f))

- Update changelog [skip ci] (#623) ([bbd6247](https://github.com/aliyevaladddin/AladdinAI/commit/bbd6247054c4db7dcf8e97b75d10e360fd099897))

- Gitignore .git-rewrite filter-branch leftovers ([8e9a9a3](https://github.com/aliyevaladddin/AladdinAI/commit/8e9a9a36869ac3617e38ba2698243e00e8d04810))

- Update changelog [skip ci] (#627) ([e6010f6](https://github.com/aliyevaladddin/AladdinAI/commit/e6010f660ef260673be19fe3ccba492503ba7702))

- Update changelog after history rewrite [skip ci] (#631) ([011a994](https://github.com/aliyevaladddin/AladdinAI/commit/011a994ce67c45bf7d8f2e797d4c25da700932b1))

- Update changelog [skip ci] (#633) ([2991897](https://github.com/aliyevaladddin/AladdinAI/commit/2991897c6f5fb791265fa9dbeb936476c81418c2))

- Update changelog [skip ci] (#635) ([c94fa59](https://github.com/aliyevaladddin/AladdinAI/commit/c94fa59a269ca9f85fe21448b65f215dd228c319))

## [v2.2.3] - 2026-07-22

### Bug Fixes

- Add --allow-same-version to npm version steps in release workflow ([33a85a6](https://github.com/aliyevaladddin/AladdinAI/commit/33a85a60bfa13c9de6c0a070d914a525e4f81fd6))

- Add python3 make g++ build tools to frontend Dockerfile.prod deps stage ([57f4da0](https://github.com/aliyevaladddin/AladdinAI/commit/57f4da0977ae5e8daf7dcb3c7a766b41b5b78de6))


### Dependencies

- Bump body-parser from 2.2.2 to 2.3.0 in /frontend (#447) ([9be4f8f](https://github.com/aliyevaladddin/AladdinAI/commit/9be4f8f858700b3e57b3fb8760ffe41842c87ebd))

- Bump fast-uri from 3.1.2 to 3.1.4 in /frontend (#455) ([4729c1d](https://github.com/aliyevaladddin/AladdinAI/commit/4729c1d4b58a2db209c65a07ddc2075ac1e61f37))

- Bump hono from 4.12.25 to 4.12.31 in /frontend (#459) ([7fe47ff](https://github.com/aliyevaladddin/AladdinAI/commit/7fe47ff50b6de551f71c278b23561794c48c4611))

- Bump dompurify from 3.4.11 to 3.4.12 in /frontend (#461) ([9dbf74a](https://github.com/aliyevaladddin/AladdinAI/commit/9dbf74a41da0e1b1e2dd38e41b09dc9407719818))


### Documentation

- Update API documentation [skip ci] (#451) ([3babaab](https://github.com/aliyevaladddin/AladdinAI/commit/3babaab88f2acca17ea8a5b7b8c16d5b79ab1f2a))

- Update readme modules to include multi-agent swarm, meta-search, evaluation harness, UI features, and revised voice/order documentation ([dcc5dfb](https://github.com/aliyevaladddin/AladdinAI/commit/dcc5dfbc2862584e1a96988cfcacfdcbfba2f72b))

- Update API documentation [skip ci] (#467) ([f346a4c](https://github.com/aliyevaladddin/AladdinAI/commit/f346a4c4d2ce7f84d4a093b7013e89aded5f564b))


### Features

- Implement voice playback, markdown parsing, and chat UI improvements (#453) ([fb76e01](https://github.com/aliyevaladddin/AladdinAI/commit/fb76e0158f121ba013526e6f50316f798c25b701))

- Implement system-wide Command Palette with keyboard shortcut registry and documentation settings tab (#457) ([464ddaa](https://github.com/aliyevaladddin/AladdinAI/commit/464ddaa16d955e3c7eef7760dd66bf060109ad17))

- Implement native log/grep utilities and improve terminal UX with clipboard support and render safety patches (#465) ([1059538](https://github.com/aliyevaladddin/AladdinAI/commit/10595380110ace1a5877c3efbc05211120a0302a))

- Add @hono/node-server to frontend dependencies ([8a801eb](https://github.com/aliyevaladddin/AladdinAI/commit/8a801ebb396604bf1f3dcd7590ce49bab91a53fa))


### Maintenance

- Bump tar from 7.5.16 to 7.5.20 in /frontend (#445) ([41d841d](https://github.com/aliyevaladddin/AladdinAI/commit/41d841dc46ed58a419e9e2c8c054c0b5793291d0))

- Update changelog [skip ci] (#446) ([09594fb](https://github.com/aliyevaladddin/AladdinAI/commit/09594fb283686ee4f6717f2787a88a80e6c42b56))

- Update changelog [skip ci] (#448) ([cae5fe5](https://github.com/aliyevaladddin/AladdinAI/commit/cae5fe5899b2d9db24e9178121ba71e16aca3081))

- Update changelog [skip ci] (#450) ([f5617e5](https://github.com/aliyevaladddin/AladdinAI/commit/f5617e5c2f27957853066958b649d8d2e5fc21b4))

- Update changelog [skip ci] (#456) ([9134849](https://github.com/aliyevaladddin/AladdinAI/commit/91348494c90c6f9a66a3bcff8d15554e54a4c3e0))

- Update changelog [skip ci] (#458) ([cb1166a](https://github.com/aliyevaladddin/AladdinAI/commit/cb1166aa63d1e7f080810c279799b6204f027a62))

- Update changelog [skip ci] (#460) ([0befe73](https://github.com/aliyevaladddin/AladdinAI/commit/0befe73931e08fbdff1c06395dd763ca1e52268f))

- Update changelog [skip ci] (#462) ([bf81e0f](https://github.com/aliyevaladddin/AladdinAI/commit/bf81e0fac9d49225c0ba244a280410173ee2f633))

- Update changelog [skip ci] (#463) ([2d05f03](https://github.com/aliyevaladddin/AladdinAI/commit/2d05f033e5d7c26d6382bf621e41e49e44b9874d))

- Add axios, dotenv, ink, prompts, rcf-protocol, react, and zod dependencies to package.json ([4ac39c4](https://github.com/aliyevaladddin/AladdinAI/commit/4ac39c4fb60b42073945a10e24392fd1bf82802f))

- Update changelog [skip ci] (#466) ([c5dbf2d](https://github.com/aliyevaladddin/AladdinAI/commit/c5dbf2db28ba3e82c0f30b13303e997e4c88820f))

- Update changelog [skip ci] (#468) ([126b5c3](https://github.com/aliyevaladddin/AladdinAI/commit/126b5c30952ec10d2ed14a0f0f915c5c6af5f7fb))

## [v2.2.2] - 2026-07-20

### Bug Fixes

- Merge two heads; guard against schema drift (#406) ([73ce624](https://github.com/aliyevaladddin/AladdinAI/commit/73ce6245b39080adb98914d5a2e586b88add2f1c))

- Register web_search and correct its function schema (#408) ([c6ce0c9](https://github.com/aliyevaladddin/AladdinAI/commit/c6ce0c9dc3716059ae95b74bc422ff3149450149))


### Dependencies

- Bump actions/setup-node from 6 to 7 (#413) ([450ea05](https://github.com/aliyevaladddin/AladdinAI/commit/450ea05f998c3a7fc17c8ba0fb9584ece17fe06e))

- Bump fastapi from 0.139.0 to 0.139.2 (#414) ([432a65e](https://github.com/aliyevaladddin/AladdinAI/commit/432a65ea142d9fd2572e8e495a963a04c6a53be1))

- Bump the security-patches group in /frontend with 4 updates (#415) ([7050df8](https://github.com/aliyevaladddin/AladdinAI/commit/7050df84df912d633f4495c8a769173066f523dc))

- Bump lucide-react from 1.24.0 to 1.25.0 in /frontend (#416) ([adacc06](https://github.com/aliyevaladddin/AladdinAI/commit/adacc06d872eb0450047ee5a034fdb053c904276))


### Documentation

- Update API documentation [skip ci] (#400) ([f029efe](https://github.com/aliyevaladddin/AladdinAI/commit/f029efe99f304902031c863679facb38f965f7cb))

- Update API documentation [skip ci] (#403) ([40f820b](https://github.com/aliyevaladddin/AladdinAI/commit/40f820bb3768db3e26b826a8e4cc35d9b2ab0306))

- Add Orders & Sales module documentation to README overview ([dfe38db](https://github.com/aliyevaladddin/AladdinAI/commit/dfe38db2bc21b27dcb936a304ea0ad61611b2456))

- Update API documentation [skip ci] (#412) ([4343002](https://github.com/aliyevaladddin/AladdinAI/commit/434300241c72080caac5aaee04d0246b622d92d7))

- Update API documentation [skip ci] (#424) ([2056d2e](https://github.com/aliyevaladddin/AladdinAI/commit/2056d2e35446a54897dfeab8c094cb17c60eb139))

- Update API documentation [skip ci] (#427) ([ff77608](https://github.com/aliyevaladddin/AladdinAI/commit/ff77608e38284a56c4294bcd3d922c1e1809cd29))

- Update API documentation [skip ci] (#434) ([8eebd5a](https://github.com/aliyevaladddin/AladdinAI/commit/8eebd5a5e49793a3c4dab75d32927bb48636b387))


### Features

- Human 👍/👎 labeling layer for the self-forging loop (#380) ([56fffd1](https://github.com/aliyevaladddin/AladdinAI/commit/56fffd10c028c812bee232f1dae81098b4cd38a3))

- Add orders, product catalog, and sales/marketing layer (#401) ([21dc28a](https://github.com/aliyevaladddin/AladdinAI/commit/21dc28a56a8a26cc3b758d92e5190ca61c89d769))

- Implement order management system, product catalog, and status tracking in CRM docs ([19f9093](https://github.com/aliyevaladddin/AladdinAI/commit/19f9093144536637facf7d3f9e9e11f34cdaff51))

- Golden set + base-vs-forged harness (self-forging layers 2-3) (#410) ([cdeac81](https://github.com/aliyevaladddin/AladdinAI/commit/cdeac81effd638a9f0a3f3bf2b8c832638c8f55d))

- Integrate native meta-search and agent tool calling capabilities (#422) ([b2dc07a](https://github.com/aliyevaladddin/AladdinAI/commit/b2dc07aec101765495e0c408a9b190e516d9f667))

- Native Out-of-the-Box Meta-Search (ArXiv, Google News RSS, DDG HTML Fallback) (#425) ([a61c38a](https://github.com/aliyevaladddin/AladdinAI/commit/a61c38a27c944de39df2b129704b07b54c87d5af))

- Integrate fetch_url tool with Chromium Headless Browser and UI thought process accordion ([3228267](https://github.com/aliyevaladddin/AladdinAI/commit/3228267a2082f9af3e1c62f9e82d06892ae1ce88))

- Implement Playwright-based URL scraping and agent thought process visualization in chat UI ([22cff42](https://github.com/aliyevaladddin/AladdinAI/commit/22cff426ee86c9bb582df17e2e4cb0e5ee87be95))

- Add AI response synthesis endpoint with optional deep web scraping and frontend integration (#432) ([ee33d23](https://github.com/aliyevaladddin/AladdinAI/commit/ee33d23859ceb5d569fe2fde930f310b38f75833))

- Add multi-agent swarm orchestrator, python sandbox, http tools, and autonomous task execution stepper (#435) ([4184894](https://github.com/aliyevaladddin/AladdinAI/commit/4184894c86ff168e6a9b05584dae7e5a77084269))


### Maintenance

- Bump version to 2.2.1 and update deps [skip ci] ([14c6811](https://github.com/aliyevaladddin/AladdinAI/commit/14c6811e56f275b40e115fb928a6f151fc9863b7))

- Add good-first-issue mini-tutorial template (#374) ([11fde3b](https://github.com/aliyevaladddin/AladdinAI/commit/11fde3b3e105adf1a3bc6ccb5398f2d8d3d3c3ae))

- Update changelog [skip ci] (#375) ([f6c5177](https://github.com/aliyevaladddin/AladdinAI/commit/f6c5177b9896b516ca17a8ac3782f7a1db526228))

- Update changelog [skip ci] (#399) ([f5aa6c9](https://github.com/aliyevaladddin/AladdinAI/commit/f5aa6c9b4411ea1ee4807472f09dc4fff39873d6))

- Update changelog [skip ci] (#402) ([a281e2a](https://github.com/aliyevaladddin/AladdinAI/commit/a281e2aede745027bff00d517a0b909a3bda48c5))

- Update changelog [skip ci] (#404) ([2d96f69](https://github.com/aliyevaladddin/AladdinAI/commit/2d96f6984dc1c02830c4bfd142ff478128b95ff5))

- Update changelog [skip ci] (#405) ([860ffe1](https://github.com/aliyevaladddin/AladdinAI/commit/860ffe13a14eecdb752a3f04cb269c8fe7b837ca))

- Update changelog [skip ci] (#407) ([bd9ff23](https://github.com/aliyevaladddin/AladdinAI/commit/bd9ff23297ddcd858b1502c848912bc165dabd25))

- Update changelog [skip ci] (#411) ([394b6d0](https://github.com/aliyevaladddin/AladdinAI/commit/394b6d02cbf0563a11d0575540a5bf7e7aa3c607))

- Update changelog [skip ci] (#420) ([ef7e269](https://github.com/aliyevaladddin/AladdinAI/commit/ef7e26945bb4f73c38f2862644f9724089037d3a))

- Update changelog [skip ci] (#423) ([ae3f512](https://github.com/aliyevaladddin/AladdinAI/commit/ae3f512837232364f16393f827e2b570851b3c89))

- Update changelog [skip ci] (#426) ([a50a679](https://github.com/aliyevaladddin/AladdinAI/commit/a50a679d955b61c89792b532c526bc7fcb1490e0))

- Update changelog [skip ci] (#428) ([d38408e](https://github.com/aliyevaladddin/AladdinAI/commit/d38408eca72651bc56bce4b4b0f4c6aa82a59461))

- Update changelog [skip ci] (#429) ([3d31e2e](https://github.com/aliyevaladddin/AladdinAI/commit/3d31e2ef8c7a578fcbe7655ac1008c6db0a4a7a6))

- Update changelog [skip ci] (#431) ([ed50e10](https://github.com/aliyevaladddin/AladdinAI/commit/ed50e106f87473386b3f7b65f593fed94500b8e1))

- Update changelog [skip ci] (#433) ([2b99ddf](https://github.com/aliyevaladddin/AladdinAI/commit/2b99ddf81f52f6dc8f9dee233583fd23471d17e4))

- Update changelog [skip ci] (#436) ([ad227bf](https://github.com/aliyevaladddin/AladdinAI/commit/ad227bf6d6bbb716a9522280f5865cab48492ec6))

- Bump axios from 1.17.0 to 1.18.1 in /frontend (#437) ([0103a69](https://github.com/aliyevaladddin/AladdinAI/commit/0103a69c3f0fde1e5471cd725952ac9c638369b0))

- Update changelog [skip ci] (#438) ([49a5e90](https://github.com/aliyevaladddin/AladdinAI/commit/49a5e90e79897411ff8913a4f9fbdbe3ebfff2f7))

- Update dependency overrides in package.json ([c2a55d0](https://github.com/aliyevaladddin/AladdinAI/commit/c2a55d0d0bcfe645d69d5ec212cbb81e96b7e84e))

- Update changelog [skip ci] (#439) ([2cc0c06](https://github.com/aliyevaladddin/AladdinAI/commit/2cc0c062d85fc2f392c308ad7ef2a9030d07c45b))

- Bump version to 2.2.2 across packages and documentation ([249b68a](https://github.com/aliyevaladddin/AladdinAI/commit/249b68aac3f58d6f964bd96fa47c28ce3a59d272))

## [v2.2.1] - 2026-07-09

### Dependencies

- Bump lucide-react from 1.21.0 to 1.23.0 in /frontend (#353) ([db7aea2](https://github.com/aliyevaladddin/AladdinAI/commit/db7aea2144971cad5d6507da1cac79768cbe5fd0))


### Features

- Score reward/quality_label at write time from loop out come (#368) ([8777cb9](https://github.com/aliyevaladddin/AladdinAI/commit/8777cb9db5e9d8a9339d1eea686f761480cc5fb1))

- Add funding field to package.json (#371) ([851f8d4](https://github.com/aliyevaladddin/AladdinAI/commit/851f8d4767429b378d6918491481f37d36d4ad43))

- Add skillspector dependency to CI workflow and requirements ([5a5bf15](https://github.com/aliyevaladddin/AladdinAI/commit/5a5bf15b674502cfbc23d6e8a478aab7f92ef6c7))


### Maintenance

- Update changelog [skip ci] (#341) ([d07d9a3](https://github.com/aliyevaladddin/AladdinAI/commit/d07d9a3d465f6ec27b35ee222f5db047bfc072ed))

- Update changelog [skip ci] (#342) ([2b2628a](https://github.com/aliyevaladddin/AladdinAI/commit/2b2628a7497bcd98194bc4ecd071b0c16c07a78b))

- Update changelog [skip ci] (#343) ([3c4e743](https://github.com/aliyevaladddin/AladdinAI/commit/3c4e743e5c80caa6ae17211ff2a01ba8c0b3fed1))

- Update changelog [skip ci] (#344) ([793d1ac](https://github.com/aliyevaladddin/AladdinAI/commit/793d1ac0eb79ec1ef7debcfbe04820f4c27a096f))

- Bump electron from 42.5.0 to 43.0.0 in /frontend (#354) ([7f4044c](https://github.com/aliyevaladddin/AladdinAI/commit/7f4044cb6020654542880a8b42e96ab60a3cb963))

- Update changelog [skip ci] (#355) ([af75c01](https://github.com/aliyevaladddin/AladdinAI/commit/af75c01f513f1f0dd4e77de2603bfbbafaf9c0c1))

- Update changelog (#358) ([976be0b](https://github.com/aliyevaladddin/AladdinAI/commit/976be0bb503feaee6788ef511c40dd5fe248cb15))

- Update changelog [skip ci] (#369) ([d9b4741](https://github.com/aliyevaladddin/AladdinAI/commit/d9b474189b459ec9a130f123408c7e59d5519a00))

- Update changelog [skip ci] (#372) ([1979f78](https://github.com/aliyevaladddin/AladdinAI/commit/1979f78b83903192db6b5c2eb35fdb00739f2cac))

- Update changelog [skip ci] (#373) ([a45c222](https://github.com/aliyevaladddin/AladdinAI/commit/a45c2228a9f30d3fb0fd03b8c898c0cb185ac972))

## [v2.2.0] - 2026-06-29

### Bug Fixes

- Move shebang to first line to resolve node syntax error ([369af3c](https://github.com/aliyevaladddin/AladdinAI/commit/369af3ca749fec98d76e0115eaaeba7b656cbd28))


### Documentation

- Update API documentation [skip ci] (#334) ([7921583](https://github.com/aliyevaladddin/AladdinAI/commit/792158343637bbc839de57d0a73bf362b6b4c604))


### Features

- Voice I/O, chat streaming, document indexing, security audit (#320) ([46b769f](https://github.com/aliyevaladddin/AladdinAI/commit/46b769f0f668fe53df19848f921c758fae97eb21))


### Maintenance

- Migrate from PyPDF2 to pypdf for PDF text extraction ([bf11f47](https://github.com/aliyevaladddin/AladdinAI/commit/bf11f47d89d3a5323b6ba051e2d4dc2dd15e6bbb))

- Update changelog [skip ci] (#333) ([ee56481](https://github.com/aliyevaladddin/AladdinAI/commit/ee56481ee0568459ccd547a4bf59247c8a7e1058))

- Update changelog [skip ci] (#332) ([53f71d8](https://github.com/aliyevaladddin/AladdinAI/commit/53f71d850a2f4fc8f3968c20dc87af16cfd4f70f))

- Update changelog [skip ci] (#338) ([e042089](https://github.com/aliyevaladddin/AladdinAI/commit/e0420897065b6b79397b47b18c8b2b9ca9f2257b))

- Update CLI release workflow to trigger on GitHub releases and allow manual version inputs ([acf3b2e](https://github.com/aliyevaladddin/AladdinAI/commit/acf3b2e90aa33366561b466259d410f67fe1297e))

- Update changelog [skip ci] (#339) ([e08a936](https://github.com/aliyevaladddin/AladdinAI/commit/e08a9360f20b880add607db682f7ad4700afd971))

- Update changelog [skip ci] (#340) ([9208874](https://github.com/aliyevaladddin/AladdinAI/commit/9208874c1a5b7f17ab38305b27cd830a4ae07412))

- Bump version to 2.2.0 and update deps [skip ci] ([e85619f](https://github.com/aliyevaladddin/AladdinAI/commit/e85619f8b85f8be8b6cf0ae8c711ee615e85a07b))

- Update cliff.toml to include dependency updates in changelog ([834ba68](https://github.com/aliyevaladddin/AladdinAI/commit/834ba6883167da6bc359bcf85037c2e97b92c9b1))

## [v2.1.9] - 2026-06-26

### Bug Fixes

- Update release workflow to push to main using HEAD reference ([2d88fc4](https://github.com/aliyevaladddin/AladdinAI/commit/2d88fc4b9cf5cccf75ed4098257f9eeecc1b4ab8))

- Order PII regex so PHONE no longer swallows SSN/credit cards ([66595b9](https://github.com/aliyevaladddin/AladdinAI/commit/66595b9c3b28152d49b5f2f13182ea12a44e9ce9))

- Harden secret validation and document docker socket security (#287) ([603a8e8](https://github.com/aliyevaladddin/AladdinAI/commit/603a8e88ccf0f4b004e54d4eb8f1d174649079ac))

- Update CLI release workflows and package config (#289) ([aaeedd3](https://github.com/aliyevaladddin/AladdinAI/commit/aaeedd3fb16822a33c95ebdcfa406b0ab2a51daa))

- Update CLI release workflows and package config (#291) ([727c31c](https://github.com/aliyevaladddin/AladdinAI/commit/727c31c00dd22318a9e285863855177036c43180))

- Set ALADDIN_ENV=test so backend tests boot under Postgres (#293) ([daada00](https://github.com/aliyevaladddin/AladdinAI/commit/daada000718bd2dbdde53b1bcfac0b70fb476cd6))

- Resolve SQLite concurrency locking and decouple database transactions, update Telegram bot command descriptions to English (#306) ([1ac68f4](https://github.com/aliyevaladddin/AladdinAI/commit/1ac68f470d4b003a1c8c902821b0b92b4a576b1a))


### Dependencies

- Bump alembic from 1.13.0 to 1.18.4 ([3b88382](https://github.com/aliyevaladddin/AladdinAI/commit/3b88382c276b96634bbee1919f532695f44fc81d))

- Bump codecov/codecov-action from 6 to 7 ([a4ee988](https://github.com/aliyevaladddin/AladdinAI/commit/a4ee98881b4ec2b86e352f73bf7d0b832ae69d7d))

- Bump uvicorn from 0.48.0 to 0.49.0 ([879b1b8](https://github.com/aliyevaladddin/AladdinAI/commit/879b1b8147f29fbd6b6d4e1db4adf90fcd3a96ae))

- Bump python-multipart from 0.0.29 to 0.0.32 ([1005ea0](https://github.com/aliyevaladddin/AladdinAI/commit/1005ea0e03237ef537a0fccbf9a48373e551fbc5))

- Bump asyncssh from 2.23.0 to 2.23.1 ([a985b84](https://github.com/aliyevaladddin/AladdinAI/commit/a985b84038d9e23316db27fb219c4f854f406bf2))

- Bump psycopg2-binary from 2.9.10 to 2.9.12 ([edf13b2](https://github.com/aliyevaladddin/AladdinAI/commit/edf13b24cf7a406944349cf77755d6ccbb3981e2))

- Bump hono from 4.12.23 to 4.12.25 in /frontend ([25c15f5](https://github.com/aliyevaladddin/AladdinAI/commit/25c15f586ab59222d8f0bc3e723181dff50d3072))

- Update certifi requirement from >=2026.5.20 to >=2026.6.17 ([5625a2c](https://github.com/aliyevaladddin/AladdinAI/commit/5625a2c6b53ef7433cae61ce28f4c9241462be32))

- Bump sqlalchemy from 2.0.50 to 2.0.51 ([f6e30dc](https://github.com/aliyevaladddin/AladdinAI/commit/f6e30dc580cb8aec5ca0f8e523c84611ebead957))

- Bump alembic from 1.13.0 to 1.18.4 ([772c922](https://github.com/aliyevaladddin/AladdinAI/commit/772c922fbaea52942df5581ccfaef07966b0b102))

- Bump fastapi from 0.136.3 to 0.137.1 ([85584d3](https://github.com/aliyevaladddin/AladdinAI/commit/85584d35369b8c297a4e43d3ca9b6a897c25a810))

- Bump the security-patches group in /frontend with 5 updates ([51873ef](https://github.com/aliyevaladddin/AladdinAI/commit/51873efa3e950d7d6b89a9c2f1fcb16b9b8628b5))

- Bump tailwind-merge from 3.5.0 to 3.6.0 in /frontend ([772858f](https://github.com/aliyevaladddin/AladdinAI/commit/772858f820b849aecffd5fe6a8830159eb88168e))

- Bump electron-serve from 1.3.0 to 3.0.1 in /frontend ([9baae53](https://github.com/aliyevaladddin/AladdinAI/commit/9baae53f0a81f78fe7c2cab15dbaaa7820c85a38))

- Bump rcf-protocol from 2.0.3 to 2.1.1 in /frontend ([b5fa711](https://github.com/aliyevaladddin/AladdinAI/commit/b5fa711816495c6901507adc85452dcf7994d2e6))

- Bump @base-ui/react from 1.4.1 to 1.5.0 in /frontend ([d787043](https://github.com/aliyevaladddin/AladdinAI/commit/d787043a9e4265757726655fa40c8f18422b292e))

- Bump lucide-react from 1.14.0 to 1.20.0 in /frontend ([0577e74](https://github.com/aliyevaladddin/AladdinAI/commit/0577e74f1d22e58a1311686e535f4f925d3f04c2))

- Bump actions/checkout from 6 to 7 (#274) ([89a5417](https://github.com/aliyevaladddin/AladdinAI/commit/89a5417b2b57199435fd290fd6de9a7a27953add))

- Bump pydantic-settings from 2.14.1 to 2.14.2 (#276) ([f5f6306](https://github.com/aliyevaladddin/AladdinAI/commit/f5f63067ba1b34bfa8b8d08936ee40bbfd1577b2))

- Bump @base-ui/react from 1.5.0 to 1.6.0 in /frontend (#277) ([6e4ea59](https://github.com/aliyevaladddin/AladdinAI/commit/6e4ea59fffa775fda5b20d056456cce470e39514))

- Bump lucide-react from 1.20.0 to 1.21.0 in /frontend (#280) ([a3a1fff](https://github.com/aliyevaladddin/AladdinAI/commit/a3a1fffc2038801281676c402665295dc3937b7a))

- Bump shadcn from 4.6.0 to 4.11.0 in /frontend (#284) ([0e3031b](https://github.com/aliyevaladddin/AladdinAI/commit/0e3031bb1dc2412f327f98a77265e1de829d2e95))


### Documentation

- Add README files for GitHub, devcontainer, and guides directories ([8521178](https://github.com/aliyevaladddin/AladdinAI/commit/85211787005c985bc25f38f39dcac7172f73be19))

- Update API documentation [skip ci] (#286) ([4a34dfd](https://github.com/aliyevaladddin/AladdinAI/commit/4a34dfd697114c2b1c959f11b817daac057ce332))

- Update API documentation [skip ci] (#297) ([5f95fd9](https://github.com/aliyevaladddin/AladdinAI/commit/5f95fd9abca831d8ee6f4fc3a510adc51d56b1c9))

- Update API documentation [skip ci] (#308) ([4e8803a](https://github.com/aliyevaladddin/AladdinAI/commit/4e8803ad33fc48743cb5ba1fe8b736327c61ac52))


### Features

- Add js-yaml dependency to frontend package.json ([4b8f7b3](https://github.com/aliyevaladddin/AladdinAI/commit/4b8f7b3b15a0f267b95eb433fd13a099bb793537))

- Add @babel/core and dompurify dependencies to frontend package.json ([929a849](https://github.com/aliyevaladddin/AladdinAI/commit/929a84937ee4f0de8003caef2d9778c71c46f9a6))

- Use input_type=passage when indexing facts for NIM embeddings ([f50fa7a](https://github.com/aliyevaladddin/AladdinAI/commit/f50fa7a4d247314f1dd1a62941efbeda5233a20e))

- Env-driven CORS, IP rate limiting, lifespan, secret validation ([87b13be](https://github.com/aliyevaladddin/AladdinAI/commit/87b13be988a9213e337a3957ddd110cae8db1cd1))

- Implement dynamic channel agent binding and UI selection (#295) ([49a28fe](https://github.com/aliyevaladddin/AladdinAI/commit/49a28fefa750618ed3f632c84eff0e5b86368423))


### Maintenance

- Update changelog [skip ci] ([bab9a2c](https://github.com/aliyevaladddin/AladdinAI/commit/bab9a2c9b37148a54345cffaac7e51719df89000))

- Update changelog [skip ci] ([4cebe47](https://github.com/aliyevaladddin/AladdinAI/commit/4cebe4798cb29ec77aa2cb982f399fd45e766c47))

- Update changelog [skip ci] ([f9e29ae](https://github.com/aliyevaladddin/AladdinAI/commit/f9e29ae7f99c83dac9b5437542b8af7c7c08c075))

- Bump shell-quote from 1.8.3 to 1.8.4 in /frontend ([e224059](https://github.com/aliyevaladddin/AladdinAI/commit/e224059018963be8df3d7b86e65978da6a320f7d))

- Bump form-data from 4.0.5 to 4.0.6 in /frontend ([16d24cd](https://github.com/aliyevaladddin/AladdinAI/commit/16d24cd2ec45f4d4d18af66ea5cf68ced5b8ab25))

- Update changelog [skip ci] ([5a7b7b7](https://github.com/aliyevaladddin/AladdinAI/commit/5a7b7b74af2520607cd79a5dfe851a0948c283cf))

- Add dependabot configuration for frontend and automate dependency security patching during release ([4ea684d](https://github.com/aliyevaladddin/AladdinAI/commit/4ea684db0dba71ecc87fe05e60b0fc53ffcca773))

- Bump electron-builder in /frontend ([03f459d](https://github.com/aliyevaladddin/AladdinAI/commit/03f459d2c3a226ba2762590514714ad530d39fad))

- Bump wait-on from 7.2.0 to 9.0.10 in /frontend ([e913529](https://github.com/aliyevaladddin/AladdinAI/commit/e913529edc2b0031c84a821b724a0576bc6bf917))

- Bump concurrently from 8.2.2 to 10.0.3 in /frontend ([0b8c68e](https://github.com/aliyevaladddin/AladdinAI/commit/0b8c68e9cb706037482b12de59a0fcc763d8c1d1))

- Bump eslint from 9.39.4 to 10.5.0 in /frontend ([514ef8e](https://github.com/aliyevaladddin/AladdinAI/commit/514ef8ef65740fb0441dd5d2f46e627227164359))

- Rename .github/README.md to .github/WORKFLOWS.md ([07b5b38](https://github.com/aliyevaladddin/AladdinAI/commit/07b5b38adcf7bc1c55c73cb567cbabb031855f87))

- Update changelog [skip ci] ([b590ba6](https://github.com/aliyevaladddin/AladdinAI/commit/b590ba6f7f86aa04ccb97169d1148ffc15a32f8c))

- Bump typescript from 5.9.3 to 6.0.3 in /frontend (#278) ([7a973e3](https://github.com/aliyevaladddin/AladdinAI/commit/7a973e3eb154029350eee944a2279123a9068d82))

- Bump electron from 39.8.5 to 42.4.1 in /frontend (#279) ([e019cde](https://github.com/aliyevaladddin/AladdinAI/commit/e019cde3b98f2432404485ff2d9b4653a2ab03b6))

- Bump tailwindcss from 4.2.4 to 4.3.1 in /frontend (#281) ([54bf91a](https://github.com/aliyevaladddin/AladdinAI/commit/54bf91a5d4be7621aecff29b74611c45e27d1665))

- Bump @tailwindcss/postcss in /frontend (#282) ([9d1634d](https://github.com/aliyevaladddin/AladdinAI/commit/9d1634d9b3d370381f0db7241ccb575af2efe02d))

- Bump @types/node from 20.19.39 to 26.0.0 in /frontend (#283) ([c7b0c72](https://github.com/aliyevaladddin/AladdinAI/commit/c7b0c72e09b5b30db52e4d622090ab19d28622bd))

- Update changelog [skip ci] (#285) ([93b246f](https://github.com/aliyevaladddin/AladdinAI/commit/93b246fb911cab0adc563a15b83a7348c1955dee))

- Update changelog [skip ci] (#288) ([5845a5b](https://github.com/aliyevaladddin/AladdinAI/commit/5845a5b1d44f08d09b647cf586be460665be5390))

- Update changelog [skip ci] (#290) ([305d6da](https://github.com/aliyevaladddin/AladdinAI/commit/305d6dade5b9549e2c142a5100c096a0d24bd825))

- Update changelog [skip ci] (#292) ([4359aa3](https://github.com/aliyevaladddin/AladdinAI/commit/4359aa367c45741573f79f8c12a753239b980c5a))

- Update changelog [skip ci] (#294) ([a6a8133](https://github.com/aliyevaladddin/AladdinAI/commit/a6a8133c94657a23899f327cbbe421295f6cef46))

- Update changelog [skip ci] (#296) ([86afacd](https://github.com/aliyevaladddin/AladdinAI/commit/86afacd085bf4f437fe059a3f700b4abf5cd2f07))

- Update changelog [skip ci] (#300) ([3a86fca](https://github.com/aliyevaladddin/AladdinAI/commit/3a86fca0d92cb173653773fa74ffc722dff66355))

- Initialize RCF protocol and protect assets (#301) ([4063b51](https://github.com/aliyevaladddin/AladdinAI/commit/4063b51a97b3fd2f88055bb719f596b5ad7ca13f))

- Update changelog [skip ci] (#302) ([927af6c](https://github.com/aliyevaladddin/AladdinAI/commit/927af6cd47e610f2f5d9fb152e0aeea75a9d769b))

- Update changelog [skip ci] (#305) ([dd77d10](https://github.com/aliyevaladddin/AladdinAI/commit/dd77d10d62b41dd0c3185cae5614fc5f36215492))

- Update changelog [skip ci] (#307) ([09acc30](https://github.com/aliyevaladddin/AladdinAI/commit/09acc3062fcc91d131424b482d796306ffa89aa1))


### Testing

- Add tests for safety PII, memory embeddings, agent runner ([046755c](https://github.com/aliyevaladddin/AladdinAI/commit/046755c05a5ae30051735eacf6e9174f472fcba4))


### Efactor

- Remove RCF:PROTECTED placeholders from codebase and documentation ([eea4ba4](https://github.com/aliyevaladddin/AladdinAI/commit/eea4ba46ae601fc76ec9c085f82dc7ed4213c559))

## [v2.1.8] - 2026-06-08

### Bug Fixes

- Update dependency overrides and improve HTML sanitization logic in dashboard preview ([049a871](https://github.com/aliyevaladddin/AladdinAI/commit/049a87191ed90813e4a9cb100feec77c337b5c47))

- Sanitize and validate attachment filenames to prevent path traversal vulnerabilities ([9c1f198](https://github.com/aliyevaladddin/AladdinAI/commit/9c1f19890aba7ce5d00ddffb3fb291c22a413919))

- Simplify path traversal validation for CRM activity attachments using prefix checking ([d3701a9](https://github.com/aliyevaladddin/AladdinAI/commit/d3701a9cc20e980f31979fcf89e9cc959e808c61))


### Dependencies

- Bump hono from 4.12.15 to 4.12.23 in /frontend ([33d1b55](https://github.com/aliyevaladddin/AladdinAI/commit/33d1b55cb784c5bf091ab2120196b13c55a30920))

- Bump fast-uri from 3.1.0 to 3.1.2 in /frontend ([35c020f](https://github.com/aliyevaladddin/AladdinAI/commit/35c020f6d9019215ffdc068808454d1ae260f6b9))

- Bump qs from 6.15.1 to 6.15.2 in /frontend ([e55f809](https://github.com/aliyevaladddin/AladdinAI/commit/e55f8095da497c4078b391ea7b7c9ac8fdf3e434))

- Bump ip-address and express-rate-limit in /frontend ([9300875](https://github.com/aliyevaladddin/AladdinAI/commit/9300875874197802db806e313c77315b5722190f))


### Documentation

- Update API documentation [skip ci] ([e9c88f0](https://github.com/aliyevaladddin/AladdinAI/commit/e9c88f089f7a178c545be8a5933a97e6123f6a8a))


### Features

- Update doc generation workflow to create PRs and enable auto-merge using a GitHub App token ([d900c4c](https://github.com/aliyevaladddin/AladdinAI/commit/d900c4ca89c04c7d53d1d9edfba6dca94c77d067))


### Maintenance

- Update changelog [skip ci] ([c5485c8](https://github.com/aliyevaladddin/AladdinAI/commit/c5485c857db453759a1cce53ef801eda1eed8902))

- Bump axios from 1.15.2 to 1.17.0 in /frontend ([3821bbb](https://github.com/aliyevaladddin/AladdinAI/commit/3821bbb6b50c048f4344e9b8ada52d564b6fac97))

- Update changelog [skip ci] ([2fc7462](https://github.com/aliyevaladddin/AladdinAI/commit/2fc7462a5601cd49d526de3e4e1761332b7326de))

- Bump electron from 30.5.1 to 39.8.5 in /frontend ([bcd088f](https://github.com/aliyevaladddin/AladdinAI/commit/bcd088fd93b5fdae37660a8b159a59d61ce799c3))

- Update xlsx dependency to version 0.20.2 via direct tarball link ([4259ebf](https://github.com/aliyevaladddin/AladdinAI/commit/4259ebf6c407fee3e9fdd90e3d8bcd497b33f4df))

- Update xlsx dependency to official npm registry package with scoped configuration ([f7be37a](https://github.com/aliyevaladddin/AladdinAI/commit/f7be37ad1c7dc957b469f157ace5e18b464580fe))

- Update dependencies in package-lock.json ([c7ecbac](https://github.com/aliyevaladddin/AladdinAI/commit/c7ecbacd11c118c0d7f307605383acc4803e52fe))

- Add package overrides for brace-expansion and qs to address security vulnerabilities ([5505659](https://github.com/aliyevaladddin/AladdinAI/commit/55056597b31627091b302576b0ff0a07e6136a67))

- Remove dependency overrides in package.json and update lockfile ([28e46b0](https://github.com/aliyevaladddin/AladdinAI/commit/28e46b066e09d26ebf079afc7b5f5a9bbf394e61))

- Update frontend dependencies in package-lock.json ([d134e8c](https://github.com/aliyevaladddin/AladdinAI/commit/d134e8ce1bf3a6d152daab74668b33224e475d4a))

- Add package overrides for brace-expansion, qs, and postcss to resolve security vulnerabilities ([9c08e5c](https://github.com/aliyevaladddin/AladdinAI/commit/9c08e5c8c47b8b5705533a990ba860b51f7c94a0))

- Update changelog [skip ci] ([4365a64](https://github.com/aliyevaladddin/AladdinAI/commit/4365a64db41e6e82dfab2c606837782f3a002c58))

- Update changelog [skip ci] ([1e17782](https://github.com/aliyevaladddin/AladdinAI/commit/1e17782206cc84344c810e684c25f8b0923ace69))

- Update changelog [skip ci] ([2f08418](https://github.com/aliyevaladddin/AladdinAI/commit/2f084185a03136658e17bf0b01c139e72f4327f2))

- Skip electron binary download during dependency installation in CI workflows ([ba7930b](https://github.com/aliyevaladddin/AladdinAI/commit/ba7930b8701cb460760fa3bbef960b0a54dbd2b2))

- Update changelog [skip ci] ([88b6edb](https://github.com/aliyevaladddin/AladdinAI/commit/88b6edb19759d7f7c838075831c66dbee6a1da80))

- Update changelog [skip ci] ([0be28b2](https://github.com/aliyevaladddin/AladdinAI/commit/0be28b2c768bda64f9b1dfdc3a1e79cae5d77718))


### Refactor

- Replace regex-based HTML stripping with a robust MLStripper implementation in _strip_html ([38f25aa](https://github.com/aliyevaladddin/AladdinAI/commit/38f25aa849db426bbca73d1304ad469781fde87c))

- Address CodeQL security alerts and enforce least privilege workflow permissions ([0e73831](https://github.com/aliyevaladddin/AladdinAI/commit/0e73831711d34d301be5fd7b889dbb90274cceb5))

- Resolve ruff lint errors and fix channels_email stack trace exposure ([c6c0718](https://github.com/aliyevaladddin/AladdinAI/commit/c6c0718d5f31b619ec97891cc7eb2b0d6d9b8c87))

## [v2.1.7] - 2026-06-06

### Dependencies

- Bump bcrypt from 4.2.0 to 5.0.0 ([3d27684](https://github.com/aliyevaladddin/AladdinAI/commit/3d27684a0bd639cd50578fc1323e3ed62772973e))

- Bump actions/setup-python from 5 to 6 ([d56ea67](https://github.com/aliyevaladddin/AladdinAI/commit/d56ea67cbf163dc4b77daf08a32c45c97d22e52f))

- Bump docker/setup-buildx-action from 3 to 4 ([9e3361c](https://github.com/aliyevaladddin/AladdinAI/commit/9e3361c3bee988f56e0f8f5e4d051db02760f67a))

- Bump actions/checkout from 4 to 6 ([9a34e37](https://github.com/aliyevaladddin/AladdinAI/commit/9a34e376d68b02e563e4531e2f33a2c87dab555d))

- Bump codecov/codecov-action from 4 to 6 ([8679918](https://github.com/aliyevaladddin/AladdinAI/commit/86799183126692385d7abecf8300b4bf561fc393))

- Bump actions/setup-node from 4 to 6 ([a056fb9](https://github.com/aliyevaladddin/AladdinAI/commit/a056fb98c0071eb5e03feb55823d089791e572b7))

- Bump sqlparse from 0.5.3 to 0.5.5 ([bc945ab](https://github.com/aliyevaladddin/AladdinAI/commit/bc945ab792aa8062ded5ca09315665dbfdead126))

- Bump apscheduler from 3.10.4 to 3.11.2 ([f30b080](https://github.com/aliyevaladddin/AladdinAI/commit/f30b080dc84889fe29308d2fcaea4c3bcbf8c8f3))

- Bump python-jose from 3.4.0 to 3.5.0 ([e425d2f](https://github.com/aliyevaladddin/AladdinAI/commit/e425d2f3bfe8e1c6dd5373b58f07175600280963))

- Bump pydantic from 2.9.0 to 2.13.4 ([94b5964](https://github.com/aliyevaladddin/AladdinAI/commit/94b59649cde77b319483020d9709c84c80da4370))


### Maintenance

- Update changelog [skip ci] ([b202eda](https://github.com/aliyevaladddin/AladdinAI/commit/b202eda14b7c5ca10261ad30722a568c9322bae4))

- Update changelog [skip ci] ([3a6b72a](https://github.com/aliyevaladddin/AladdinAI/commit/3a6b72a12905c4b0b1a481cbc795b4b6e9dd23f8))

## [v2.1.6] - 2026-06-06

### Bug Fixes

- Buffer upstream response body in-memory to prevent stream truncation issues ([ab0ab61](https://github.com/aliyevaladddin/AladdinAI/commit/ab0ab61009f613953a6b2ea1ee3302fe03f3b492))

- Add error handling for request body reading and refine proxy error reporting ([ee260c6](https://github.com/aliyevaladddin/AladdinAI/commit/ee260c6eeda75e924e547e27dc9f4cadb9ec7dcc))

- Add robust JSON parsing and error handling to API request methods ([36269e2](https://github.com/aliyevaladddin/AladdinAI/commit/36269e2bd0272ddce4d2590e8c9cbeca9d1edc64))

- Strip content-length header from upstream responses to prevent stream truncation errors ([26f5b74](https://github.com/aliyevaladddin/AladdinAI/commit/26f5b74528ba16028f95e15f10adbebb827a4764))

- Resolve potential connection handling issues in chat router endpoints ([53b4407](https://github.com/aliyevaladddin/AladdinAI/commit/53b44078e75df99969197aa85f7747e7fc692075))

- Update database engine config with WAL mode and busy timeout ([380c93a](https://github.com/aliyevaladddin/AladdinAI/commit/380c93a5e74e21366c874efa3a32287f0dc5b703))

- Remove unused sqlalchemy text import ([89af84c](https://github.com/aliyevaladddin/AladdinAI/commit/89af84c01e473cd78ef69580032c97e9b89fc441))

- Resolve busy_timeout redundancy and tighten docs regex in cliff ([78693e4](https://github.com/aliyevaladddin/AladdinAI/commit/78693e407fdf324ca9bdbd1ddecedde01e6f65a9))

- Resolve race condition, silent merge failure and clarify connect_args ([9de8f32](https://github.com/aliyevaladddin/AladdinAI/commit/9de8f32bad84bd2138b7a0b067d55989391d54a5))

- Replace immediate merge with GitHub native auto-merge via GraphQL ([b046891](https://github.com/aliyevaladddin/AladdinAI/commit/b04689155a09c8407d7d686b1845398e7b5035b5))

- Remove unused pathlib.Path import in media_storage (ruff F401) ([eb7d5d4](https://github.com/aliyevaladddin/AladdinAI/commit/eb7d5d44b5fd03a1bdbadae17886abf5d07063a0))

- Address security vulnerabilities and bugs in SQL playground ([a4b8730](https://github.com/aliyevaladddin/AladdinAI/commit/a4b8730acc30913ba66eb0e75d19a90c17faffc5))

- Prevent ReDoS vulnerability in SQL comment stripping ([669593c](https://github.com/aliyevaladddin/AladdinAI/commit/669593c09fd737ab54a49a48a45512a0db226939))

- Eliminate remaining ReDoS vulnerabilities in comment stripping ([dc23bd8](https://github.com/aliyevaladddin/AladdinAI/commit/dc23bd8b7ac4a890bd8d245e9c1ef5da74e8a532))

- Replace regex with string operations to eliminate ReDoS ([318e958](https://github.com/aliyevaladddin/AladdinAI/commit/318e95875cd41cdebe15cb787c35d55d0bad7b39))

- Disable parallel_tool_calls for NVIDIA NIM compatibility ([329d865](https://github.com/aliyevaladddin/AladdinAI/commit/329d865d5daec9f903969e46d204d6019fca3ff0))

- Pass tool_choice=auto explicitly so NIM calls tools autonomously ([1cfacb6](https://github.com/aliyevaladddin/AladdinAI/commit/1cfacb6888f986d6fc2a9d2926f0e95729d13b36))

- Disable inter-agent tools by default to prevent small model hallucination of agent IDs ([58a7b74](https://github.com/aliyevaladddin/AladdinAI/commit/58a7b74ea5b84d1d138062222a0883cddd231f88))

- Revert remoteUser to vscode to preserve safe file ownership ([0ce7ccc](https://github.com/aliyevaladddin/AladdinAI/commit/0ce7cccf76a67be9eabe9bdd643273fb9baa6e32))

- Resolve CI failures, test isolation, and test suite issues ([f532ae7](https://github.com/aliyevaladddin/AladdinAI/commit/f532ae72703dc1b91788c8fa604ee345361a674f))

- Add backend root path to sys.path in conftest.py ([abad0cb](https://github.com/aliyevaladddin/AladdinAI/commit/abad0cbabf70ddb64afd6796a1f9d4a3120fd53d))

- Automatically rewrite postgresql:// scheme to use asyncpg driver ([0fa46c7](https://github.com/aliyevaladddin/AladdinAI/commit/0fa46c764da1e342d6cdddb9191ab16515341306))

- Use npx openapi-markdown for API doc generation in CI ([03179ea](https://github.com/aliyevaladddin/AladdinAI/commit/03179ea7809694d7dccfab8ae00c3bd04bf432a3))


### CI

- Drop Node 20 from CI matrix, require Node 22 LTS minimum ([8ba3409](https://github.com/aliyevaladddin/AladdinAI/commit/8ba34096118f0b6ad1ea3d580747dca18e4491ea))


### Dependencies

- Bump tar and electron-builder in /frontend ([a9a3746](https://github.com/aliyevaladddin/AladdinAI/commit/a9a37461ce782f48dec9a1543c707c80dc23a700))


### Documentation

- Add INTEGRATIONS.md with memory layer docs and Origin integration ([06372f1](https://github.com/aliyevaladddin/AladdinAI/commit/06372f16523a48f9ff28dfa782f19a8932791378))

- Fix model name prefix and API route parameter in INTEGRATIONS.md ([078831d](https://github.com/aliyevaladddin/AladdinAI/commit/078831d5bd65205eac59dee9174f1508d254e766))

- Fix vector index filter fields and add npx security notice ([defc359](https://github.com/aliyevaladddin/AladdinAI/commit/defc359c120b0ac5fe06fa1f92c148ff5d347be2))

- Add Operations section covering logs, upgrades, recovery, permissions and agent limits ([db1000c](https://github.com/aliyevaladddin/AladdinAI/commit/db1000c3842da1c23bd62f354402b2876c75e495))

- Add security documentation for SQL playground endpoint ([b6ea353](https://github.com/aliyevaladddin/AladdinAI/commit/b6ea3535a6cb5a6557c92b4afbba011e100db6c1))

- Add nosec annotation for intentional SQL execution ([1e0133b](https://github.com/aliyevaladddin/AladdinAI/commit/1e0133bfb2bf18ddf79c95c85ffc077ea542fc1e))

- Generate API documentation and OpenAPI specification for the agent orchestration system ([3653c9b](https://github.com/aliyevaladddin/AladdinAI/commit/3653c9bd36769b99f6034771397bab735a357143))


### Features

- Add existence checks to timestamp migration and expand target table list ([7da73c8](https://github.com/aliyevaladddin/AladdinAI/commit/7da73c887ca96301c602af4e4577122dd317901b))

- Add Notification model and create corresponding database table ([9999afa](https://github.com/aliyevaladddin/AladdinAI/commit/9999afa9240c5a65bbdf18de303e1b388955a9ba))

- Allow localhost URLs in development for WAHA integration ([dde2d67](https://github.com/aliyevaladddin/AladdinAI/commit/dde2d674482ef568086ad069ecc0a48236e18d95))

- Add email tool, UI improvements, and image generation ([6cc1f66](https://github.com/aliyevaladddin/AladdinAI/commit/6cc1f668df7f12d4c3fb9b369c8f43f9410523de))

- Add send_email tool to default agent capabilities ([b8f6c10](https://github.com/aliyevaladddin/AladdinAI/commit/b8f6c104c00cd25872663b8a1ba3092b895d3b8b))

- Add git-cliff config and update changelog workflow ([61e1d98](https://github.com/aliyevaladddin/AladdinAI/commit/61e1d986c36f20cf19f092fb53491299d1395839))

- MongoDB GridFS media storage + provider-independent models ([48c3454](https://github.com/aliyevaladddin/AladdinAI/commit/48c3454d1c39708b523d3d73877ce5aa3243a9ef))

- SQL playground enhancements + storage settings UI ([9c799da](https://github.com/aliyevaladddin/AladdinAI/commit/9c799dac3043ee8728d1aaf1d07e7a54d90cd707))

- Add agent execution tracing and comprehensive documentation system ([7188083](https://github.com/aliyevaladddin/AladdinAI/commit/7188083c09868be3460ba2a90db1a03cc2b7f061))

- Add GitHub action for AladdinAI multi-agent deployment ([c35f16e](https://github.com/aliyevaladddin/AladdinAI/commit/c35f16eb493afb4b37d2a8d58a360f7b15d9cc03))

- Update Docker image to bookworm, add sudo user support, and set remoteUser to root ([d6977ae](https://github.com/aliyevaladddin/AladdinAI/commit/d6977ae8e10a3a47cce9d58eff90537fe2c47d10))


### Maintenance

- Update changelog [skip ci] ([7a97c50](https://github.com/aliyevaladddin/AladdinAI/commit/7a97c50596542ef4a83548c176d49ac83d933da8))

- Update GitHub Actions versions across workflow configurations ([da7cb98](https://github.com/aliyevaladddin/AladdinAI/commit/da7cb980fcc30282060f3052f9a6f85e12bd416c))

- Update changelog [skip ci] ([49a4b65](https://github.com/aliyevaladddin/AladdinAI/commit/49a4b6509af70e3ac3e10f73a271226924cc1759))

- Add ESM-only remark and rehype packages to transpilePackages in next.config.ts ([dfbfec2](https://github.com/aliyevaladddin/AladdinAI/commit/dfbfec2a6953466a139e5449f3f3e61368451bce))

- Remove unused package.json and package-lock.json dependencies ([4872efd](https://github.com/aliyevaladddin/AladdinAI/commit/4872efda19fdd469f2157c121f3cbf1e3cf469e2))

- Update changelog [skip ci] ([43edbfa](https://github.com/aliyevaladddin/AladdinAI/commit/43edbfa2124ef46acdf4173feaf374c6e664b8c9))

- Update changelog [skip ci] ([0d02b79](https://github.com/aliyevaladddin/AladdinAI/commit/0d02b79739bfaa0893d91c929f6cf97b185fbc0d))

- Update changelog [skip ci] ([25b653e](https://github.com/aliyevaladddin/AladdinAI/commit/25b653e0c94122675bd93ef8d026266efaf19edd))

- Update changelog [skip ci] ([fc3bb12](https://github.com/aliyevaladddin/AladdinAI/commit/fc3bb12aad2abef2f18ab9104efaa8d2d82016b6))

- Ignore SQLite temporary write-ahead log and shared memory files ([8f4d4d7](https://github.com/aliyevaladddin/AladdinAI/commit/8f4d4d7ae2695dbc098cacb32b21ee800382d27b))

- Update changelog [skip ci] ([2e4ba8f](https://github.com/aliyevaladddin/AladdinAI/commit/2e4ba8f0fee9579cee673e971587aedc38a59039))

- Update changelog [skip ci] ([a5fe2d5](https://github.com/aliyevaladddin/AladdinAI/commit/a5fe2d56738484a0c1fd65763443f0497a916b99))

- Update changelog [skip ci] ([25af22a](https://github.com/aliyevaladddin/AladdinAI/commit/25af22a3e27e81f7cfbcf86d2577f504700197ec))

- Update changelog [skip ci] ([dfa7777](https://github.com/aliyevaladddin/AladdinAI/commit/dfa777720913f07c128ce22348e73c15ea7d15a5))

- Update changelog [skip ci] ([8deb311](https://github.com/aliyevaladddin/AladdinAI/commit/8deb311de39df017a02494e28c2f8674b01dd760))

- Update changelog [skip ci] ([b1c4731](https://github.com/aliyevaladddin/AladdinAI/commit/b1c47317282a5496cb494eb61bad34e29c3075b2))

- Downgrade github actions to stable versions for checkout and setup-python ([5765e22](https://github.com/aliyevaladddin/AladdinAI/commit/5765e2296b1e11d6850bdc9dcc5142aead4314ad))

- Update changelog [skip ci] ([15ec6ee](https://github.com/aliyevaladddin/AladdinAI/commit/15ec6ee1e6c6e95833d31c71b4a451a947d47ac3))


### Refactor

- Migrate database timestamps to timezone-aware format and update SQLAlchemy type mapping ([1d42f98](https://github.com/aliyevaladddin/AladdinAI/commit/1d42f980e22e90747fb04ecbc3e2ed5e29ba216c))

- Remove unused sqlalchemy import in timestamp migration script ([ec89995](https://github.com/aliyevaladddin/AladdinAI/commit/ec89995fb739504c77b4b46e663c21abcd8b218c))

- Improve Markdown code block detection and type safety in chat interface ([296cedd](https://github.com/aliyevaladddin/AladdinAI/commit/296ceddcf0323fc326f1a2ef0921e8310bd044aa))

- Make system settings read-only by default and ensure concurrency-safe database persistence with a unique user_id constraint while fixing OpenAI embedding dimension support. ([9d9b26c](https://github.com/aliyevaladddin/AladdinAI/commit/9d9b26ce51e7e45c611eea97b3c060005a37d92d))

- Remove unused AsyncSession import and simplify forbidden keyword error string formatting ([39349a4](https://github.com/aliyevaladddin/AladdinAI/commit/39349a4d30485dc314cf5300c844981af345a6d3))

- Remove automated version update workflow and dynamically sync API version from CLI package.json ([34aab68](https://github.com/aliyevaladddin/AladdinAI/commit/34aab68140d9d55dfa1b70384342436050b82e5e))

- Remove unused imports across tests and services and clean up console output formatting ([00f97c4](https://github.com/aliyevaladddin/AladdinAI/commit/00f97c463943f1b41c6f9da69b0bca45adc38984))


### Security

- Mask sensitive API keys with password prompt in setup wizard ([4825ed8](https://github.com/aliyevaladddin/AladdinAI/commit/4825ed8cd728453de1281150c13d35263e6ef2bc))

## [v2.1.5] - 2026-05-31

### Bug Fixes

- Prepend https protocol to Render service hostnames in backend proxy target ([348f0f4](https://github.com/aliyevaladddin/AladdinAI/commit/348f0f434fe30da4eedfd05fff32c9f1be0514c5))


### Features

- Add Render configuration for AladdinAI-frontend service with environment variable bindings ([d8b3ec8](https://github.com/aliyevaladddin/AladdinAI/commit/d8b3ec837f4f447d02a282fbedaf439477d12f8c))

- Replace build-time rewrites with a runtime API proxy route handler to support dynamic environment variables ([301ff72](https://github.com/aliyevaladddin/AladdinAI/commit/301ff7218dc29a5ad6a7f0d905cc444b26160592))


### Maintenance

- Update build cache and transition to script-based entrypoint execution ([9f30105](https://github.com/aliyevaladddin/AladdinAI/commit/9f301050a968297b14a6089075d52854a021b23f))

- Update production Dockerfile to use Render-compatible port defaults and dynamic healthcheck configuration ([635352b](https://github.com/aliyevaladddin/AladdinAI/commit/635352bd254faa5275c0ea2164e7305c97c02a98))

- Update changelog [skip ci] ([e9489e2](https://github.com/aliyevaladddin/AladdinAI/commit/e9489e2645a0d481afd8b6204f9f00d50fcd57bb))

- Configure API URL and set HOSTNAME for Render deployment in Dockerfile.prod ([2375d5c](https://github.com/aliyevaladddin/AladdinAI/commit/2375d5ce10b8a8c6cdf0df63e89d0b05775bcbd4))

- Update changelog [skip ci] ([39168a5](https://github.com/aliyevaladddin/AladdinAI/commit/39168a57b0e03d16472cddf97b37376747a4e111))

- Remove railway.json configuration file ([213353d](https://github.com/aliyevaladddin/AladdinAI/commit/213353d50ddfcfc4979782a07b0a6e5be98421d4))

- Update backend URL configuration and set proxy for API requests in render.yaml ([721e05e](https://github.com/aliyevaladddin/AladdinAI/commit/721e05e9ecb3dbb36d5e3c3d210a08a55df3f202))

- Update changelog [skip ci] ([8b9e9df](https://github.com/aliyevaladddin/AladdinAI/commit/8b9e9df064f383bccca0aecd6770e9435dee4a5f))

- Replace dynamic BACKEND_INTERNAL_URL reference with manual environment variable configuration ([7afe202](https://github.com/aliyevaladddin/AladdinAI/commit/7afe202985f1f8dbb4f6a9904a89da3852f4a8c3))

## [v2.1.4] - 2026-05-31

### Bug Fixes

- Update dockerfilePath from /backend/Dockerfile to Dockerfile ([7149521](https://github.com/aliyevaladddin/AladdinAI/commit/714952117a3f66df213adc9cf6f955277669d43d))

- Replace preDeployCommand with startCommand for SQLite migrations (#125) ([74e7185](https://github.com/aliyevaladddin/AladdinAI/commit/74e7185a070ede46249c63aa39ab8434343da4dc))

- Move alembic migrations to preDeployCommand, remove multi-region ([a04e523](https://github.com/aliyevaladddin/AladdinAI/commit/a04e523394e8eedc1e9d886f1349e95831231edc))

- Replace preDeployCommand with startCommand for SQLite migrations ([09fa4f6](https://github.com/aliyevaladddin/AladdinAI/commit/09fa4f63c54cafc87fee5fccc1bbe1ddb985e63c))

- Correct alembic migration chain and move to startCommand for SQLite ([916061e](https://github.com/aliyevaladddin/AladdinAI/commit/916061ef722567ae5acf407e75ec5ec2b144363b))

- Move railway.json to repo root with correct paths ([88e4dec](https://github.com/aliyevaladddin/AladdinAI/commit/88e4dec586a65d057852a0ec4163135f184f51b7))

- Add dockerContext to railway.json ([b95c800](https://github.com/aliyevaladddin/AladdinAI/commit/b95c8006a033dc5021eeef9ebec56ab9e1bddff8))

- Remove dockerContext from railway.json to prevent double backend/ path lookup ([48afdea](https://github.com/aliyevaladddin/AladdinAI/commit/48afdea4a63f3622ff53992173870b9b8aafbcdd))

- Use sync postgresql driver for Alembic migrations on Render ([da3343d](https://github.com/aliyevaladddin/AladdinAI/commit/da3343d4a2c07f6221141886c7b37f9646729af3))

- Add psycopg2-binary for Alembic sync migrations ([97bfbae](https://github.com/aliyevaladddin/AladdinAI/commit/97bfbae42100226502f41bb94f18530acb9416b6))

- Add verbose logging to render_init.sh for debugging migrations ([d57f4f1](https://github.com/aliyevaladddin/AladdinAI/commit/d57f4f165b3166648fa92108d89d29da54cda966))

- Force Docker rebuild and upgrade pip to fix PyJWT import ([c548292](https://github.com/aliyevaladddin/AladdinAI/commit/c54829235d6c9e810e8526ad7ceb4c8138305dc0))


### Features

- Configure Render deployment with Postgres and async driver conversion ([8688fba](https://github.com/aliyevaladddin/AladdinAI/commit/8688fba258f5bf932bee64683e4dfc005a8b6477))


### Maintenance

- Update changelog [skip ci] (#124) ([431b030](https://github.com/aliyevaladddin/AladdinAI/commit/431b0305ced41410a0e2f65a66ec742f846d315a))

- Update changelog [skip ci] (#126) ([6bb7ed1](https://github.com/aliyevaladddin/AladdinAI/commit/6bb7ed1ce77115c05016053bd7dfc1abc805a8aa))

- Update changelog [skip ci] (#129) ([1ac7283](https://github.com/aliyevaladddin/AladdinAI/commit/1ac728351fc61df741184bb99db7bba8c921a2b5))

- Update changelog [skip ci] (#131) ([3be06ac](https://github.com/aliyevaladddin/AladdinAI/commit/3be06acabf3f626a986de9e2b7b99c738c6d2ab3))

- Update changelog [skip ci] (#133) ([19e6b10](https://github.com/aliyevaladddin/AladdinAI/commit/19e6b10ee57522ae0a0778fa4c86634e912b6557))

- Update changelog [skip ci] (#134) ([9eadcd9](https://github.com/aliyevaladddin/AladdinAI/commit/9eadcd9485dbadb76977b96495d0293ccbe3c126))

- Update changelog [skip ci] (#135) ([816db98](https://github.com/aliyevaladddin/AladdinAI/commit/816db98c4c2d5a028e1837d9bfd272f1ea91ba79))

- Update changelog [skip ci] (#136) ([1829876](https://github.com/aliyevaladddin/AladdinAI/commit/18298761729b4d0fa6ecede522733984574d2a17))

- Update changelog [skip ci] (#137) ([6582883](https://github.com/aliyevaladddin/AladdinAI/commit/6582883d04389a09939183e3e429612c56c0869a))

- Update changelog [skip ci] (#138) ([df14875](https://github.com/aliyevaladddin/AladdinAI/commit/df14875a572cdc08fff5069c9c266f2532caef39))

- Update changelog [skip ci] (#139) ([cf3c409](https://github.com/aliyevaladddin/AladdinAI/commit/cf3c409fef88b71889be6f672aecbe4b57dfc5f7))

- Update changelog [skip ci] (#140) ([7020c00](https://github.com/aliyevaladddin/AladdinAI/commit/7020c002a70353b60627d6c1566b6b1e0f22f4dd))

- Update changelog [skip ci] ([093aa09](https://github.com/aliyevaladddin/AladdinAI/commit/093aa09f3d67dcfeea13855885381deb891c082c))

## [v2.1.3] - 2026-05-30
## [v2.1.2] - 2026-05-30

### Bug Fixes

- Verify GitHub webhook signature against raw body bytes ([81fc47d](https://github.com/aliyevaladddin/AladdinAI/commit/81fc47da61b602ba611836c680da5b3b26b1dccd))

- Improve security and error handling in webhook handler ([b4e03fb](https://github.com/aliyevaladddin/AladdinAI/commit/b4e03fb22819121288d2888bfc89ef9f7493daf3))


### Build

- Remove Node.js 18.x from CI build matrix ([f5c9ec9](https://github.com/aliyevaladddin/AladdinAI/commit/f5c9ec9d2f265b19ea2336839dd82264151793b7))

- Bump next from 16.2.4 to 16.2.6 in /frontend ([b67ace2](https://github.com/aliyevaladddin/AladdinAI/commit/b67ace2d497a1a8749403f45630ee8fdfbe95437))

- Bump python-jose from 3.3.0 to 3.4.0 in /backend ([ca732f4](https://github.com/aliyevaladddin/AladdinAI/commit/ca732f4e4caf5e86ac320d0737d67c3375301c74))

- Bump sqlalchemy from 2.0.35 to 2.0.50 ([975709c](https://github.com/aliyevaladddin/AladdinAI/commit/975709c021b003d7b3db12a0cdce0f39168e814c))

- Bump actions/checkout from 4 to 6 ([28896bc](https://github.com/aliyevaladddin/AladdinAI/commit/28896bc1162dc50d99020de82231a2ac2c56784b))

- Bump python-multipart from 0.0.12 to 0.0.29 ([5918974](https://github.com/aliyevaladddin/AladdinAI/commit/5918974b89f5124564ffa45c159551a9f1255346))

- Bump pyjwt from 2.8.0 to 2.13.0 ([3d15050](https://github.com/aliyevaladddin/AladdinAI/commit/3d15050e11a42f243249c02cdeb754fdad97a27a))

- Bump httpx from 0.27.0 to 0.28.1 ([b2453e4](https://github.com/aliyevaladddin/AladdinAI/commit/b2453e48cb390d1c3271269dcb9ecfb1009ca99b))

- Bump fastapi from 0.115.0 to 0.136.3 ([be0c206](https://github.com/aliyevaladddin/AladdinAI/commit/be0c206c41cfe7877ad9dcdd82cb82d3eaac3551))

- Bump actions/setup-node from 4 to 6 ([9c72654](https://github.com/aliyevaladddin/AladdinAI/commit/9c7265461cc663ec28f1ea091c80f33d203743ed))

- Bump actions/setup-python from 5 to 6 ([7aade93](https://github.com/aliyevaladddin/AladdinAI/commit/7aade93a345569849a118ca5d109865275255ed9))


### CI

- Update webpack workflow to install dependencies and build from frontend directory ([91d12c2](https://github.com/aliyevaladddin/AladdinAI/commit/91d12c2ba2423a3501d6754253a59ff94d519803))


### Documentation

- Update CONTRIBUTING.md with actual setup commands and conventional commits ([930ff1d](https://github.com/aliyevaladddin/AladdinAI/commit/930ff1d0bcdd646cf67cf2144579c4189d3eb3ee))

- Restore CODE_OF_CONDUCT link and fix backend venv setup ([ef1a6f8](https://github.com/aliyevaladddin/AladdinAI/commit/ef1a6f83528ef072b77651bddf1c8dff35348b6d))

- Fix CLI language and clarify changelog commit types ([24fe26a](https://github.com/aliyevaladddin/AladdinAI/commit/24fe26a117a95bf265b7417080920bc2b0ac432b))

- Add docstrings and comments for secret field changes ([162e45e](https://github.com/aliyevaladddin/AladdinAI/commit/162e45ec60e02a55204182e62f83273caf890d9f))

- Add Privacy Policy and Terms of Service for GitHub Marketplace ([e50079a](https://github.com/aliyevaladddin/AladdinAI/commit/e50079aaafca6ee8eb3a50d8a7196693d09c16ed))

- Add MongoDB for Startups badge and credits info ([a98bd94](https://github.com/aliyevaladddin/AladdinAI/commit/a98bd9498263179b858d2ef5e2bf87375e8acec1))


### Features

- Add Cloudflare Functions for GitHub bot webhook ([b2529a6](https://github.com/aliyevaladddin/AladdinAI/commit/b2529a6a9293717d86a97720880015dc02d97a65))

- Increase secret field lengths for GitHub App token format change ([c0b9181](https://github.com/aliyevaladddin/AladdinAI/commit/c0b9181ce14b324d3bd337c93b75f54eceb6ad24))

- Add descriptive metadata and parameter schemas to GitHub tools ([725eb32](https://github.com/aliyevaladddin/AladdinAI/commit/725eb32d51d97478d73e46ee0b8d123ab07b045c))


### Maintenance

- Remove test bot trigger file from repository ([67f88cb](https://github.com/aliyevaladddin/AladdinAI/commit/67f88cb477e2ef612bff67f5c4ec001400f78e89))

- Update changelog [skip ci] (#85) ([9d1a53f](https://github.com/aliyevaladddin/AladdinAI/commit/9d1a53fbe3f494e47b3495839eb206bf42d7fad7))

- Update changelog [skip ci] ([433bdee](https://github.com/aliyevaladddin/AladdinAI/commit/433bdee7fc2a06105e0dd2bff8408c47cf409b62))

- Update changelog [skip ci] (#87) ([36e9541](https://github.com/aliyevaladddin/AladdinAI/commit/36e954160b3389d39e4d58043a8253b98947ec6d))

- Update changelog [skip ci] (#91) ([1e6d9ee](https://github.com/aliyevaladddin/AladdinAI/commit/1e6d9ee9f5a7371d9f5e358f0646faaafa7a4169))

- Update changelog [skip ci] (#93) ([2856400](https://github.com/aliyevaladddin/AladdinAI/commit/2856400cc0598624f796388245d6baa5dba911da))

- Update changelog [skip ci] (#94) ([5c05e17](https://github.com/aliyevaladddin/AladdinAI/commit/5c05e1799058d3647bfcfaae63ee1275b743469e))

- Update changelog [skip ci] (#96) ([b2698bc](https://github.com/aliyevaladddin/AladdinAI/commit/b2698bc6544499c806dd9df42a0b345e716f698e))

- Update changelog [skip ci] (#98) ([0b7fcda](https://github.com/aliyevaladddin/AladdinAI/commit/0b7fcda063b0c5d285029dfb6492c319df767094))

- Update GitHub Actions versions across workflow configurations ([354d2a5](https://github.com/aliyevaladddin/AladdinAI/commit/354d2a57c538432b7d8b79d8518d53d8a8002f56))

- Update changelog [skip ci] (#111) ([9f1c833](https://github.com/aliyevaladddin/AladdinAI/commit/9f1c8334a799dd604e638bbe2465e1824c7aa4c2))

- Update changelog [skip ci] (#112) ([4316e2a](https://github.com/aliyevaladddin/AladdinAI/commit/4316e2a71980499c280a180361cf61e93a50f653))

- Update changelog [skip ci] (#113) ([1b7b2a2](https://github.com/aliyevaladddin/AladdinAI/commit/1b7b2a2f046b254050b4ab221a8b47111e046d95))

- Update changelog [skip ci] (#114) ([9c6c94a](https://github.com/aliyevaladddin/AladdinAI/commit/9c6c94ad5b25799bad4c54b98e8cbd870fb84851))

- Update changelog [skip ci] (#115) ([e995efe](https://github.com/aliyevaladddin/AladdinAI/commit/e995efe19315f98258258f74b9b7fc425db65cad))

- Update changelog [skip ci] (#116) ([fe62199](https://github.com/aliyevaladddin/AladdinAI/commit/fe621993694388b82fc2b6745257e7327d59c7a8))

- Update changelog [skip ci] ([2a0b531](https://github.com/aliyevaladddin/AladdinAI/commit/2a0b531bc413dd2de239308ed6f5ae4cf24de188))

- Update changelog [skip ci] (#117) ([9afe10a](https://github.com/aliyevaladddin/AladdinAI/commit/9afe10a360eef4bf0c5688fafeaca62f85693f2f))

- Update changelog [skip ci] (#119) ([9d23198](https://github.com/aliyevaladddin/AladdinAI/commit/9d2319865d46917bb3f47b27c974e15221391867))

- Update changelog [skip ci] (#122) ([dfbc1fc](https://github.com/aliyevaladddin/AladdinAI/commit/dfbc1fc1bf055ae15a668397f8f3048a484cdf91))


### Refactor

- Update Cloudflare Functions env variable names ([26b03a9](https://github.com/aliyevaladddin/AladdinAI/commit/26b03a9f25c8a8a5e26de375815f9227255b3031))

## [v2.1.1] - 2026-05-28

### Bug Fixes

- Fix readme ([48bafa7](https://github.com/aliyevaladddin/AladdinAI/commit/48bafa781e9e98e7fa51f1966c3358c0bfcfad27))

- Replace git-cliff-action with direct binary ([1e139f5](https://github.com/aliyevaladddin/AladdinAI/commit/1e139f5de15b69616975e917c9ae1e71773085ce))

- Add write permissions to changelog workflow ([ee00a5d](https://github.com/aliyevaladddin/AladdinAI/commit/ee00a5d6c5f3a9d3902b09c26a4993b7a85be83b))

- Add validation for GitHub tools parameters per code review feedback ([dd29f23](https://github.com/aliyevaladddin/AladdinAI/commit/dd29f23e07db854bf2db68947bc8f4936e86b663))

- Improve error message for empty installation_id ([dd865b0](https://github.com/aliyevaladddin/AladdinAI/commit/dd865b06893576332676173526d76f74adf8cd87))

- Add token validation and improve repo format regex per code review ([c8f900f](https://github.com/aliyevaladddin/AladdinAI/commit/c8f900fa98eb4c613e801663e1e10d056de9b8c6))

- Move imports inside function to resolve ruff E402 ([e96947e](https://github.com/aliyevaladddin/AladdinAI/commit/e96947ebd255b0956b8decb47d57282730d3c9fe))

- Add input validation and logging per code review suggestions ([fe81e61](https://github.com/aliyevaladddin/AladdinAI/commit/fe81e61c10f25ee474b1daa7a8cb020526cd3a11))

- Add logging for unhandled event types ([b716fb5](https://github.com/aliyevaladddin/AladdinAI/commit/b716fb5b3b162e0e0cb6e1a22a9678f3aa138c7e))

- Add explicit HTTP error handling with logging ([faf2751](https://github.com/aliyevaladddin/AladdinAI/commit/faf2751d189c6ff129198540a9f95ee6bf922524))

- Add error handling and logging to AladdinAI bot ([90a9ecd](https://github.com/aliyevaladddin/AladdinAI/commit/90a9ecdf592e4f17e4761329bed0788c8799ba4c))

- Remove unused settings import in autonomous_bot_scheduler ([797158e](https://github.com/aliyevaladddin/AladdinAI/commit/797158ea65b89861243ed4af2f14fd51333fb811))

- Update changelog workflow to use AladdinAI bot and create PRs ([a595815](https://github.com/aliyevaladddin/AladdinAI/commit/a595815e90da1d1d10d06ee0f239312926f2bb75))

- Correct indentation and add owner parameter to _get_user_context ([b496ed9](https://github.com/aliyevaladddin/AladdinAI/commit/b496ed975b7289ce218795a7cc710f6bfa899945))


### Dependencies

- Bump alembic from 1.13.0 to 1.18.4 ([5a75fa5](https://github.com/aliyevaladddin/AladdinAI/commit/5a75fa5e650cd139ca8b8d6485c5e6e32f4bf7b0))

- Bump asyncssh from 2.18.0 to 2.23.0 ([a0b16be](https://github.com/aliyevaladddin/AladdinAI/commit/a0b16be7434e7098d2894bb10accc0c86afef2be))

- Bump actions/checkout from 4 to 6 ([61727c7](https://github.com/aliyevaladddin/AladdinAI/commit/61727c776962f225e04a47afa648d813f0ce12ba))

- Bump docker/build-push-action from 5 to 7 ([54a90e5](https://github.com/aliyevaladddin/AladdinAI/commit/54a90e5b0f4557094b9dc5971637d943b5a18e51))

- Bump docker/setup-buildx-action from 3 to 4 ([e6c532c](https://github.com/aliyevaladddin/AladdinAI/commit/e6c532c2ddf1d26ab1f9fc3e6583c0315c1db3c4))

- Bump docker/login-action from 3 to 4 ([547ec98](https://github.com/aliyevaladddin/AladdinAI/commit/547ec987706605de62b4c606c7bf5fb35b10ebfc))

- Update certifi requirement from >=2024.2.2 to >=2026.5.20 ([9959cd5](https://github.com/aliyevaladddin/AladdinAI/commit/9959cd5d6f2864d0af68356ae1ab9fafbb3d4567))

- Bump actions/setup-python from 5 to 6 ([fec2e60](https://github.com/aliyevaladddin/AladdinAI/commit/fec2e60d0e220cd3d207759ca74b0fcdf24ca9de))

- Bump pydantic-settings from 2.5.0 to 2.14.1 ([8cb52a6](https://github.com/aliyevaladddin/AladdinAI/commit/8cb52a6d799bfdb59ea20da0fd46a5f333897ed4))

- Bump asyncpg from 0.30.0 to 0.31.0 ([55b049d](https://github.com/aliyevaladddin/AladdinAI/commit/55b049dcc78c2fb31a8afeb9f2d7dd530a321554))

- Bump sqlalchemy from 2.0.35 to 2.0.50 ([9255392](https://github.com/aliyevaladddin/AladdinAI/commit/9255392201f054958b7966d9879132cfc704a971))

- Bump pyyaml from 6.0.2 to 6.0.3 ([35ccfc0](https://github.com/aliyevaladddin/AladdinAI/commit/35ccfc024053aa2c9a7e163543a99abebc5a411b))

- Bump croniter from 2.0.5 to 6.2.2 ([5b971db](https://github.com/aliyevaladddin/AladdinAI/commit/5b971db22a9c54c07cecb7905ab0100b1c83893e))

- Bump uvicorn from 0.30.0 to 0.48.0 ([795c47c](https://github.com/aliyevaladddin/AladdinAI/commit/795c47cbbf701b26200614689d75fd8593c347f9))

- Bump motor from 3.6.0 to 3.7.1 ([f4df4a4](https://github.com/aliyevaladddin/AladdinAI/commit/f4df4a479f96be9bfaeac98785dc5b918c5158cd))


### Documentation

- Rewrite Quick start around npx aladdin-ai ([d7bae59](https://github.com/aliyevaladddin/AladdinAI/commit/d7bae59d7168cd02aa62782b72dc40f06e31b5a2))

- Add project structure documentation for backend modules and update environment configuration reference. ([bb9827c](https://github.com/aliyevaladddin/AladdinAI/commit/bb9827cc5bc5f4dd7e8e16932011afde232d31df))

- Redesign and update README with improved project branding and documentation structure ([2ad389a](https://github.com/aliyevaladddin/AladdinAI/commit/2ad389a6cc9bb2f7df6805694cc3d096df087930))


### Features

- Implement Operational Control Center theme system and UI shell ([be6798d](https://github.com/aliyevaladddin/AladdinAI/commit/be6798d7e853cbe858e22f2026f7f439ad630897))

- Implement control center, theme switcher and terminal provider ([172ee05](https://github.com/aliyevaladddin/AladdinAI/commit/172ee05e3841f17eeada258ec870e7eed70fad56))

- Implement modular plug-and-play terminal system ([601c6b9](https://github.com/aliyevaladddin/AladdinAI/commit/601c6b98d71ad28d227d8a3a0de92917b2ebeea9))

- Terminal UI fixes, router resolver, and encryption updates ([9601ee1](https://github.com/aliyevaladddin/AladdinAI/commit/9601ee1a6e08ca4accc2712316c18546c6c7d64b))

- Initialize session tracking file and configure Claude proxy model routes ([2cdbbb3](https://github.com/aliyevaladddin/AladdinAI/commit/2cdbbb3d38e656891e9a0bfefaef94df94bc8c15))

- Refactor terminal system with multi-session support and configure Docker-in-Docker for local development. ([43d71ea](https://github.com/aliyevaladddin/AladdinAI/commit/43d71ea2486c96f8b574253b99c267dee6994c7d))

- Implement Wetty terminal adapter with SSH support and configurable Traefik routing ([4759618](https://github.com/aliyevaladddin/AladdinAI/commit/4759618f766d38e7c5d6fa8f468eda372cb4451c))

- Refactor terminal adapters, introduce registry, lifecycle management, and setup scripts ([fc2e6ed](https://github.com/aliyevaladddin/AladdinAI/commit/fc2e6ed61c4dff21344e01f4fb114684e9684cf2))

- Add project feedback links to README and setup script, and ignore blog architecture documentation ([0e838f9](https://github.com/aliyevaladddin/AladdinAI/commit/0e838f9ecfe65db63e0f96ca033882b32a8ae688))

- Add CI, changelog, render deploy ([7e02b0c](https://github.com/aliyevaladddin/AladdinAI/commit/7e02b0cc22cec60d017c0f1e5bce6a5e8bedc85b))

- Implement multi-agent orchestration framework and add suite of specialized agents with automated workflow triggers ([cf4e730](https://github.com/aliyevaladddin/AladdinAI/commit/cf4e730ec3419bbc6468861945dae461d0ba7bb8))

- Add documentation for demo agents and clean up proactive reminder service imports ([27d3ba0](https://github.com/aliyevaladddin/AladdinAI/commit/27d3ba089fb441c83501bdc0720bbd57f1c2e9ee))

- Refine code review agent prompt and add bot commit workflow demo ([51d41f2](https://github.com/aliyevaladddin/AladdinAI/commit/51d41f2677af6f68b98af578c1dc690924224e97))

- Add bot-commits workflow for GitHub App demo ([2e8c02a](https://github.com/aliyevaladddin/AladdinAI/commit/2e8c02a113cd7cf29284c65ab15306706f7bf0d2))

- Add auto-merge for bot PRs ([3eaf4a5](https://github.com/aliyevaladddin/AladdinAI/commit/3eaf4a5f5687bdb31fcf98a527c82fd63e32f853))

- Integrate GitHub App bots into backend with tools and auth service ([179c96d](https://github.com/aliyevaladddin/AladdinAI/commit/179c96d0672574498fa3a0440f529f639482ec95))

- Add GitHub webhook handler with event processing ([2ec949a](https://github.com/aliyevaladddin/AladdinAI/commit/2ec949ac511138864021818b0b2d58def94a2614))

- Add AladdinAI bot with reactions and Telegram notifications ([60ff6d0](https://github.com/aliyevaladddin/AladdinAI/commit/60ff6d09468e6dc9170e585ae41750e75c52b725))

- Add issue milestone celebrations, mention handling, random PR roasts, and automated reviewer assignment ([f5d9cef](https://github.com/aliyevaladddin/AladdinAI/commit/f5d9cefc8eee821c8e9ae9f7da32caa08beab972))

- Add autonomous AI personality and advanced features to AladdinAI bot ([baf947d](https://github.com/aliyevaladddin/AladdinAI/commit/baf947d79d0ba0c0bc46c9b4857e8732f2311cf6))

- Add autonomous bot scheduler with morning standup and Friday recap ([ef93dbf](https://github.com/aliyevaladddin/AladdinAI/commit/ef93dbf29fbc6d50409c409fd1fa7cdba2646a42))

- Add automatic issue assignment functionality for the aladdinai bot ([03058f8](https://github.com/aliyevaladddin/AladdinAI/commit/03058f84ec064e800c9f58e169b9786336e54d1c))

- Add user interaction tracking with personalized bot responses ([ee01a73](https://github.com/aliyevaladddin/AladdinAI/commit/ee01a734f4467732881779e4e62eaa4ca34ea7ee))

- Add repository owner recognition with special treatment ([03f0540](https://github.com/aliyevaladddin/AladdinAI/commit/03f05402f23b6a61ff06abc84f43a8bdba57e202))


### Maintenance

- Add proxy configuration ([bd13d5b](https://github.com/aliyevaladddin/AladdinAI/commit/bd13d5b64f25ebb49ad568001e89ed8c340b0eb9))

- Add .gitignore ([dc3979b](https://github.com/aliyevaladddin/AladdinAI/commit/dc3979b58a601c1ade84e36ef0b53d105a871d3e))

- Remove package-lock.json from repository ([066ad7f](https://github.com/aliyevaladddin/AladdinAI/commit/066ad7fdf70b31e262aa47eba455ff0a51d43b71))

- Update changelog [skip ci] ([e0cf1b3](https://github.com/aliyevaladddin/AladdinAI/commit/e0cf1b3de7ade6ac89572e58d44d2c2cc5e2ea62))

- Cleanup imports and update gitignore ([a418405](https://github.com/aliyevaladddin/AladdinAI/commit/a41840535c672b1f20a6acda4e16e25f7f2c645a))

- Update changelog [skip ci] ([8329ad1](https://github.com/aliyevaladddin/AladdinAI/commit/8329ad1ae227e3a28b6869cdd111b4a3b374899b))

- Remove docker-compose version and add .env setup step to CI pipeline ([3fa317d](https://github.com/aliyevaladddin/AladdinAI/commit/3fa317dc9d1ff95b194e26dfe435cd0b139a6eac))

- Update changelog [skip ci] ([c3aad74](https://github.com/aliyevaladddin/AladdinAI/commit/c3aad74f9bbe05d62120eb46a56759351ce8b69f))

- Update bot activity log ([4fe5dee](https://github.com/aliyevaladddin/AladdinAI/commit/4fe5dee0f2e142c06b0d42e1ed2b1282eadb6126))

- Update nvidia bot activity log ([1fdef50](https://github.com/aliyevaladddin/AladdinAI/commit/1fdef504fc01e55caa9f14df02283a9b92ee7ad7))

- Update bot activity log ([a7522cb](https://github.com/aliyevaladddin/AladdinAI/commit/a7522cbc0e6451dcb28caabdb94878f565db11b6))

- Update nvidia bot activity log ([4ce9132](https://github.com/aliyevaladddin/AladdinAI/commit/4ce91323f27aaab4da724d1aec97ee96b85175b0))

- Update changelog [skip ci] ([ed6af6c](https://github.com/aliyevaladddin/AladdinAI/commit/ed6af6c1d04c65c77f7ef87bc91a4255152ee3da))

- Update changelog [skip ci] ([861da86](https://github.com/aliyevaladddin/AladdinAI/commit/861da868d9fdd18aca87eb66160ca97205cb944b))

- Update bot activity log ([806b965](https://github.com/aliyevaladddin/AladdinAI/commit/806b965f160fd6c4606664a1fd112fd92f2b14d2))

- Update nvidia bot activity log ([71a4b2c](https://github.com/aliyevaladddin/AladdinAI/commit/71a4b2cad20aec23db1ea80aaafbc8dcb4c523d8))

- Update changelog [skip ci] ([6189b5e](https://github.com/aliyevaladddin/AladdinAI/commit/6189b5efb540aaa264b7deb5fb1d0c2367c991c9))

- Update changelog [skip ci] ([96698bd](https://github.com/aliyevaladddin/AladdinAI/commit/96698bd5374a4f3c89f920212e2ee646bbc37692))

- Update changelog [skip ci] (#69) ([6c0b9e0](https://github.com/aliyevaladddin/AladdinAI/commit/6c0b9e035cedb96928705efe1d51ad43ef514f61))

- Update changelog [skip ci] (#71) ([cb773fb](https://github.com/aliyevaladddin/AladdinAI/commit/cb773fbc351c33be1ed385ce151cf692b55743a0))

- Update changelog [skip ci] (#78) ([c471fe0](https://github.com/aliyevaladddin/AladdinAI/commit/c471fe0976cc24253a5669b327860e0371948688))

- Update changelog [skip ci] (#83) ([385d0c9](https://github.com/aliyevaladddin/AladdinAI/commit/385d0c93a36e3c60c897620d635ef87bce0184d9))


### Refactor

- Migrate terminal routing to Traefik file-provider and unify session management ([03445b0](https://github.com/aliyevaladddin/AladdinAI/commit/03445b04a8973a77815c7a25f6d6665609340dc3))

- Export terminal adapters in init, fix database event import, and remove unused variable in dashboard router ([7c16864](https://github.com/aliyevaladddin/AladdinAI/commit/7c1686494fa0031a3a99621cda1728315e52fd71))

- Migrate code review agent to use NIM and update generation parameters ([66ca8b0](https://github.com/aliyevaladddin/AladdinAI/commit/66ca8b0d7c679745b06dedf4845f38f842a71fe0))

- Update code review agent to use NVIDIA NIM, add file filtering, structured review summaries, and migrate to GitHub App authentication ([67a43f2](https://github.com/aliyevaladddin/AladdinAI/commit/67a43f22d1d145c5efb7a57e9c44650388c887c0))


### Style

- Update README CI and deployment badges to use consistent shield styles ([5d308d5](https://github.com/aliyevaladddin/AladdinAI/commit/5d308d5135631101741834f5b87a9f78351d487b))


### Testing

- Add file with intentional issues to trigger code review bot ([e2cc649](https://github.com/aliyevaladddin/AladdinAI/commit/e2cc649ba85d4cdcc45920778a0ad532b18f9ad8))

- Trigger webhook for AladdinAI bot ([690d247](https://github.com/aliyevaladddin/AladdinAI/commit/690d247e3d84c9ab6d6e5584b82ddafa159a012d))

## [v2.0.1] - 2026-05-18

### Maintenance

- Rename env template to prevent npm dotfile exclusion and add .npmignore file ([35ed81b](https://github.com/aliyevaladddin/AladdinAI/commit/35ed81b47c01d863a774f8d274cf762448856281))

## [v2.0.0] - 2026-05-18

### Bug Fixes

- Prepend venv activation to remote shell commands and restyle terminal container for full-screen layout ([a1f6585](https://github.com/aliyevaladddin/AladdinAI/commit/a1f65850cebcb03c6ec2ef1fd02f239f01690e7f))

- Resolve nested buttons in chat and de-duplicate model lists in agents/gates/safety panels ([84d2229](https://github.com/aliyevaladddin/AladdinAI/commit/84d2229947846787439c2c8f9de16c99a2881a05))

- PII phases, shared visibility for user facts, NIM timeout ([30f806b](https://github.com/aliyevaladddin/AladdinAI/commit/30f806ba8e6917f9178f7af5a5882fa235785a7f))

- Add exception handling to migration for password_encrypted column in vm_connections ([89ce305](https://github.com/aliyevaladddin/AladdinAI/commit/89ce3053ffb9bda017b0bc67c7daa483ded9e329))

- Verify signatures on incoming channel webhooks ([b1a5549](https://github.com/aliyevaladddin/AladdinAI/commit/b1a554947e495366159cea0063232c8c507adfa7))

- Block SSRF via user-configured waha_url (#23) ([5f04503](https://github.com/aliyevaladddin/AladdinAI/commit/5f045033d75f2a5760c3ddc892b90dc8558ac6ee))

- Robustness pass on email sync, telegram poller, orchestrator (#24) ([176ea27](https://github.com/aliyevaladddin/AladdinAI/commit/176ea2741483281971a28270c1ba1e9798384f90))

- Add contact_id to local Activity interface in crm/[id]/page ([264168c](https://github.com/aliyevaladddin/AladdinAI/commit/264168c8c3957deb9eb848f951d6a9f336b43d59))


### Documentation

- Comprehensive documentation overhaul and CLI refactor ([09228c2](https://github.com/aliyevaladddin/AladdinAI/commit/09228c2a64ae04059c7405e9065491b8344fb421))

- Revamp README and ARCHITECTURE for partner outreach; polish login UI ([26d40a1](https://github.com/aliyevaladddin/AladdinAI/commit/26d40a1573196ace335712fb3d2901e828d53cc8))


### Features

- Stabilize terminal lifecycle, fix BentoML deploy & enhance network diagnostics ([15fdf94](https://github.com/aliyevaladddin/AladdinAI/commit/15fdf949ad89fb8c1abb1a6ac49c04def8c06175))

- Feat: redesign comms/crm/agents pages and add VM password migration
  - Replace mock cyberpunk UI on /comms, /crm, /agents with real API-driven views
  - Match design system used by /channels, /deals (shadcn Button, border-border, muted-foreground)
  - /comms now shows connected messaging channels and email accounts with Test/Sync
  - /crm becomes Contacts list with create form, search, tags, source
  - /agents lists real agents with Start/Stop/Delete and provider join
  - Add Alembic migration adding password_encrypted column to vm_connections ([9046a26](https://github.com/aliyevaladddin/AladdinAI/commit/9046a26e2b3159b6589b08b747f05295601ca568))

- Replace alert() with sonner toasts across dashboard ([11967e5](https://github.com/aliyevaladddin/AladdinAI/commit/11967e5ef6c628a187a10a65046290ed12a1efed))

- Replace alert() with sonner toasts in dashboard pages ([59c8986](https://github.com/aliyevaladddin/AladdinAI/commit/59c89860125018bbf02f5c09f9e4d5a941ebeec0))

- Add BentoML deployment schema and implement unified general chat mode in UI ([c1764bd](https://github.com/aliyevaladddin/AladdinAI/commit/c1764bd07b49c615fdb0189b39b7d6b4209f064e))

- Implement multi-agent delegation system and tool-calling infrastructure ([a6487fc](https://github.com/aliyevaladddin/AladdinAI/commit/a6487fc49c16fefa10f0323974e579ffbd9cc821))

- Implement gate decision logging and moderation gates ([f8c3f21](https://github.com/aliyevaladddin/AladdinAI/commit/f8c3f21fb1762ba750a8a7a35bfc5184ab8f4fef))

- Per-message extraction, shared-context injection, safety UI, recommended models ([e9d529a](https://github.com/aliyevaladddin/AladdinAI/commit/e9d529a55eb664d2117dd4a21d3ba6e03ced0d3c))

- Add user profile endpoint ([b3d9dba](https://github.com/aliyevaladddin/AladdinAI/commit/b3d9dbaced23a9a05819b74e110f1c428ffaacdf))

- UI panel to list/search/add/delete agent memories ([bd08ad8](https://github.com/aliyevaladddin/AladdinAI/commit/bd08ad8f34311cca066f4dd665c4485ed944a5ae))

- Cron-scheduled agent tasks via APScheduler ([b7192dc](https://github.com/aliyevaladddin/AladdinAI/commit/b7192dc45f20f4dc7f1ff1cfa1573938b5483af3))

- Add automated CLI publishing workflow with version verification ([bf78e3f](https://github.com/aliyevaladddin/AladdinAI/commit/bf78e3fc1ce4f4a77bfa62ff50dfbcf53b931a5f))

- Implement sovereign WhatsApp integration via WAHA with in-dashboard QR code ([8f1b0f8](https://github.com/aliyevaladddin/AladdinAI/commit/8f1b0f869dbbc385143455daef3343ad755b1d51))

- Complete sovereign messaging setup (TG/WA) and security hardening ([a0fbc3b](https://github.com/aliyevaladddin/AladdinAI/commit/a0fbc3bb55d40fef9b4432af06aaf0d6b257f728))

- Add multimodal support for telegram attachments and implement image handling in the orchestrator and agent runner. ([680dd03](https://github.com/aliyevaladddin/AladdinAI/commit/680dd03b452751b5f28d8e2a13d27984871b7df4))

- Implement scalable image tools and ToolContext.extra channel logic ([6164439](https://github.com/aliyevaladddin/AladdinAI/commit/616443975602e3fd0e801057efff9e44697fac4a))

- Implement AI-driven reply suggestions, add search router, and introduce CLI lifecycle and doctor commands. ([7f6a32d](https://github.com/aliyevaladddin/AladdinAI/commit/7f6a32d46fc7a34c9d36acc24b4c4dbcf9f10c8f))

- Docker-first install via GHCR images ([ec42f90](https://github.com/aliyevaladddin/AladdinAI/commit/ec42f90b5bd78dc9900a8ea8b6bab9b9d44faf12))


### Maintenance

- Update and populate ([d3bfbdc](https://github.com/aliyevaladddin/AladdinAI/commit/d3bfbdc936b43ffafd17a05a26940f7ad1db9694))

- Ignore aider-related configuration and history files in .gitignore ([bb69d56](https://github.com/aliyevaladddin/AladdinAI/commit/bb69d56d2105d9ab760cf7f2911e3a18d40eea19))

- Add aider configuration files to .gitignore ([6180ecf](https://github.com/aliyevaladddin/AladdinAI/commit/6180ecfc8995062712ece5665c8b86cd39cd7e7d))

- Update .gitignore, environment configuration, and parameterize docker-compose database credentials ([409735d](https://github.com/aliyevaladddin/AladdinAI/commit/409735d26cf08bcbb8cf04425662fafd51e07d36))

- Add pgdata/ to gitignore to exclude local PostgreSQL data volumes ([43e6a7c](https://github.com/aliyevaladddin/AladdinAI/commit/43e6a7c66aded1290eaabe89b519dee8937862b1))


### Refactor

- Update BentoML deployment logic and add repository documentation files ([3c0ccbc](https://github.com/aliyevaladddin/AladdinAI/commit/3c0ccbc1e3570d82b01516664f0dff2861b1a41a))

## [v1.2.0] - 2026-04-30

### Bug Fixes

- Improve CLI download robustness, update cross-platform open command, and bump package versions to 1.2.0 ([5900eb3](https://github.com/aliyevaladddin/AladdinAI/commit/5900eb3883ecd9f19cf04c6e60eeb461bff74017))

## [v1.1.9] - 2026-04-30

### Bug Fixes

- Resolve Windows installation path opening issue and bump version to 1.1.8 ([4e2b3a5](https://github.com/aliyevaladddin/AladdinAI/commit/4e2b3a571f3aabd88d719eab28d32aaf901ac92c))

## [v1.1.7] - 2026-04-30

### Features

- Add publish-cli workflow to automate npm releases ([2bbcc95](https://github.com/aliyevaladddin/AladdinAI/commit/2bbcc95ca0cf3ba2966c0bb1eb1e5e2fa1b26601))


### Maintenance

- Bump cli and frontend package versions to 1.1.7 ([50fe45c](https://github.com/aliyevaladddin/AladdinAI/commit/50fe45c32366931d04dae27efe62880654ed5f22))

## [v1.1.6] - 2026-04-30

### Bug Fixes

- Clean up workflows and prepare for final release v1.1.6 ([49032d8](https://github.com/aliyevaladddin/AladdinAI/commit/49032d839e58a5f1975670912c5e781cf143ba46))

## [v1.1.5] - 2026-04-30

### CI

- Add ubuntu support and consolidate electron build and artifact collection process ([ef59008](https://github.com/aliyevaladddin/AladdinAI/commit/ef59008977bd7d10859d440b155d5f8892babe2b))

## [v1.1.4] - 2026-04-30

### Maintenance

- Add write permissions for contents to desktop build workflow ([192bd16](https://github.com/aliyevaladddin/AladdinAI/commit/192bd165a9375f34acb67fbaf2f1a2d1cd7bba8b))

## [v1.1.3] - 2026-04-30

### Maintenance

- Add metadata to package.json for electron-builder publishing ([80cdff8](https://github.com/aliyevaladddin/AladdinAI/commit/80cdff87e369876b91b843866473b9a54263c506))

## [v1.1.2] - 2026-04-30

### Bug Fixes

- Final build cleanup - remove deprecated next export command ([ea653ea](https://github.com/aliyevaladddin/AladdinAI/commit/ea653ea5c5ffeaf7db00f944d4f9e17538285b28))

## [v1.1.1] - 2026-04-30

### Bug Fixes

- Final build hardening (TS generics, null token support, CSS native patterns) ([8802c79](https://github.com/aliyevaladddin/AladdinAI/commit/8802c7908e16705aa44646a5d5f192d17bae4382))

## [v1.1.0] - 2026-04-30

### Bug Fixes

- Add token management methods to api client ([63f0102](https://github.com/aliyevaladddin/AladdinAI/commit/63f0102674dadb3fae5ecb0f351707030362290a))

## [v1.0.9] - 2026-04-30

### Bug Fixes

- Make API body optional for POST/PUT and support all CRUD methods ([2864641](https://github.com/aliyevaladddin/AladdinAI/commit/28646413449d843c0f751095f7092b505f2da759))

## [v1.0.8] - 2026-04-30

### Features

- Implement full CRUD support in api utility by adding post, put, and delete methods ([797f7cd](https://github.com/aliyevaladddin/AladdinAI/commit/797f7cd83db50577a63d1eb8f4ec1076c483d032))

## [v1.0.7] - 2026-04-30

### Bug Fixes

- Add generic support to api client to resolve TS errors ([7600cad](https://github.com/aliyevaladddin/AladdinAI/commit/7600cad0334bac17d99c06ebc9d53f4f450ac446))

## [v1.0.6] - 2026-04-30

### Bug Fixes

- Move selection styles to native CSS for Tailwind v4 compatibility ([28f6123](https://github.com/aliyevaladddin/AladdinAI/commit/28f61233448cf10dc3c3a6c9be55d40dd1a994b0))

## [v1.0.5] - 2026-04-30

### Ix

- Final resolve for Tailwind v4 CSS build errors ([5e60636](https://github.com/aliyevaladddin/AladdinAI/commit/5e60636ebf0411e0a967b51b680801417f61db30))

## [v1.0.4] - 2026-04-30

### Bug Fixes

- Resolve Tailwind v4 utility errors and rename Sidebar to SovereignSidebar ([157d625](https://github.com/aliyevaladddin/AladdinAI/commit/157d6252ed8f0da7685f314665334e272a71d9be))

## [v1.0.3] - 2026-04-30

### Features

- Export api compatibility object and update CI to use npm install ([90bc654](https://github.com/aliyevaladddin/AladdinAI/commit/90bc65450b2aaa981b2368622ca71640b9764736))

## [v1.0.2] - 2026-04-30

### Bug Fixes

- Use rcf-cli audit command instead of scan ([38d4cae](https://github.com/aliyevaladddin/AladdinAI/commit/38d4cae1b347069eba708281c046746aa439fc5c))

- Add publishConfig for npm ([9604a77](https://github.com/aliyevaladddin/AladdinAI/commit/9604a777a0c3891afbfdca229e27fdf0bbf05c3b))

- Use correct npm scope @aladdinaliyev ([c9200d9](https://github.com/aliyevaladddin/AladdinAI/commit/c9200d9c68058707af24386d101b75228e0f5b81))


### CI

- Allow npm publish from feature branch for testing ([65cca02](https://github.com/aliyevaladddin/AladdinAI/commit/65cca025f9070c80f2022b10019e0b09e98f2c50))

- Trigger npm publish workflow on changes to its own configuration file ([4fc4864](https://github.com/aliyevaladddin/AladdinAI/commit/4fc4864526d1838747ae69745f56fdf12f782be9))

- Sync npm publish config with working rcf-protocol setup ([74d9712](https://github.com/aliyevaladddin/AladdinAI/commit/74d9712629e0af0b50705433dc84647f6ab1b2b8))

- Update npm publish workflow to target typescript SDK and add release trigger ([ffada2c](https://github.com/aliyevaladddin/AladdinAI/commit/ffada2cf71f45f465086c8af94ec589e8743fe0f))

- Switch RCF audit to npm rcf-protocol ([ff2613f](https://github.com/aliyevaladddin/AladdinAI/commit/ff2613fb4a0dd649acaab58dcc66644b6872e931))


### Documentation

- Update README with project badges, feature list, and contribution guidelines, and finalize LICENSE copyright notice ([a220565](https://github.com/aliyevaladddin/AladdinAI/commit/a220565da458090f0c6190a1190f05e04459bfb9))

- Update quick start command and add native desktop app benefits to README ([4f3e898](https://github.com/aliyevaladddin/AladdinAI/commit/4f3e898dad2c005a64e2e17270d5ec618b44b1eb))


### Features

- Project structure initialization (FastAPI backend and Next.js frontend) ([319d75d](https://github.com/aliyevaladddin/AladdinAI/commit/319d75d3c04d5c17c9975092dba3de58d8ba3fea))

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
- Add asyncssh==2.18.0 to requirements.txt ([6345200](https://github.com/aliyevaladddin/AladdinAI/commit/634520022691b1945f0467bd7c6ebfe67ff57f8e))

- Add dynamic model loading, persistent chat sessions, and visual router config ([4b9fea9](https://github.com/aliyevaladddin/AladdinAI/commit/4b9fea9ea8d9433097f508e322b8235d74f3d551))

- Implement RCF Protocol (Restricted Correlation) and Outgoing Webhooks ([e3fcadd](https://github.com/aliyevaladddin/AladdinAI/commit/e3fcadd3ca702def7474111c0125333f58b4cdf1))

- Integrate Electron for desktop support and upgrade aladdin-ai CLI installer ([d9641ea](https://github.com/aliyevaladddin/AladdinAI/commit/d9641ea3de39d5c79f2ac5055683ef855fabb655))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([708f214](https://github.com/aliyevaladddin/AladdinAI/commit/708f2146d1a8487b826281f9fc342ce494888c42))

- Initialize CLI package with documentation, licensing, and CI/CD publishing pipeline ([987b8f8](https://github.com/aliyevaladddin/AladdinAI/commit/987b8f8918cb45aaf6859f69b89036c20aee7754))

- Rename package to aladdin-ai for clean npx command ([700cdde](https://github.com/aliyevaladddin/AladdinAI/commit/700cddea6f56c9abb5df2480fd3d16ce0bc8e004))

- Complete SOVEREIGN_CMD transformation (UI, Backend Stats, Desktop Build) ([2b3fd0a](https://github.com/aliyevaladddin/AladdinAI/commit/2b3fd0adbee4e281bd0a66161566d3a05daef73f))


### Maintenance

- Upgrade RCF Protocol to v2.0.3 across the platform ([20fcf22](https://github.com/aliyevaladddin/AladdinAI/commit/20fcf22fe4b84ead039c4a40300fe6ab74450328))

- Move CLI to scoped package @aliyevaladddin/aladdin-ai ([1d46475](https://github.com/aliyevaladddin/AladdinAI/commit/1d46475ee253a0e962fa6234bc4d8033d0e802c4))

- Update npm authentication method in publish workflow to use npm config set ([3a4271a](https://github.com/aliyevaladddin/AladdinAI/commit/3a4271a504618f5670e2a05a48690cfcf5160ccc))

- Add .npmrc configuration for Aurora Access registry authentication ([48f18c4](https://github.com/aliyevaladddin/AladdinAI/commit/48f18c4cf8a5c1a4e0b0b991290b28b5e9ce833b))

- Update npm publish workflow to use clean install and cache dependencies ([df5b7f0](https://github.com/aliyevaladddin/AladdinAI/commit/df5b7f059c372f6a6b68c6eb445449c3ba9fc5ba))

- Update npm publish workflow to include job definition and required permissions ([a3e9ee5](https://github.com/aliyevaladddin/AladdinAI/commit/a3e9ee585f00e91a35b387f98b0f226dd0af5eaa))

- Update registry configuration to GitHub Packages and trigger workflow on cli directory changes ([746a135](https://github.com/aliyevaladddin/AladdinAI/commit/746a135a6d4d93070bebaa6bdf94a72d2a0156b5))


### Hore

- Publish under @auroraaccess organization ([d459cb9](https://github.com/aliyevaladddin/AladdinAI/commit/d459cb9af1c4b45ec0c677dce3824cd03c7d834d))

<!-- Generated by git-cliff -->
