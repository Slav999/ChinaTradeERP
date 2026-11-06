# Chat review — 2026-11-06

Scope: all chat application modules, migrations, upload/backup/cleanup commands,
Vue chat components and utilities, and chat integration with authentication,
notifications and ERP record sharing. Production settings were not changed.

Subsequent product decision: aggregate per-company storage quotas have been
removed, including the quota database field and API setting (migration 0008).
Per-upload file/count/total-size validation and private backup/purge coordination
remain. Existing messages and uploaded files are unchanged by this migration.

## Correctness fixes made during review

- Late history/mutation responses no longer replace a message with an older
  revision, including restoring text that another response already deleted.
- Incremental changes to unloaded older messages no longer prepend isolated
  rows to the loaded window and skip the intervening history on “load older”.
- Draft saving waits until restoration completes. A failed initial history
  request can no longer overwrite an existing draft with an empty composer.
- Identity changes and logout in another tab clear in-memory drafts and pending
  deliveries, in addition to the existing persistent-storage cleanup.
- Selecting a colleague fetches an existing conversation directly when it is
  outside the first list page or in the archive.
- Employee filtering includes usernames. Group candidate search excludes current
  participants on the server before applying its result limit; the requester
  must participate in the supplied conversation.
- History searches use all permitted matching reference IDs as SQL subqueries.
  The five-result suggestion limit now applies only to the composer picker.
- A missing physical upload returns 404 instead of an unhandled server error.

## Verification

- `python backend/manage.py test chat users --noinput`: 89 passed, PostgreSQL
  test database created and removed by Django.
- Three chat/sound utility test files: 12 passed, including regressions for stale
  responses and history gaps.
- `npm run build`: passed. Existing Bootstrap/Sass deprecation and large bundle
  warnings remain (main bundle about 691 KB, about 202 KB gzip; whole application).
- `makemigrations chat --check --dry-run`: no model changes detected. The sandbox
  could not check live migration history in this command; the complete database
  test suite ran with local PostgreSQL access separately.
- Access tests cover company/participant isolation, revoked membership, CSRF,
  reference permissions, authored edits/deletion, private uploads and owner roles.
- No real-browser visual/audio test or load test was completed during this review.
  Passing compilation and mocked sound tests do not establish actual audibility.

## Before public deployment

1. Configure the application API origin: `src/axios.js` currently hardcodes
   `http://localhost:8000/`. Prepare environment-based deployment configuration,
   HTTPS, allowed hosts and non-debug settings as a separate deployment task.
2. Load-test realistic room/history/file counts and simultaneous employees.
   Polling runs every five seconds; compact responses still inspect all of the
   user's conversations. Multiple tabs multiply these requests.
3. Measure database queries on reference-heavy history and large group lists.
   Reference serialization currently resolves records individually, and owner
   recovery checks can add a query per group for company admins. Batch those
   lookups if profiling confirms a bottleneck; no architecture rewrite is needed.
4. Use a shared cache for consistent throttles with multiple server workers.
   Keep private chat files outside public media aliases, on persistent storage;
   configure web-server upload limits to accommodate the documented file sizes.
5. Schedule protected backups and retention cleanup, then test restoration with
   a matching main database backup. Consider upload malware scanning if required
   by the deployment's document handling policy.
6. Check two real sessions in Chrome/Edge/Firefox and a narrow mobile viewport:
   sound after a user gesture, mentions, removing participants, failed/retried
   sends, draft restoration after failed loading, logout in another tab, file
   downloads and the aligned ownership-transfer controls.

## Maintainability

Keep Vue/Bootstrap and the current API. There is no evidence here that adding a
chat framework, Redis or WebSockets would fix the reviewed correctness issues.
Draft/delivery handling has subsequently been moved from CompanyChat.vue into
`useChatDrafts.js` and `useChatDelivery.js`, with direct composable tests covering
room switching, draft restoration, failed send retries, logout during a request
and cancellation of editing. Canceling editing now also restores the original
draft's retry UUID after reload, preserving idempotence for uncertain sends.
After extraction, all 19 frontend tests and the full production build passed;
the backend implementation and dependencies were unchanged by this refactor.
Further UI/features and dependency upgrades should remain separate changes.
The size of source code alone is not a useful performance metric.
