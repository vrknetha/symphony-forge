# Client apps pass a VAPT test without per-client security work

14 parts · Risks: none one-way · New moving parts: the `qrcode` package in the web app, and four pinned scan tools in the nightly full run

## What changes for you

- Sign-in, sign-up and password reset show the same message for every email, and take about the
  same time, so nobody can find out which emails have an account.
- Sign-up starts with the email only. The app sends a link, and the person sets a password from
  that link. When the email already has an account, the email says so and links to sign in.
- After 10 failed sign-ins for one email, sign-in for that email stops for 15 minutes. The limit
  for each network address stays as it is.
- A new password that is on a list of leaked passwords is refused. The list is part of the app,
  so the check sends nothing over the network.
- A session ends after 30 minutes without use and after 12 hours at most. Sign-out ends it on the
  server. A password reset ends all sessions of the account. Each sign-in starts a new session.
- Admins must set up a code from an authenticator app, with recovery codes, before they can use
  the app. Members can turn it on and off in Settings. Sign-in then asks for the code.
- Failed sign-ins, role changes and invites go to the app's log as security events. The log
  holds no email, name or password.
- The web app sends the security headers that a VAPT test checks, and no server version. Sign-in
  goes on only to the app's own pages.
- The Python starter gets the same rate limits, headers and form-forgery guard as the
  TypeScript starter.
- Each night the full run also checks the packages for known holes, the history for secrets, the
  code against the OWASP rules, and the running app with a ZAP scan. A finding opens a fix, as a
  failed nightly test does now.
- New apps get all of this from the starters. Existing apps keep their code on upgrade; the guide
  says how to copy each part from the starter.

Design: docs/design/FORGE-VAPT-1/ (TREE)

## Why

Client apps would fail a VAPT test today. In both starters, sign-up says that an account already
exists, sign-in answers faster for an unknown email, and password reset answers faster for an
unknown email. Both starters have no lockout for one email, no authenticator code, no
leaked-password check and no security log. Sessions in both starters last 30 days with no idle
timeout. Neither web app sends a Permissions-Policy header, and the Python app names its server
in each reply. The Python starter checks the form-forgery token only on the routes that ask for
it. The nightly full run only runs tests. On 25 October 2026 the owner chose to meet the OWASP
ASVS Level 2 checks that apply, once in the starters, each with a test.

## Done when

1. **In both starters, sign-in, sign-up and password reset give the same reply for an email with an account and an email without one, and a sign-in for an unknown email takes at least half as long as a wrong password.**
2. **In both starters, sign-in for an email stops for 15 minutes after 10 failed tries, a leaked password is refused, and failed sign-ins, role changes and invites write a security event with no personal data.**
3. **In both starters, each sign-in starts a new session, a session ends after 30 minutes idle or 12 hours, a password reset ends all sessions, sign-out ends the session on the server, and the cookies are HttpOnly, Secure and SameSite.**
4. **Both web apps send CSP with frame-ancestors, HSTS, Referrer-Policy and Permissions-Policy, and no version header; the Python starter has the same rate limits and form-forgery guard as the TypeScript one; sign-in goes on only to the app's own pages.**
5. **In both starters, an admin cannot use the app until they set up an authenticator code with recovery codes; a member can turn the code on and off; sign-in then asks for a code or a recovery code, and each code works once.**
6. **The nightly full run of a new app also runs the package audit, gitleaks, semgrep with the OWASP rules and a ZAP baseline scan, and a finding fails the run and opens a fix. An existing app's code does not change on upgrade, and the guide says how to copy each part.**

## Risks

<!-- Each one-way step: deleting data, a destructive migration, a new vendor. -->

Risks: none one-way. Each part reverts with its pull request. The new migrations change only the
starters, which a new app copies at set-up; no existing app gets them.

Trade-off: sign-up now needs email. In local and test runs the link goes to the log, as the reset
and invite links do now. A production app without a mail provider refuses every sign-up with one
clear message, as it refuses invites now, until a story adds a mail provider.

Trade-off: anyone who knows an email can stop sign-in for it for 15 minutes with 10 wrong
passwords. The per-address limit slows this down. Lockout for each email, not each address, is
what the check asks for.

Trade-off: an admin who loses the authenticator and all recovery codes cannot sign in. Another
admin, or support with database access, must turn the code off. No screen does this.

## For the builders

<!-- Everything from here down is for the agents. The owner doesn't see it when approving, and
tightening it needs no new approval. -->

All paths under `starter/` mean `src/forge/templates/starter/`, and paths under
`starter-python/` mean `src/forge/templates/starter-python/`. The Python starter has no web app of
its own: `forge init --starter python` copies `starter/apps/web` (`init._starter_files`), so each
web part changes both starters, and its Playwright flows run against both APIs.

Each new test file starts with `STORY = "FORGE-VAPT-1"`. Forge's tests run the forge command or
the starters' own suites and never import forge. One test per Done-when rule, named
`test_<n>_...`. As in FORGE-DEFAULTS-1, the starter's behaviour is proven by its own cases
(Supertest against the real API and Postgres in `compose.test.yml`, pytest with httpx against the
Python API, Playwright flows against the built app), and each pytest test in `tests/` requires its
case names from the live run with `_require_cases(live_run(...)[...], CASES)` and
`live_python_starter`. Live tests carry `@pytest.mark.platform` and a `@pytest.mark.timeout`.
Each `test_<n>` also has its existing-repo case (see "New and existing repos").

### What the starters do today (checked 25 October 2026)

- Sign-up: `AuthService.createAccount` (TS) and `_create_account` (Python) answer
  `409 EMAIL_ALREADY_REGISTERED` "An account already uses that email."
