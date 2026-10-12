// eng-ai base for ESLint flat config. Needs: npm i -D eslint typescript-eslint
// Use from your own config:
//   import base from "./.eng-ai/lint/typescript/eslint.config.mjs";
//   export default [...base, { /* repo overrides */ }];
import tseslint from "typescript-eslint";

export default [
  ...tseslint.configs.strict,
  {
    rules: {
      // TYP-001 no untyped escape hatches
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/no-non-null-assertion": "error",
      // ERR-001 no swallowed errors
      "no-empty": ["error", { allowEmptyCatch: false }],
      // SEC-008 no dynamic code evaluation
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      // OBS-001 log through the project logger, never console
      "no-console": "error",
      // CPX-001 keep functions simple
      complexity: ["warn", 10],
    },
  },
];
