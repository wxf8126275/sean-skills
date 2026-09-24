# Handoff: comments

> **Generated**: 2026-09-23T12:00:00+08:00
> **Source**: sean handoff

## Status

- **Overall**: BLOCKED
- **Tasks completed**: 3 / 5
- **Last updated**: 2026-09-23T12:00:00+08:00

## What Was Done

| Task | Status | Summary |
|------|--------|---------|
| 1 | done | Comment entity + DTO with validation |
| 2 | done | CommentService (create, findByPageId, delete) |
| 3 | done | CommentController (POST, GET, DELETE endpoints) |
| 4 | failed | Permission guard for author/admin deletion |
| 5 | — | Frontend components (not started) |

## File Inventory (verified on disk)

### Created

- `apps/server/src/core/comment/comment.entity.ts` — Comment entity with TypeORM decorators
- `apps/server/src/core/comment/comment.service.ts` — Service with CRUD operations
- `apps/server/src/core/comment/comment.controller.ts` — REST API controller
- `apps/server/src/core/comment/comment.module.ts` — NestJS module definition
- `apps/server/src/core/comment/dto/create-comment.dto.ts` — DTO with class-validator
- `apps/server/src/core/comment/guards/comment-permission.guard.ts` — Permission guard (incomplete)

### Modified

- `apps/server/src/app.module.ts` — Registered CommentModule

### Tests

- `apps/server/src/core/comment/comment.entity.spec.ts` — Entity validation tests
- `apps/server/src/core/comment/comment.service.spec.ts` — Service unit tests
- `apps/server/src/core/comment/comment.controller.spec.ts` — Controller integration tests

## Current Blocker

- **Issue**: Permission guard CASL ability check returns 500 instead of 403
- **What was tried**: Injected AbilityService, checked ability for `delete-comment` action
- **Suggested direction**: Debug CASL ability registration — ability may not be initialized for comment resource

## Next Steps

1. Fix CASL ability registration in AppModule for comment resource
2. Re-run permission guard tests to confirm 403 vs 401 distinction
3. Continue with frontend components (Task 5)

## Known Risks / TODOs

- Frontend tests use Vitest, need separate config for jsdom environment
- WebSocket for real-time comment updates deferred to v2

## How to Resume

```bash
cd docmost
sean status comments              # check current state
sean task comments 4              # resume Task 4 only
pnpm test apps/server/src/core/comment/guards/  # run permission tests
```