- Sign-in: both return early for an unknown email, before scrypt runs, so the reply is about
  scrypt's time faster (scrypt N=2^17 takes about 150 to 300 ms).
- Forgot password: both give the same message, but only a known email writes a token and sends
  mail before the reply.
- Throttling: TS has a global `ThrottlerGuard` (120 a minute for each address) and 30 a minute on
  sign-up, sign-in, accept-invite, forgot and reset password and error reports. Python has the 30
  a minute on the same paths (`_RATE_LIMITED_PATHS`) and no general limit.
- Sessions: 30 days (`SESSION_LIFETIME_MS`, `_SESSION_LIFETIME`), no idle timeout. Each sign-in
  makes a new random token; an existing session cookie stays valid. Sign-out deletes the row.
  Reset deletes all sessions of the account. There is no password change for a signed-in person.
- Cookies: `starter_session` (HttpOnly) and `starter_csrf` (readable by the web app), SameSite
  Lax, Secure outside `development` and `test`, no `__Host-` prefix.
- Headers: production serves the web app from the API (TS `express.static` plus the index route
  in `apps/api/src/main.ts`; Python the `web_app` catch-all in `app/main.py`). TS uses
  `helmet()` defaults; Python sets the helmet-like list in `app/core/security.py::_headers`. Both
  send CSP with `frame-ancestors 'self'` and `base-uri 'self'`, HSTS with includeSubDomains and
  Referrer-Policy `no-referrer`. Neither sends Permissions-Policy. Uvicorn sends
  `server: uvicorn`; helmet removes `X-Powered-By`.
- Form-forgery guard: TS `CsrfGuard` is global and checks every state-changing request with a
  session. Python checks only routes that depend on `require_csrf` or `admin_only`.
- Redirect: the protected layout passes `state.from`, and the sign-in page ignores it and always
  goes to `/projects`. No open redirect today.
- Logs: `JsonLogger` (TS) and `app/core/logging.py` (Python) write JSON lines; `ErrorReporter`
  writes error reports. No security events.
- Nightly: `forge.yml`'s `full-suite` job (CI test place) and `forge test --full` (local) run
  forge.toml's `test` through `review.test_run(..., always=True)` in `src/forge/fullrun.py`. A
  failed scheduled run shows in `forge next` (`nextstep._failed_schedules`) with a
  `forge fix start` line; a failed local full run prints one.

### Words this story pins

The part named first owns each name; later parts use it and list that part under After.

