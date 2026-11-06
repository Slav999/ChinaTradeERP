# Company chat

## Included

- Direct conversations and named groups (creator plus up to 99 selected colleagues).
- Only active, email-verified company members can use chat.
- The recipient directory includes all active company members with enabled user
  accounts, including those who have not verified email yet. They can receive
  messages, but must verify email before signing in and accessing chat themselves.
- A user can contact colleagues whose active UI company is different, provided both
  have active membership in the conversation's company.
- Plain text up to 5,000 characters, history in pages of 50, unread counters.
- “Mark unread” in the conversation menu sets a personal reminder and returns to
  the conversation list. It survives reloads and does not rewind read receipts or
  affect other participants. Viewing messages dismisses it; for empty/already-read
  windows the read endpoint accepts `message_ids: []` to clear only the reminder.
- Conversation search matches group titles, colleague names/usernames, visible
  message text/authors and accessible shared references (including product SKU,
  product name and order number). Deleted/personally cleared messages cannot
  make a conversation match. Suggestions remain bounded to five, while searches
  of shared history use all matching permitted records with paginated results.
- Authors can edit their own text or delete a message for everyone. Edited text
  is labelled; deletion scrubs text/references/mentions/reactions/pins and leaves
  a tombstone. Attachments become inaccessible immediately. Deleted content is
  also removed from reply previews and subsequent incremental updates.
- Replies quote a message in the same conversation, with navigation to its
  original context. Personally cleared quotes do not disclose hidden content.
- Initial history opens at the first unread message (or mention when selected),
  with a new-message divider. Actual visible message IDs are acknowledged;
  reading a late mention leaves earlier unseen messages unread.
- Authors see “Read” in direct chats (first confirmed view time on hover), and
  “Read X of Y” for current other group participants, expandable to names/times.
  The read-status endpoint is restricted to the author's own visible live
  messages and at most 100 IDs. Only visible outgoing messages are polled.
  Migration 0007 adds nullable first-view times; previously compacted receipts
  cannot be reconstructed and require a fresh view. Joining or clearing history
  does not manufacture receipts; personal “mark unread” does not erase them.
- Draft text, replies, reference cards and retry UUIDs are saved per user/company/
  conversation for seven days and removed on logout. File selections survive
  conversation switches in memory; after reload the user is asked to reattach
  files. An uncertain send is checked by its UUID before a retry.
- Pending sends show sending/failed/retry state and file upload progress. A server
  acknowledgement is labelled sent, without claiming that the recipient read it.
- Reactions (👍 ✅ 👀 ❤️ 🙏), one per user/message, up to ten pinned messages,
  searchable messages, files and reference libraries are available. Choosing a
  different reaction replaces the previous one; selecting it again removes it.
  Pins open from the conversation's pinned strip. Group events remain in the
  conversation timeline but have no separate search tab.
- The group owner can transfer management to an active participant. Non-owners
  can leave; the owner must transfer first if others remain. A company admin who
  is already a participant can recover management if the owner loses company
  access, without access to anyone else's private conversations.
- Group creation/rename/membership changes/transfer/leaving are recorded as
  system events. Owners and initial creators are stored separately.
- Per-conversation all/mentions-only/off sound preferences live in the conversation
  menu. Personal archive/restore icons sit beside each conversation's arrow in the
  list, for direct chats and groups. The archive filter opens archived conversations.
  Archiving does not delete history. The list search has an inline clear button.
  Sending a new message automatically restores the sender's archived conversation
  to the main list. Incoming messages leave the recipient's archive preference
  unchanged; failed sends and retries of an already accepted message do too.
- “Delete for everyone” immediately deletes an author's message without a second
  confirmation. The server retains the tombstone and existing author-only checks.
- Saved order detail pages (customer/supplier/sample), product cards and
  counterparty cards/previews have an accessible-discussions button, shown only
  when a permitted, live reference exists in the requester's visible chat history.
  The lightweight `related/?exists=1` check returns only `has_discussions`.
  Buttons refresh when record/user/company changes, on window focus, and when
  chat revision changes are detected. Opening from a modal closes that modal.
  Selecting a related conversation requests its latest visible live reference
  via `messages/?reference_type=...&reference_id=...` and opens a context window
  around that message, even when newer messages span months. Record permissions,
  participation and personal clearing boundaries are checked again on this jump.
- Duplicate direct conversations are prevented per company. A client UUID makes
  message retries idempotent.
- Small floating button, close by clicking outside, five-second polling. Background
  tabs poll conversation metadata for incoming sounds, without loading message
  history or marking messages read; browsers may throttle background timers.
- The group owner manages its name and participants; company-admin status does
  not grant management rights over other people's groups.
- Newly added/re-added members can read the complete group history and its files. Removal
  revokes all conversation and attachment access immediately on subsequent requests.
  Existing participants' personal clearing cursors are preserved. No existing data
  is reset: participants added under the previous history rule retain that old
  cutoff until they are removed and re-added.
- Personal history clearing hides messages and attachments for the current user.
  Deleting a direct chat also hides it from their list until a new message arrives.
