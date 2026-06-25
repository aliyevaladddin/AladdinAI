// NOTICE: This file is protected under RCF-PL
// Locate the AladdinAI project root from the current working directory.
//
// Strategy: walk up from cwd looking for docker-compose.yml AND backend/ dir.
// If not found, return null — caller decides whether to error out.

import fs from 'fs-extra';
import path from 'path';

// [RCF:PROTECTED]
export function findProjectRoot(start = process.cwd()) {
  let dir = path.resolve(start);
  const { root } = path.parse(dir);
  while (true) {
    const compose = path.join(dir, 'docker-compose.yml');
    const backend = path.join(dir, 'backend');
    if (fs.existsSync(compose) && fs.existsSync(backend)) return dir;
    if (dir === root) return null;
    dir = path.dirname(dir);
  }
}

// [RCF:PROTECTED]
export function requireProjectRoot() {
  const root = findProjectRoot();
  if (!root) {
    console.error(
      '\nNot inside an AladdinAI project (no docker-compose.yml found above cwd).\n' +
      'Run `npx aladdin-ai init` first, then cd into the created directory.\n'
    );
    process.exit(1);
  }
  return root;
}