- **Security event (SIGNIN pins, SIGNINPY copies).** TS: `libs/core/src/common/security-events.ts`
  exports `SecurityEvents` (injectable, in `CommonModule`) with
  `record(event: SecurityEvent, fields: { accountId?: string | null; organisationId?: string | null; targetAccountId?: string | null })`.
  It writes one `JsonLogger.warn` line with message `Security event`, module `SecurityEvents`,
  and context `{ event, accountId, organisationId, targetAccountId, correlationId }`. Python:
  `app/core/security_events.py::record_security_event(event, *, account_id=None,
  organisation_id=None, target_account_id=None)` writes the same JSON fields through the
  existing logger. `SecurityEvent` is one of `sign_in_failed`, `sign_in_locked`,
  `mfa_code_failed`, `mfa_enabled`, `mfa_disabled`, `role_changed`, `invite_sent`. Ids only: no
  email, no network address, no password, token or code (security.md's "Secrets and personal
  data" rule). A failed sign-in for an unknown email logs `accountId: null`.
- **Lockout (SIGNIN).** Table `SignInLockout` / `sign_in_lockouts`: `emailHash` (sha256 hex of
  the normalized email, primary key), `failures` int, `firstFailureAtUtc`, `lockedUntilUtc`
  nullable. It is keyed by email, not by account, so an unknown email locks the same way and the
  lock tells nothing. 10 failures within 15 minutes set `lockedUntilUtc` to now plus 15 minutes;
  a success deletes the row; a failure after the 15-minute window starts the count again. While
  locked, sign-in (and the code step of item 5) replies `429 SIGN_IN_LOCKED` "Too many failed
  sign-ins for this email. Try again in 15 minutes." also for the right password.
- **Leaked passwords (SIGNIN).** `starter/libs/auth/src/leaked-passwords.txt` and
  `starter-python/apps/api/app/auth/leaked_passwords.txt`, the same file: the entries of SecLists
  `Passwords/Common-Credentials/10-million-password-list-top-1000000.txt` (MIT licence, name the
  source and licence in the file's first comment line) with 12 to 128 characters, one a line. A
  password that equals a line (exact match, as ASVS 6.2.8 wants) is refused with
  `400 VALIDATION_FAILED` and the field error on `password`: "This password is on a list of
  leaked passwords. Choose another." in the existing field-error shape, so the web shows it with
  `applyApiFieldErrors` and needs no change. The check runs where a password is set: sign-up
  finish, accept invite, reset password. Load the file once at start into a `Set`.
- **Session limits (SESSIONS).** `SESSION_IDLE_MS = 30 * 60 * 1000` and
  `SESSION_MAX_MS = 12 * 60 * 60 * 1000` (Python `timedelta`s of the same names). Session gets
  `lastSeenAtUtc`. The guard ends (deletes) a session when `now - lastSeenAtUtc > idle` or
  `now > expiresAtUtc` (expires is set at creation to now plus max). It updates `lastSeenAtUtc`
  when it is more than 60 seconds old (one write a minute, not each request). The cookie's
  `expires` is the max age.
- **Cookie names (SESSIONS).** Outside `development` and `test`: `__Host-starter_session` and
  `__Host-starter_csrf` (Secure, Path `/`, no Domain), so ASVS 3.3.1 and 3.3.3 hold. In
  `development` and `test`: `starter_session` and `starter_csrf`, because a browser refuses a
  `__Host-` cookie without Secure on plain http. One function in each API picks the names. The
  web `csrfToken()` in `apps/web/src/lib/api-client.ts` reads `__Host-starter_csrf` first, then
  `starter_csrf`, so it works with both APIs at all times.
- **Sign-up endpoints (SIGNUP pins).** `POST /api/v1/auth/sign-up/start` `{ email }` replies
  `202 { message: "Check your email. The link to finish sign-up works for one hour." }` for every
  email. `POST /api/v1/auth/sign-up/finish` `{ token, password }` creates the account and its
  organisation and starts the session, as `POST /auth/sign-up` does now (201, account, cookies).
  Table `SignUpToken` / `sign_up_tokens` (email, tokenHash, expiresAtUtc), one hour, used once,
  as `PasswordResetToken`. Mail: `MailProvider.sendSignUp(email, url)` (link to
  `/finish-sign-up?token=`) and `MailProvider.sendAccountExists(email, signInUrl)`. Shared
  schemas `signUpStartSchema` and `signUpFinishSchema` in both `libs/shared/src/index.ts`. A
  production app without a mail provider refuses the start with the same status and code as an
  invite without one, before it reads the email, so the refusal is the same for every email.
- **Reply first (SIGNIN and SIGNUP).** Sign-up start and forgot password check the input, reply,
  and then do the email lookup, token write and mail. TS: the service method returns the message
  and starts `void this.deliver(email).catch(...)`, which sends a failure to `ErrorReporter`.
  Python: FastAPI `BackgroundTasks`; the task opens its own database session from
  `app.state.session_factory`, because the request's session closes before the task runs.
- **Codes (MFA pins).** TOTP by RFC 6238 with the standard library (TS `node:crypto` HMAC-SHA1;
  Python `hmac`), 6 digits, 30-second step, a 20-byte secret from the CSPRNG in base32. A code
  for the current or the previous step is accepted, and only once: `Account.mfaLastStep` keeps
  the last used step, and a step at or below it is refused. Ten recovery codes, each 120 random
  bits as 24 base32 characters in four groups of six, stored as sha256 (ASVS 6.5.2 allows a plain
  hash at 112 bits or more), deleted on use. Account gets `mfaSecret` (nullable), `mfaEnabledAtUtc`
  (nullable), `mfaLastStep` (nullable). Table `RecoveryCode` / `recovery_codes`.
  Table `PendingSignIn` / `pending_sign_ins` (tokenHash, accountId, expiresAtUtc five minutes),
  cookie `starter_pending` / `__Host-starter_pending` (HttpOnly).
- **Code endpoints (MFA pins).** `POST /auth/sign-in` replies as now when the account has no code;
  when it has one, it replies `202 { codeRequired: true }`, sets only the pending cookie and
  starts no session. `POST /auth/sign-in/code` `{ code }` (a TOTP or a recovery code) starts the
  session and clears the pending cookie; a wrong code counts as a failed sign-in for that email
  (lockout and `mfa_code_failed`). `POST /auth/mfa/setup` returns `{ secret, otpauthUrl }` and
  stores the secret, not yet on. `POST /auth/mfa/confirm` `{ code }` turns it on, ends the
  account's other sessions, and returns `{ recoveryCodes }` once. `POST /auth/mfa/disable`
  `{ password, code }` turns it off for a member, ends the other sessions, and refuses an admin
  with `403 MFA_REQUIRED_FOR_ADMINS`. `/auth/me` gains `mfaEnabled: boolean` and
  `mfaSetupRequired: boolean` (role admin and code off). The `otpauthUrl` issuer is `APP_NAME`
  when the starter has one, else the app origin's host.
- **Admin enforcement (ENFORCE).** When `mfaSetupRequired` is true, the session guard (TS
  `SessionGuard`, Python `current_account`) allows only `GET /auth/me`, `POST /auth/sign-out` and
  the `/auth/mfa/setup` and `/auth/mfa/confirm` routes, and refuses all other routes with
  `403 MFA_SETUP_REQUIRED` "Set up your authenticator app to continue." Fail closed: a new route is
  refused until the admin has a code. The web protected layout sends such an account to
  `/settings/two-step`. The test helpers' `signUp` sets up the code for the new admin (each
  helper computes the TOTP from the returned secret with its own few lines), so the existing
  suites keep passing.
- **Full-run flag (SCAN pins).** `fullrun.run` sets `FORGE_FULL_RUN=1` in the environment of the
  test command it runs. No other run sets it. The starters' `scripts/test.mjs` runs
  `scripts/security-scan.mjs` after the browser suite, while the compose stack is up, only when
  `FORGE_FULL_RUN` is `1`.

### Done-when details

1. No account by message or by time (SIGNIN, SIGNINPY, SIGNUP, SIGNUPPY, SIGNUPWEB).
   - Sign-in: for an unknown email, run `verifyPassword` against one fixed dummy scrypt hash made
     at start, then reply `401 INVALID_CREDENTIALS` as for a wrong password.
   - Sign-up: the start reply and status are the same for a new and an existing email (pinned
     words). The finish page is `/finish-sign-up`. The old `POST /auth/sign-up` stays until
     SIGNUPWEB, which deletes it from both APIs after the web and every test use the new routes.
   - FORGE-SINGLECO-1's one-company refusal moves from `POST /auth/sign-up` to `sign-up/start`
     and `sign-up/finish` in SIGNUP and SIGNUPPY; its cases change only the path.
   - Forgot password: reply first (pinned words).
   - Accept invite keeps its conflict message: it needs a valid invite token, so a stranger cannot
     use it to test emails. An admin's invite to an existing account keeps "That person already
     has an account": only an admin of an organisation sees it.
   - API cases (TS names; Python cases are the snake_case twins with `test_`):
     `sign-in gives the same reply for an unknown email and a wrong password`;
     `sign-in for an unknown email takes at least half as long as a wrong password` (median of
     five of each, fresh emails each time so lockout does not start);
     `sign-up start gives the same reply for a new and an existing email`;
     `forgot password gives the same reply for a known and an unknown email`;
     `sign-up finish creates the account once and the link then stops working`.
     Mind the 30-a-minute limit for each address in one test file, as the existing suites do.
   - Flow: `a person signs up from the emailed link` (the e2e helper reads the link from the API
     log, as `invite()` in `apps/api/test/helpers.ts` does).
   - Test: `tests/test_vapt_accounts.py::test_1_no_account_by_message_or_time` requires these
     cases from both live runs, plus the existing-repo case.
2. Lockout, leaked passwords, security events (SIGNIN, SIGNINPY).
   - Lockout and leaked list as pinned. Keep the per-address limits as they are.
   - Events: `sign_in_failed` on each failed password or unknown email, `sign_in_locked` when a
     lock starts, `role_changed` (accountId the admin, targetAccountId the member) in the
     organisations service's role change, `invite_sent` in its invite. Use the service the module
     already has; organisations gets the event helper from core, not from auth.
   - API cases: `sign-in stops for 15 minutes after 10 failed tries, also for an unknown email`;
     `a leaked password is refused at sign-up, invite and reset`;
     `failed sign-ins, role changes and invites write security events with no email` (reads the
     log lines through `logEvents('api')` and checks that no line has the test email).
   - Test: `tests/test_vapt_accounts.py::test_2_lockout_leaked_passwords_and_security_events`.
3. Sessions and cookies (SESSIONS, SESSIONSPY).
   - Pinned limits and cookie names. Sign-in, sign-up finish, accept invite and the code step
     delete the session row of a session cookie that the request brings (ASVS 7.2.4).
   - Reset keeps ending all sessions; MFA confirm and disable end the other sessions (item 5).
   - The idle test does not wait 30 minutes: it moves `lastSeenAtUtc` back with `psql(...)` (TS)
     or the test database session (Python), then calls `/auth/me`.
   - API cases: `each sign-in starts a new session and ends the one it replaces`;
     `a session ends after 30 minutes idle and after 12 hours`;
     `a password reset ends all sessions`; `sign-out ends the session on the server` (the old
     cookie then gets 401); `production cookies are __Host- HttpOnly Secure SameSite=Lax` (against
     `production-api`; SameSite Lax because the app is same-site and Lax keeps links from mail
     working).
   - Test: `tests/test_vapt_sessions.py::test_3_sessions_end_and_cookies_are_locked_down`.
4. Headers, Python guards, redirect (HEADERS; the redirect is in MFAWEB).
   - TS `main.ts`: `helmet({ contentSecurityPolicy: { directives: { baseUri: ["'none'"] } } })`
     keeping helmet's other defaults, and one middleware that sets
     `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()`. Python
     `_headers`: `base-uri 'none'` and the same Permissions-Policy. The Swagger page keeps its
     nonce.
   - Python: `--no-server-header` in the Dockerfile's uvicorn command (and in the dev command in
     the README if it names one); a general limit of 120 a minute for each address on every path
     but `/health`, beside the 30 a minute on the auth paths, in `security_middleware`; and
     `current_account` calls `verify_csrf` for POST, PUT, PATCH and DELETE, so a route that only
     depends on `current_account` is guarded. Remove `require_csrf` and its uses, and the call in
     `admin_only`, since `current_account` now does it.
   - API cases, against `production-api` and on the web app's index route and one API route:
     `the web app and the API send the security headers and no version header`;
     Python also `test_a_signed_in_post_without_the_csrf_token_is_refused_on_every_route` (walks
     the app's routes) and `test_more_than_120_requests_a_minute_from_one_address_are_refused`.
   - Redirect (MFAWEB): the sign-in page and the code step go to `state.from` only when it starts
     with `/` and not `//` or `/\`, else `/projects`. Flow:
     `sign-in goes on only to the app's own pages` (a `from` of `//example.test` lands on
     `/projects`).
   - Test: `tests/test_vapt_headers.py::test_4_headers_python_guards_and_redirects`.
