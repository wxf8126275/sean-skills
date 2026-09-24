# Project Onboarding

> AI-readable project primer. Any agent can read this to understand the project quickly.

## Project Name

{{project_name}}

## Tech Stack

- **Language**: {{language}}
- **Framework**: {{framework}}
- **Database**: {{database}}
- **Frontend**: {{frontend}}
- **Testing**: {{test_framework}}
- **CI/CD**: {{ci_cd}}

## Directory Structure

```
{{project_root}}/
├── apps/
│   ├── server/          # Backend application
│   │   ├── src/
│   │   │   ├── core/    # Domain modules (one per feature)
│   │   │   └── app.module.ts
│   │   └── test/
│   └── client/          # Frontend application
│       ├── src/
│       │   ├── features/  # Feature-based modules
│       │   └── pages/
│       └── tests/
```

## Key Patterns

- **Module structure**: Each feature is a self-contained module under `core/`
- **Testing**: Unit tests colocated with source (`*.spec.ts`)
- **DTOs**: Use class-validator for input validation
- **Permissions**: CASL-based ability system
- **API style**: RESTful with conventional HTTP status codes

## Common Commands

```bash
# Install
pnpm install

# Run tests
pnpm test

# Run dev server
pnpm dev

# Build
pnpm build

# Migration
pnpm migration:run
```

## Conventions

- Conventional Commits for commit messages
- Lowercase kebab-case for file names
- Feature-based directory organization
- One module per domain concept
- Tests must be RED before GREEN (TDD enforced by sean)

## Recent Changes

{{recent_changes}}