- Deleting a group is owner-only and closes it for everyone (soft deletion).
  History and files are retained on disk/database; this is not physical erasure.
- Private photo/document attachments: up to 5 files, 20 MB per file and 50 MB per
  message. Supports JPEG/PNG/WebP/GIF, PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, UTF-8 TXT/CSV.
  Types are checked server-side; arbitrary executables and HTML/SVG are rejected.
- Screenshots can be pasted into the composer. Images are loaded lazily through
  authenticated requests; documents download as attachments.
- Share customer orders, supplier orders (including samples), products and
  counterparties. Search from the composer, or use the share button on order pages
  and order/product/counterparty rows (including sample/trip orders). Choosing a
  chat stages the object; Send submits it.
- Share buttons are also available inside saved product/counterparty cards.
  Sharing closes the overlay and stages the saved record in the chat.
- Reference search starts automatically 300 ms after typing a nonempty query and
  returns at most five matches: order number, counterparty name, product name/SKU,
  or trip name. Old responses are discarded when the query/company changes.
- Group settings initially show selected members only. Trash buttons stage their
  removal; searching other company colleagues offers at most five additions.
  Save applies the whole membership change; the owner cannot remove themselves.
- Type @ in the composer to choose a conversation participant by username/name.
  Mentions are rendered as safe highlighted text; own mentions also accent the
  message. Unread mentions show "Вас упомянули" in the conversation list;
  read/clear actions remove the marker. The launcher retains only its unread count.
  No cross-company/global employee lookup is performed for mentions.
- The composer offers thirty native Unicode emoji with insertion at the cursor.
- Chat and ordinary notifications share a soft local Web Audio chime, unlocked by
  a click/key press. Initial unread history and own messages do not trigger it.
  No external sound service or audio download is used. Chat metadata exposes a
  last-incoming-message marker so read receipts and own sends are silent.
  Unlock handlers include click/touch release; playback waits for asynchronous
  resume and recovers from suspended/interrupted audio contexts. Sound controls
  are not shown in the chat or ordinary notification panel. Actual audibility still depends
  on browser/site/tab/OS volume settings; no browser policies are changed.
- Reference titles and routes are resolved per recipient's current company and
  role permissions. References do not share prices or grant access to an object.

No new packages, paid services, WebSocket server or Redis are required.

## Access contract

All `/api/chat/` requests require the existing JWT authentication and a
`company_id` query parameter matching the user's current company. Mutations using
cookie authentication retain the existing CSRF requirements. A stale company
context returns 409; the client clears company data and reloads the profile.

Conversation IDs, company IDs and user IDs supplied by clients never grant access.
Every message/history/read request checks conversation participation and current
active company membership. Company administrators have no implicit access to
other employees' conversations. Disabling a company membership revokes chat access
without deleting history. HTML is displayed as text by Vue interpolation.

Files are stored in `backend/private_chat_files/`, outside MEDIA_ROOT, with UUID
paths. Do not expose this directory via a public web-server alias. Include it in
private backups and persistent storage when deploying. Downloads check company,
participation and the user's personal history-clearing cursor on every request.
Serving files does not provide malware scanning; documents should be treated as
user uploads. Physical retention/cleanup uses the explicit administrative command
below and is not scheduled automatically.

Chat uses separate per-user throttle budgets: 120 reads/minute and 30
mutations/minute, instead of the ERP-wide daily budget. Visible-message read
receipts have a separate 60/minute budget. The contiguous unread cursor still
advances, while detailed receipts are retained for first-view times. These rows
grow with actually viewed incoming messages and belong in capacity planning.
These use Django's configured cache, like the existing DRF throttles; distributed
deployments should use a shared cache for consistent limits across workers.

## Setup and verification

From the project root with its virtual environment:

```powershell
.\venv\Scripts\python.exe backend/manage.py migrate chat
.\venv\Scripts\python.exe backend/manage.py test chat --noinput
```

The 0003–0005 migrations extend only chat tables and preserve existing owners and
mentions. Mentions are now stored at send/edit time and remain stable after
participants leave or change nicknames. Deleted messages remain as tombstones.
Migration 0006 adds the personal unread-reminder flag without changing read cursors.

Conversation lists are searched/paginated (30 by default, at most 50), and employee
lookups return at most 50. Closed/background chats request compact notification
metadata; selected histories synchronize by revision rather than reloading whole
threads. Reaction/edit/deletion and changed reply previews share the same cursor.

Migrations affect only the chat module. Apply the latest migration before using
the updated frontend; no order, product or user model changes are required.

Manual checks, using separate browser sessions for different employees:

1. Log in and click the floating Chat button near the bottom right.
2. Select New, choose a colleague, and send text including multiple lines.
3. Check receipt within about five seconds and the unread badge while the
   recipient's chat is closed; open the conversation to clear the badge.
4. Create a named group with selected colleagues. Check that all selected users
   see the group and that an unselected colleague cannot see it.
5. Switch company while a conversation is open: previous messages and drafts
   must disappear. Repeat a switch in a second browser tab.