5. Authenticator codes (MFA, MFAPY, MFAWEB, ENFORCE).
   - Pinned endpoints and codes. The web uses the `qrcode` package (exact version, at least two
     weeks old) to draw the `otpauthUrl` as an image in the browser, and shows the secret as text
     for typing in.
   - Screens, as `docs/design/FORGE-VAPT-1/` shows them: the two-step section of Settings
     (`/settings/two-step`): off, set-up (QR code, secret, code field), recovery codes shown once,
     on (with Turn off for members, which asks for the password and a code; for admins "Required
     for admins"); the code step of sign-in (`/sign-in/code`, with "Use a recovery code"); the
     forced set-up for an admin who has no code.
   - API cases: `an admin cannot use the app until they set up a code`;
     `a member turns the code on and off with password and code`;
     `sign-in asks for the code and a code works once`;
     `a recovery code works once`; `a wrong code counts toward the lockout`;
     `a member made admin must set up a code`.
   - Flows: `an admin sets up an authenticator code and saves the recovery codes`;
     `a member signs in with a code`.
   - Test: `tests/test_vapt_codes.py::test_5_admins_need_a_code_and_members_may_use_one`.
6. Nightly scans, existing repos (SCAN, GUIDE).
   - `scripts/security-scan.mjs` in each starter runs, and fails on any finding:
     `corepack pnpm audit --audit-level moderate`; in the Python starter also
     `uv export --frozen --no-dev --no-hashes` into a file and `uvx pip-audit==<pinned> -r <file>`;
     `docker run` of pinned `zricethezav/gitleaks:<version>` `detect --source /repo --redact`
     on the whole history; pinned `semgrep/semgrep:<version>` `semgrep scan --config
     p/owasp-top-ten --error`; pinned `ghcr.io/zaproxy/zaproxy:<version>` `zap-baseline.py -t
     http://production-api:3000 -c /zap/wrk/zap-rules.tsv` on the compose network
     (`${COMPOSE_PROJECT_NAME}_default`), where a WARN or FAIL fails the scan. Pin each tool to an
     exact version at least two weeks old. `.zap/zap-rules.tsv` in each starter lists any rule set
     to IGNORE, each with its reason on the same line; the starters pass the scan with the fewest
     such lines. Each tool prints `security scan: <tool> passed` or `security scan: <tool> found
     problems`, so the failed job names the tool.
   - A failing scan fails the test command, so the full run fails: in CI the scheduled job fails
     and `forge next` shows its `forge fix start` line; in local mode `forge test --full` prints
     it. No new Forge code for the fix.
   - Tests: `tests/test_vapt_scan.py::test_6_the_full_run_runs_the_security_scans`: (a) not live:
     in a new repo with a test command that writes `FORGE_FULL_RUN` to a file, `forge test --full`
     writes `1` and `forge test` writes nothing; (b) live (`FORGE_STARTER_LIVE=1`): the TypeScript
     and Python starters' `node scripts/test.mjs` with `FORGE_FULL_RUN=1` prints the four (Python:
     five) `passed` lines; (c) existing-repo case: the same check (a) on the adopted fixture.
   - `tests/test_vapt_guide.py::test_6_existing_apps_unchanged_and_the_guide_says_how_to_copy`
     (see "New and existing repos").

