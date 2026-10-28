# `@scope/tsconfig` — shared TypeScript configs

The single source of TypeScript compiler options across the monorepo. Every TS package or app extends one of these files via its `tsconfig.json` instead of redefining `compilerOptions`.

## Files

| File | Extends | Use when |
|---|---|---|
| [`base.json`](base.json) | — | Any TS package. Defines `ES2023`, `bundler` module resolution, strict mode, `noEmit`, and verbatim module syntax (Vite / esbuild / swc friendly). |
| [`react.json`](react.json) | `./base.json` | React packages + apps. Adds `jsx: "react-jsx"`. |
| [`node.json`](node.json) | `./base.json` | Node-only scripts or libraries. Adds `lib: ["ES2023"]` + `types: ["node"]`. |

## Consumption

From any workspace package:

```jsonc
// packages/ui/tsconfig.json
{
  "extends": "@scope/tsconfig/react.json",
  "include": ["src"]
}
```

`@scope/tsconfig` must appear as a `devDependency` in the consumer's `package.json` at `"workspace:*"`.

## History

Populated in Phase 4 Wave 1 (`phase4-wave-1.1`) by `git mv` from the pre-Phase-4 `unmigrated/scope-app/packages/tsconfig/`. Content unchanged from that canonical source.

Plan: [`.cursor/plans/phase_4_caller-driven_migration_01bc891c.plan.md`](../../.cursor/plans/phase_4_caller-driven_migration_01bc891c.plan.md) §Wave 1.
