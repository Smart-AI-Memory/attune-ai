import nextCoreWebVitals from "eslint-config-next/core-web-vitals";
import nextTypescript from "eslint-config-next/typescript";

const eslintConfig = [
  ...nextCoreWebVitals,
  ...nextTypescript,
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
      "public/framework-docs/**",
    ],
  },
  {
    rules: {
      // Allow inline styles for dynamic values and complex gradients
      // that cannot be easily expressed with Tailwind utility classes
      "react/style-prop-object": "off",
      "@next/next/no-css-inline": "off",

      // === Code Quality Rules ===
      // Enforce const for variables that are never reassigned
      "prefer-const": "error",

      // Enforce === instead of == (except for null checks)
      "eqeqeq": ["error", "always", { null: "ignore" }],

      // Disallow var, use let/const
      "no-var": "error",

      // Warn on console usage in components (allow in API routes)
      // Note: API routes legitimately use console for server logging
      // This warns on client-side code
      "no-console": ["warn", {
        allow: ["warn", "error", "info", "debug"]
      }],

      // Security: Disallow eval and similar
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",

      // Security: Disallow script URLs
      "no-script-url": "error",

      // Prevent common mistakes
      "no-return-await": "error",
      "no-throw-literal": "error",
      "no-useless-catch": "error",

      // React-Compiler-era rules new in eslint-config-next 16 flag
      // pre-existing shipped patterns (theme/localStorage hydration,
      // initial-fetch effects); warn until those sites are refactored
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/immutability": "warn",
      "react-hooks/static-components": "warn",

      // TypeScript strict rules
      "@typescript-eslint/no-unused-vars": ["error", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
        caughtErrorsIgnorePattern: "^_"
      }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  // Allow console.log in API routes and lib (server-side logging)
  {
    files: ["app/api/**/*.ts", "app/api/**/*.tsx", "lib/**/*.ts"],
    rules: {
      "no-console": "off",
    },
  },
];

export default eslintConfig;