### New and existing repos

- **New repos** (`forge init --starter`, and `--starter python`): both starters have every check
  of items 1 to 5, the scan script and the ZAP rules file. The guide text arrives with set-up.
  Plain `forge init` gets the text and the `FORGE_FULL_RUN` flag, and no starter code.
- **Existing repos** (on upgrade, after `forge sync`): no app file, migration or script changes.
  They get the `FORGE_FULL_RUN` flag in their full run (their test command ignores it until they
  copy the scan), the `security.md` section "Copy the VAPT checks from the starter", which lists
  each check with the starter files it lives in and the order to copy them, the skill line and
  the guide paragraph.
- **The existing-repo case of each rule.** Each `test_<n>` (1 to 6) runs `adopt_earlier` from
  `tests/test_close_always_tests.py` (the adopted-v1.2.2 fixture synced to this release) and
  checks that sync changed no file outside Forge's own files and that `security.md` names the
  starter files of that rule. One shared helper in `tests/test_vapt_guide.py` does this; each
  test calls it with its rule's file list.

### Skill, brief and guide (GUIDE)

- `src/forge/templates/conventions/security.md`: the checks of items 1 to 5 as rules for both
  stacks (the page is NestJS-first; add the Python line beside each where it differs), the ASVS
  ids, and the copy section for existing apps. It also documents the lockout, session and code
  values (ASVS 6.1.1 and 7.1.1 ask for them in writing).
- `src/forge/templates/skill.md`: one line where the full run is described (about line 1564):
  the full run sets `FORGE_FULL_RUN=1`, and a test command can run slow scans only then; the
  starters run their security scan this way. `docs/guide.md` says the same near line 349.
- `src/forge/templates/brief.md`: one line in the security part: keep the starter's security
  checks; a new sign-in path, password field or cookie follows `security.md`.
- Both starters' `README.md`: the scan, the session and lockout values, and the two-step code.
- `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` are rewritten by
  `forge sync`.

### ASVS 5.0 requirements each check covers

Ids from OWASP ASVS 5.0.0 (tag `v5.0.0_release`, `5.0/en/*.md`), level in brackets.

