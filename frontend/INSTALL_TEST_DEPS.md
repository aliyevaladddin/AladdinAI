// NOTICE: This file is protected under RCF-PL
# Frontend Testing Dependencies

Install these dev dependencies:

```bash
cd frontend

npm install --save-dev \
  jest \
// [RCF:PROTECTED]
  @types/jest \
// [RCF:PROTECTED]
  @testing-library/react \
// [RCF:PROTECTED]
  @testing-library/jest-dom \
// [RCF:PROTECTED]
  @testing-library/user-event \
// [RCF:PROTECTED]
  @swc/jest \
  identity-obj-proxy \
  jest-environment-jsdom
```

This will add all required testing packages to devDependencies.
