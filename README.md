# gbot-slack

Tiny Python 3 CLI so any agent can send and receive Slack messages **as itself** through its own Slack bot app.

This is a shared adapter: one Slack app per agent identity, tokens supplied by the operator and kept local. Agent-agnostic. No telemetry. No hardcoded workspace IDs.

- **v1** — poll/read + send over the Slack Web API (stdlib only)
- **v2** — adds Socket Mode `listen`, emoji `react` / `unreact`, and assistant `thinking` status without breaking v1 commands

## Requirements

- Python 3.8+
- A Slack **bot token** (`xoxb-…`) for the agent’s own Slack app
- For `listen` only: a Slack **app-level token** (`xapp-…`) with `connections:write`, plus `pip install websockets`

`whoami` / `send` / `history` / `dms` / `mentions` / `channels` / `react` / `unreact` / `thinking` stay **stdlib-only**. `gbot-slack --help` works with no pip deps and no token.

## Install

```bash
git clone https://github.com/bcharleson/gbot-slack.git
cd gbot-slack
chmod +x gbot-slack
export PATH="$PWD:$PATH"
gbot-slack --help
```

Optional (Socket Mode listen only):

```bash
pip install websockets
```

## Create a Slack app (from scratch)

1. Open [https://api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.
2. Name the app for this agent identity (one Slack app per agent).
3. Pick the workspace where the agent should speak.
4. **OAuth & Permissions** → **Bot Token Scopes** → add:

   - `chat:write`
   - `chat:write.public`
   - `channels:read`
   - `channels:join`
   - `channels:history`
   - `groups:read`
   - `groups:history`
   - `im:history`
   - `im:write`
   - `mpim:history`
   - `mpim:write`
   - `users:read`
   - `app_mentions:read`
   - `reactions:write`
   - `reactions:read` (optional; only if you later read reactions)

5. **Install to Workspace** and approve. After adding scopes later, **reinstall** the app so the bot token picks them up.
6. Copy the **Bot User OAuth Token** (starts with `xoxb-`) into a local secret store only — never commit it.

Optional: under **App Home**, enable the bot user if prompted by Slack’s UI.

### Socket Mode (for `listen`)

1. In app settings → **Socket Mode** → **Enable Socket Mode**.
2. **Basic Information** → **App-level tokens** → generate a token with scope `connections:write` (starts with `xapp-`). Keep it local; never commit it.
3. **Event Subscriptions** → enable events and subscribe the bot to at least:

   - `message.im`
   - `app_mention`
   - `message.channels`
   - `message.groups`
   - `message.mpim`

   With Socket Mode on there is **no public Request URL** — the WebSocket replaces it.

## Put tokens where the CLI can read them

### Bot token (`xoxb-…`)

Resolution order:

1. `SLACK_BOT_TOKEN` environment variable
2. `GBOT_SLACK_TOKEN_FILE` environment variable pointing at a local file path you choose
3. Default file: `~/.config/gbot-slack/bot-token`

```bash
export SLACK_BOT_TOKEN='xoxb-your-bot-token'
# or
mkdir -p ~/.config/gbot-slack
chmod 700 ~/.config/gbot-slack
printf '%s\n' 'xoxb-your-bot-token' > ~/.config/gbot-slack/bot-token
chmod 600 ~/.config/gbot-slack/bot-token
```

### App-level token (`xapp-…`, listen only)

Resolution order:

1. `SLACK_APP_TOKEN` environment variable
2. `GBOT_SLACK_APP_TOKEN_FILE` environment variable pointing at a local file path you choose
3. Default file: `~/.config/gbot-slack/app-token`

```bash
export SLACK_APP_TOKEN='xapp-your-app-token'
# or
printf '%s\n' 'xapp-your-app-token' > ~/.config/gbot-slack/app-token
chmod 600 ~/.config/gbot-slack/app-token
```

`.gitignore` ignores `.env`, `*.token`, `bot-token`, `app-token`, `.config/`, and similar credential paths. Do not commit tokens.

## Invite the bot

For private channels (and often for reliable history and reactions), invite the bot:

```text
/invite @YourBotName
```

Public channels may be addressable with `chat:write.public`, but membership still matters for history and event delivery.

## Commands

| Command | Slack API | Purpose |
| --- | --- | --- |
| `gbot-slack whoami` | `auth.test` | Show bot identity |
| `gbot-slack send CHANNEL message...` | `chat.postMessage` | Post as the bot |
| `gbot-slack history CHANNEL [limit]` | `conversations.history` | Recent messages (default limit 20) |
| `gbot-slack dms [limit]` | `conversations.list` + `conversations.history` | IM list with last message |
| `gbot-slack mentions [limit]` | `search.messages` (best effort) | Mentions of the bot |
| `gbot-slack channels` | `conversations.list` | Conversations the bot can see |
| `gbot-slack react CHANNEL TS EMOJI` | `reactions.add` | Add emoji reaction |
| `gbot-slack unreact CHANNEL TS EMOJI` | `reactions.remove` | Remove emoji reaction |
| `gbot-slack thinking CHANNEL THREAD_TS [status...]` | `assistant.threads.setStatus` | Assistant “thinking” status |
| `gbot-slack listen [--once]` | Socket Mode (`apps.connections.open` + WebSocket) | Stream message events as JSON lines |

`CHANNEL` may be a Slack ID (`C…` / `D…` / `G…`) or a `#name` the bot can see.

### React / unreact

```bash
gbot-slack react CHANNEL TS eyes
gbot-slack unreact CHANNEL TS white_check_mark
```

`EMOJI` is the name **without** colons (leading/trailing colons are stripped if present). Needs `reactions:write`.

### Thinking status

Uses Slack’s modern assistant thread status (`assistant.threads.setStatus`), **not** the deprecated RTM “user is typing” bubble.

- Default status if omitted: `is thinking...`
- Pass an empty status string to clear: `gbot-slack thinking CHANNEL THREAD_TS ""`
- Optional rotating loading lines: `--loading "…"` (repeatable, max 10)

```bash
gbot-slack thinking CHANNEL THREAD_TS
gbot-slack thinking CHANNEL THREAD_TS is drafting a reply...
gbot-slack thinking CHANNEL THREAD_TS --loading "checking notes..." --loading "almost done..."
gbot-slack thinking CHANNEL THREAD_TS ""
```

Scope: `chat:write` is enough per Slack’s 2026 changelog. `assistant:write` is optional/legacy and will stop being accepted for this method.

### Listen (Socket Mode)

```bash
pip install websockets   # once, for listen only
gbot-slack listen        # stream until SIGINT
gbot-slack listen --once # exit after first user message / app_mention
```

Each interesting event is one JSON object on stdout with `type`, `channel`, `user`, `ts`, `text`, and `thread_ts`. Envelopes are always acknowledged; `hello` / retries are ignored for printing. `--once` lets a host agent wake, handle one event, and restart.

If `websockets` is not installed, `listen` exits with a clear error pointing at `pip install websockets`.

### Mentions note

`mentions` calls `search.messages`. Many bot tokens cannot use search (missing scope or token type). Prefer `gbot-slack listen` for live mentions, or:

- invite the bot into channels of interest
- poll with `gbot-slack history CHANNEL [limit]`
- discover rooms with `gbot-slack channels` / `gbot-slack dms`

`search:read` is intentionally not in the default scope list.

## Versioning

v1 was poll/send. This release adds v2 `listen` / `react` / `thinking` without removing or renaming v1 commands. Stdlib commands still need no pip packages.

## License

MIT — see [LICENSE](LICENSE).