| Check | ASVS 5.0 ids |
|---|---|
| Same reply and time for every email at sign-in, sign-up and reset | 6.3.8 [L3, asked by the owner] |
| Lockout for each email, per-address limits | 6.1.1 [L1], 6.3.1 [L1] |
| Leaked-password list, offline | 6.2.4 [L1], 6.2.12 [L2] |
| New session at sign-in, old one ended | 7.2.4 [L1] |
| Idle timeout and maximum age, written down | 7.3.1 [L2], 7.3.2 [L2], 7.1.1 [L2] |
| Sign-out and expiry end the session on the server | 7.4.1 [L1] |
| All sessions end on reset; other sessions end on a code change | 7.4.3 [L2] |
| Cookies Secure with `__Host-`, SameSite, HttpOnly | 3.3.1 [L1], 3.3.2 [L2], 3.3.3 [L2], 3.3.4 [L2] |
| HSTS one year with subdomains | 3.4.1 [L1] |
| CSP with `object-src 'none'` and `base-uri 'none'` | 3.4.3 [L2] |
| `X-Content-Type-Options: nosniff` (kept) | 3.4.4 [L1] |
| Referrer-Policy | 3.4.5 [L2] |
| CSP frame-ancestors | 3.4.6 [L2] |
| No version headers | 13.4.6 [L3, asked by the owner] |
| Permissions-Policy | no ASVS 5.0 id; asked by the owner for the VAPT test |
| Form-forgery guard on every state-changing route | 3.5.1 [L1], 3.3.2 [L2] |
| Redirects only to the app's own pages | 3.7.2 [L2] |
| Authenticator code for admins, optional for members | 6.3.3 [L2] (members optional: written down in security.md as the owner's choice) |
| Each code and recovery code works once | 6.5.1 [L2] |
| Recovery codes of 120 bits, hashed | 6.5.2 [L2] |
| Secrets and codes from the CSPRNG | 6.5.3 [L2] |
| TOTP step of 30 seconds | 6.5.5 [L2] |
| Turn off needs the password and a code | 7.5.1 [L2] |
| Reset does not skip the code | 6.4.3 [L2] |
| Failed sign-ins logged | 16.3.1 [L2] |
| Role changes and invites logged | 16.3.3 [L2] |
| No personal data or secrets in logs | 16.2.5 [L2] |
| Event lines with when, who, what in UTC | 16.2.1 [L2], 16.2.2 [L2] |
| Package audit each night | 15.2.1 [L1] |
| gitleaks, semgrep, ZAP baseline each night | no single id; they check 13.3.1 [L2], 1.x and 3.4.x findings |

## Tasks

<!-- One row per task. Covers: the Done-when numbers it delivers, at most three. Scope: the paths
it may change. Tests: the tests it adds or changes. After: the tasks it waits for. When two tasks
share a function, field, file format or command, the first task pins it: it commits the shared
names and stubs plus one test that crosses both sides, and the tasks that use it list it under
After. Split tasks so each owns its files; shared lines (command table, guide list, registry) go
to one task or a small last wiring task; After only when a task needs another task's code. The
Developer column is optional: the lead fills or changes a GitHub username here, below For the
builders, without another approval. Leave it blank for an unassigned part. Forge next uses
the caller's GitHub login; another developer may start it with a warning. Existing tables
without Developer still work. The moving-parts line stays last: "none", or each new dependency, service, datastore,
queue, background job or abstraction layer, with the Done-when item that needs it. -->

| ID | Name | What it delivers | Covers | Scope | Tests | After | User-facing | Developer |
|---|---|---|---|---|---|---|---|---|
| SIGNIN | Sign-in, reset and events in the TypeScript API | `SecurityEvents`, the dummy-hash sign-in, the email lockout table, the leaked-password check and list, forgot password that replies first, and the role and invite events | 1, 2 | `starter/libs/core/src/common/security-events.ts` (new), `starter/libs/core/src/common/common.module.ts`, `starter/libs/core/src/index.ts`, `starter/libs/auth/src/auth.service.ts`, `starter/libs/auth/src/leaked-passwords.txt` (new), `starter/libs/organisations/src/organisations.service.ts`, `starter/apps/api/prisma/schema/auth.prisma`, `starter/apps/api/prisma/migrations/<next>_sign_in_lockouts/` (new), `starter/apps/api/test/accounts.e2e-spec.ts` (new) | `tests/test_vapt_accounts.py` (`test_1`, `test_2`, TS names, new) | FORGE-SINGLECO-1/COMPANYAPI, FORGE-FEATURE-1/ACCESS, FORGE-DATABASE-1/IDS | no | |
| SIGNINPY | Sign-in, reset and events in the Python API | The same contract as SIGNIN in the Python starter, with the reset reply in a background task | 1, 2 | `starter-python/apps/api/app/core/security_events.py` (new), `starter-python/apps/api/app/core/__init__.py`, `starter-python/apps/api/app/auth/service.py`, `starter-python/apps/api/app/auth/routes.py`, `starter-python/apps/api/app/auth/models.py`, `starter-python/apps/api/app/auth/leaked_passwords.txt` (new), `starter-python/apps/api/app/organisations/service.py`, `starter-python/apps/api/migrations/versions/<next>_sign_in_lockouts.py` (new), `starter-python/apps/api/tests/test_accounts.py` (new), `tests/test_vapt_accounts.py` (Python names only) | the Python twins of the SIGNIN cases | SIGNIN, FORGE-SINGLECO-1/COMPANYPY, FORGE-FEATURE-1/ACCESS, FORGE-DATABASE-1/IDSPY | no | |
| HEADERS | Security headers and the Python guards | Permissions-Policy and `base-uri 'none'` in both APIs, no server header from uvicorn, the general Python limit, and the form-forgery check in Python's `current_account` | 4 | `starter/apps/api/src/main.ts`, `starter-python/apps/api/app/core/security.py`, `starter-python/apps/api/app/core/admin.py`, `starter-python/apps/api/app/auth/routes.py` and `__init__.py` (`require_csrf` out), `starter-python/apps/api/app/projects/routes.py` (`require_csrf` out), `starter-python/Dockerfile`, `starter/apps/api/test/headers.e2e-spec.ts` (new), `starter-python/apps/api/tests/test_headers.py` (new) | `tests/test_vapt_headers.py` (`test_4`, new) | SIGNINPY | no | |
| SESSIONS | Session limits and cookies in the TypeScript API | Idle and maximum age, `lastSeenAtUtc`, the replaced session ended at sign-in, the `__Host-` names in production, and the web cookie read that works with both APIs | 3 | `starter/libs/auth/src/auth.service.ts`, `starter/libs/auth/src/auth.controller.ts`, `starter/libs/auth/src/session.guard.ts`, `starter/apps/api/prisma/schema/auth.prisma`, `starter/apps/api/prisma/migrations/<next>_session_last_seen/` (new), `starter/apps/web/src/lib/api-client.ts`, `starter/apps/api/test/helpers.ts` (cookie names), `starter/apps/api/test/sessions.e2e-spec.ts` (new) | `tests/test_vapt_sessions.py` (`test_3`, TS names, new) | SIGNIN | no | |
| SESSIONSPY | Session limits and cookies in the Python API | The same contract as SESSIONS in the Python starter | 3 | `starter-python/apps/api/app/auth/service.py`, `starter-python/apps/api/app/auth/routes.py`, `starter-python/apps/api/app/auth/models.py`, `starter-python/apps/api/migrations/versions/<next>_session_last_seen.py` (new), `starter-python/apps/api/tests/conftest.py` (cookie names), `starter-python/apps/api/tests/test_sessions.py` (new), `tests/test_vapt_sessions.py` (Python names only) | the Python twins of the SESSIONS cases | SESSIONS, HEADERS | no | |
| SIGNUP | Sign-up from an emailed link in the TypeScript API | `sign-up/start` and `sign-up/finish`, the sign-up token table, the two mail methods, the shared schemas, and a `signUp` helper that every API test uses; the old route stays | 1 | `starter/libs/auth/src/auth.service.ts`, `starter/libs/auth/src/auth.controller.ts`, `starter/libs/core/src/mail/mail.provider.ts`, `starter/libs/shared/src/index.ts`, `starter/apps/api/prisma/schema/auth.prisma`, `starter/apps/api/prisma/migrations/<next>_sign_up_tokens/` (new), `starter/apps/api/test/helpers.ts`, `starter/apps/api/test/*.e2e-spec.ts` (sign-up calls to the helper only), `starter/apps/api/test/accounts.e2e-spec.ts` | `tests/test_vapt_accounts.py` (`test_1` sign-up names) | SESSIONS | no | |
| SIGNUPPY | Sign-up from an emailed link in the Python API | The same contract as SIGNUP in the Python starter | 1 | `starter-python/apps/api/app/auth/service.py`, `starter-python/apps/api/app/auth/routes.py`, `starter-python/apps/api/app/auth/schema.py`, `starter-python/apps/api/app/auth/models.py`, `starter-python/apps/api/app/core/mail.py`, `starter-python/apps/api/migrations/versions/<next>_sign_up_tokens.py` (new), `starter-python/apps/api/tests/conftest.py` and `tests/test_*.py` (sign-up calls to the helper only), `starter-python/libs/shared/**` (copy and regenerated types), `tests/test_vapt_accounts.py` (Python names only) | the Python twins of the SIGNUP cases | SIGNUP, SESSIONSPY | no | |
| SIGNUPWEB | Sign-up screens | The email-only sign-up form with its "Check your email" state, the finish sign-up page and route, the hook, the e2e helper, and the old `POST /auth/sign-up` deleted from both APIs | 1 | `starter/apps/web/src/features/auth/pages/sign-up-page.tsx`, `starter/apps/web/src/features/auth/pages/finish-sign-up-page.tsx` (new), `starter/apps/web/src/features/auth/hooks/auth-hooks.ts`, `starter/apps/web/src/app.tsx`, `starter/apps/web/e2e/helpers.ts`, `starter/apps/web/e2e/sign-up.spec.ts` (new), `starter/libs/auth/src/auth.controller.ts` and `auth.service.ts` (old route out), `starter-python/apps/api/app/auth/routes.py` and `service.py` (old route out), `starter-python/libs/shared/**` (regenerated types) | the flow `a person signs up from the emailed link` in both live runs, required by `test_1` | SIGNUPPY, FORGE-SINGLECO-1/COMPANYWEB | yes | |
| MFA | Authenticator codes in the TypeScript API | TOTP and recovery codes, the pending sign-in, the code, setup, confirm and disable routes, the `/auth/me` fields and the code events; no enforcement yet | 5 | `starter/libs/auth/src/totp.ts` (new), `starter/libs/auth/src/mfa.controller.ts` (new), `starter/libs/auth/src/auth.service.ts`, `starter/libs/auth/src/auth.controller.ts`, `starter/libs/auth/src/auth.module.ts`, `starter/libs/shared/src/index.ts`, `starter/apps/api/prisma/schema/auth.prisma`, `starter/apps/api/prisma/migrations/<next>_mfa/` (new), `starter/apps/api/test/codes.e2e-spec.ts` (new) | `tests/test_vapt_codes.py` (`test_5`, TS names, new) | SIGNUP | no | |
| MFAPY | Authenticator codes in the Python API | The same contract as MFA in the Python starter | 5 | `starter-python/apps/api/app/auth/totp.py` (new), `starter-python/apps/api/app/auth/service.py`, `starter-python/apps/api/app/auth/routes.py`, `starter-python/apps/api/app/auth/schema.py`, `starter-python/apps/api/app/auth/models.py`, `starter-python/apps/api/migrations/versions/<next>_mfa.py` (new), `starter-python/apps/api/tests/test_codes.py` (new), `starter-python/libs/shared/**` (copy and regenerated types), `tests/test_vapt_codes.py` (Python names only) | the Python twins of the MFA cases | MFA, SIGNUPPY | no | |
| MFAWEB | Two-step screens | The two-step section of Settings with the QR code, recovery codes and turn off; the code step of sign-in; sign-in that goes on only to the app's own pages; the `qrcode` package | 4, 5 | `starter/apps/web/src/features/auth/pages/two-step-page.tsx` (new), `starter/apps/web/src/features/auth/pages/sign-in-code-page.tsx` (new), `starter/apps/web/src/features/auth/pages/sign-in-page.tsx`, `starter/apps/web/src/features/auth/hooks/auth-hooks.ts`, `starter/apps/web/src/features/settings/pages/settings-page.tsx` (link only), `starter/apps/web/src/app.tsx`, `starter/apps/web/package.json`, `starter/package.json`, `starter-python/package.json`, both `pnpm-lock.yaml`, `starter/apps/web/e2e/two-step.spec.ts` (new) | the flows `a member signs in with a code` and `sign-in goes on only to the app's own pages` in both live runs, required by `test_4` and `test_5` | MFAPY, SIGNUPWEB | yes | |
| ENFORCE | Admins must set up a code | The guard rule in both APIs, the web redirect to set-up, and the test helpers that set up the code for each new admin | 5 | `starter/libs/auth/src/session.guard.ts`, `starter-python/apps/api/app/auth/routes.py` (`current_account` only), `starter/apps/web/src/app.tsx` (protected layout only), `starter/apps/api/test/helpers.ts`, `starter-python/apps/api/tests/conftest.py`, `starter/apps/web/e2e/helpers.ts`, `starter/apps/api/test/codes.e2e-spec.ts`, `starter-python/apps/api/tests/test_codes.py`, `starter/apps/web/e2e/two-step.spec.ts` | the enforcement cases and the flow `an admin sets up an authenticator code and saves the recovery codes` in both live runs, required by `test_5` | MFAWEB | yes | |
| SCAN | Nightly security scans | `FORGE_FULL_RUN` in the full run, the scan script and ZAP rules file in each starter, and the scan step in each starter's test script | 6 | `src/forge/fullrun.py` (one line), `starter/scripts/security-scan.mjs` (new), `starter/scripts/test.mjs`, `starter/.zap/zap-rules.tsv` (new), `starter-python/scripts/security-scan.mjs` (new), `starter-python/scripts/test.mjs`, `starter-python/.zap/zap-rules.tsv` (new), `tests/test_starter_tree.py` and `tests/test_python_starter.py` (file lists only) | `tests/test_vapt_scan.py` (`test_6`, new) | HEADERS, FORGE-SINGLECO-1/COMPANYAPI, FORGE-SINGLECO-1/COMPANYPY, FORGE-DATABASE-1/PG18 | no | |
| GUIDE | Security guide for new and existing apps | The `security.md` checks, values, ASVS ids and copy section; the skill, brief and guide lines; both READMEs; the existing-repo helper | 6 | `src/forge/templates/conventions/security.md`, `src/forge/templates/skill.md`, `src/forge/templates/brief.md`, `docs/guide.md`, `.claude/skills/forge/SKILL.md` and `.codex/skills/forge/SKILL.md` (rewritten by `forge sync`), `starter/README.md`, `starter-python/README.md` | `tests/test_vapt_guide.py` (`test_6` and the shared existing-repo helper, new) | SCAN, ENFORCE | no | |

New moving parts: the `qrcode` npm package in the web app, to draw the set-up QR code (item 5); pinned gitleaks, semgrep and ZAP Docker images and pip-audit through `uvx`, run only in the nightly full run (item 6). The TOTP code uses the standard library; the leaked-password list is a data file in each API.

## Notes

- **Order.** SIGNIN first: it pins the security event and the lockout, and it waits for the
  in-flight parts that change the same auth files (FORGE-SINGLECO-1/COMPANYAPI, approved and
  building; FORGE-FEATURE-1/ACCESS, which adds `permissions` in `libs/auth/**`; FORGE-DATABASE-1/IDS,
  which changes id lines in `auth.service.ts`). If one of those stories is dropped or not approved
  when SIGNIN starts, the lead removes its After line here and plans against main. Then the
  chain runs TypeScript before Python for each contract (SIGNIN, SESSIONS, SIGNUP, MFA), because
  the TypeScript part pins it. HEADERS runs beside SESSIONS after SIGNINPY (it shares Python's
  `routes.py`). SCAN runs beside the auth chain after HEADERS. GUIDE is last.
- **Why the web parts wait for both APIs.** The Python starter runs every Playwright spec in
  `apps/web` against its own API. So SIGNUPWEB, MFAWEB and ENFORCE merge only when both APIs
  serve their contract. SIGNUP and MFA add routes and keep the old replies, so the web keeps
  working between parts. ENFORCE is its own part because it changes every suite's sign-up helper.
- **Migrations.** Each part names its migration after the newest one on main when it starts
  (Prisma folders by date, Alembic by the next number), because FORGE-FEATURE-1 and
  FORGE-DATABASE-1 also add migrations.
- **Part sizes.** About five code files in each part, as the owner asked. Test files, the
  migration and the regenerated Python API types come on top. HEADERS touches both APIs because
  each change there is a few lines and no web code.
- **Not in this story (owner's rule: only the listed checks).** These ASVS 5.0 Level 2 checks
  stay open, listed for the owner: 6.2.2 and 6.2.3 (a change-password screen that asks for the
  current password; today only reset changes it), 6.1.2 and 6.2.11 (a list of words of the
  client's business refused in passwords), 7.4.5 and 7.5.2 (screens to see and end sessions),
  13.4.5 (the API docs page at `/api/docs` stays on in production), 16.4.2 and 16.4.3 (logs sent
  to a separate store; that is the host's job). Also not in this story: encrypting the TOTP
  secret at rest, email verification beyond sign-up, and a screen for an admin to turn off another
  person's code.
- **Changes the flow by one flag.** `FORGE_FULL_RUN=1` is new for every repo's full run; the
  skill and guide lines say so. No command, option or `forge.toml` setting changes.
- No client repo is named anywhere in this story's code, tests, texts or commits.