6. Disable a member's company access and check that subsequent reads and sends
   are rejected. Check another company's user cannot access a known room ID.
7. Check long history with Previous messages, network failure and send retry,
   small-screen layout, and Escape/Close behaviour.
8. In a group open the three-dot settings: rename, add and remove a colleague.
   Verify that a non-creator cannot manage members or delete the group, a removed
   member loses downloads. A new/re-added member should see older messages and attachments; check
   that existing participants' personal clear history is preserved.
9. Clear history in one session and check that it stays visible to the other user.
   Delete a direct chat, send a new message from the other side and check it returns.
10. Upload a real screenshot and PDF/Excel file, paste an image, view/download it;
    check oversized and unsupported uploads are rejected.
11. Share each order kind from its page and a product from its row; select an
    existing or new chat, send and follow the record card. Also search via the
    box icon in the composer and check recipients without record permissions.
12. Click outside the chat to close it. Hover over the participant count, then
    open the full list through the count or three-dot menu.
13. Type @ and choose a participant with the mouse or arrow keys/Enter; check
    highlighting on both clients and Shift+Enter for a new line.
14. After interacting with the page once, receive a new chat message and a new
    ordinary notification: each should sound softly. Reload with old unread
    history, send your own message, and read a chat: these should stay silent.

Frontend notification/mention logic tests (from `frontend/china_trade_erp`):

```powershell
node --experimental-default-type=module --test src/utils/chatUpdates.test.mjs src/utils/notificationSound.test.mjs
node --experimental-default-type=module --test src/utils/chatThread.test.mjs
node --experimental-default-type=module --test src/composables/chatComposer.test.mjs
node --experimental-default-type=module --test src/utils/chatTranslations.test.mjs
```

## Storage and backups

There is no aggregate storage quota per company. Uploads are not blocked after
5 GiB or any other company-wide threshold. Limits per send remain: 5 files,
20 MiB per file and 50 MiB total. The protected storage API reports usage and
allows company administrators to configure deleted-file retention, without quota
settings; these controls are hidden from the chat UI. The default
retention is 30 days for files of deleted messages/groups; active files are never
removed based solely on age or a personal history clear.

Administrative commands from the project root:

```powershell
.\venv\Scripts\python.exe backend/manage.py cleanup_chat_uploads
.\venv\Scripts\python.exe backend/manage.py cleanup_chat_uploads --company 1 --apply
.\venv\Scripts\python.exe backend/manage.py backup_chat --output C:\private-backups\chat-2026-11-06.zip
```

Cleanup defaults to a read-only preview. `--apply` physically removes only files
past the configured deleted-file retention and marks their records as purged.
Backup refuses overwrite and includes chat metadata, private files and SHA-256
checksums. The target directory must already exist; protect the archive as
company data. Keep it together with the matching main database backup containing
users and companies. No production cron, scheduled cleanup, or backup destination
has been configured automatically.

## Additional manual checks

- Switch between two conversations and reload: text drafts should survive. Log
  out: drafts should be cleared. Reattach files after reload if prompted.
- Receive over 50 messages, open at the first unread, then jump to a late mention:
  older unseen messages must remain unread.
- Edit/delete your own message in one session: another session should update it
  and its quoted replies; removed attachments should no longer download.
- Confirm another user (including a company admin) cannot edit/delete your text.
- Exercise reaction replacement/removal, pins, message/file searches, the archive
  list and sound modes.
- Transfer group ownership, leave and read timeline events. Recover an inactive
  owner only from an existing company-admin participant account.
- In an order select Discussions: only accessible linked conversations should show.
- Check Chrome/Edge/Firefox, mobile viewport, long text, upload failure/progress,
  sound after a user gesture and keyboard navigation.

Automated coverage includes cross-company and participant isolation, groups,
disabled memberships, verified email, pagination, unread cursors, idempotent send,
group administration, joined-history boundaries, clearing/deletion, private files,
reference permissions, anonymous access, cookie/CSRF authentication, authored
edits/deletion, incremental reply updates, visible-message receipts, ownership,
per-upload limits and backup/purge behaviour. Browser visual QA remains manual:
the available browser tool timed out reaching the local test server. A temporary
isolated UI harness was removed to keep test infrastructure small.

See [REVIEW.md](REVIEW.md) for the latest review findings and deployment gaps.

Composer state lives in `src/composables/useChatDrafts.js` (storage, previews,
restore/edit context and retry identity) and `useChatDelivery.js` (upload progress,
send/retry status and session invalidation). `CompanyChat.vue` coordinates these
with conversation navigation. The composable tests use Vue's actual reactivity
and controlled API responses, without a custom renderer or browser harness.

Standard chat labels/tooltips follow the existing Russian/English language state.
`chatTranslations.js` extends the app translator only for `data-chat-ui` roots;
asynchronous chat updates are observed within those roots. User messages, names,
group titles, filenames and product/counterparty names use `data-i18n-skip` and
are not translated. Generated order labels and system event text are localized
separately. Translation tests check static component labels and script strings.
Native browser visual verification was blocked when Computer Use could not
identify the current browser URL confidently; icon alignment remains a manual QA check.
