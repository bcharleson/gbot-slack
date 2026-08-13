# gbot-slack

Tiny Python 3 CLI so a **host agent** can send and receive Slack messages **as itself** through its own Slack bot app.

**gbot-slack does not think.** The host agent thinks. This repo is only an external **channel adapter** (a transport): it owns the Slack connection, filters noise, emits inbound events, and posts outbound messages the host already decided to send. It does **not** add an agent runtime, LLM calls, session memory, or an OpenClaw-style “gateway invokes the model.” Slack (and similar surfaces such as Teams or WhatsApp) are transports; the host agent is what responds.

This is a shared, org-agnostic adapter: one Slack app per agent identity, tokens supplied by the operator and kept local. No telemetry. No hardcoded workspace IDs. No client-specific data in the repo.

- **v1** — poll/read + send over the Slack Web API (stdlib only)
- **v2** — Socket Mode `listen`, emoji `react` / `unreact`, and assistant `thinking` status (Slack UI status text — not model inference)
- **v3** — `gateway`: single-instance Socket Mode channel transport for turn-based hosts (ignore self/bot echoes, reconnect until a human event, optional webhook / allowlist)

## Requirements

- Python 3.8+
- A Slack **bot token** for the agent’s own Slack app
- For `gateway` / `listen`: a Slack **app-level token** with `connections:write`, plus `pip install websockets`

`whoami` / `send` / `history` / `dms` / `mentions` / `channels` / `react` / `unreact` / `thinking` stay **stdlib-only**. `gbot-slack --help` works with no pip deps and no token.

## Install

```bash
git clone https://github.com/bcharleson/gbot-slack.git
cd gbot-slack
chmod +x gbot-slack
export PATH="$PWD:$PATH"
gbot-slack --help
gbot-slack --version
```

Optional (Socket Mode `gateway` / `listen`):

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
6. Copy the **Bot User OAuth Token** into a local secret store only — never commit it.

Optional: under **App Home**, enable the bot user if prompted by Slack’s UI.

### Socket Mode (for `gateway` / `listen`)

1. In app settings → **Socket Mode** → **Enable Socket Mode**.
2. **Basic Information** → **App-level tokens** → generate a token with scope `connections:write`. Keep it local; never commit it.
3. **Event Subscriptions** → enable events and subscribe the bot to at least:

   - `message.im`
   - `app_mention`
   - `message.channels`
   - `message.groups`
   - `message.mpim`

   If you use Slack Agent / Assistant DMs, also subscribe to:

   - `assistant_thread_started`
   - `assistant_thread_context_changed`

   With Socket Mode on there is **no public Request URL** — the WebSocket replaces it.

## Put tokens where the CLI can read them

### Bot token

Resolution order:

1. `SLACK_BOT_TOKEN` environment variable
2. `GBOT_SLACK_TOKEN_FILE` environment variable pointing at a local file path you choose
3. Default file: `~/.config/gbot-slack/bot-token`

```bash
export SLACK_BOT_TOKEN='…'   # bot token from your Slack app install
# or
mkdir -p ~/.config/gbot-slack
chmod 700 ~/.config/gbot-slack
printf '%s\n' '…' > ~/.config/gbot-slack/bot-token
chmod 600 ~/.config/gbot-slack/bot-token
```

### App-level token (`gateway` / `listen`)

Resolution order:

1. `SLACK_APP_TOKEN` environment variable
2. `GBOT_SLACK_APP_TOKEN_FILE` environment variable pointing at a local file path you choose
3. Default file: `~/.config/gbot-slack/app-token`

```bash
export SLACK_APP_TOKEN='…'   # app-level token with connections:write
# or
printf '%s\n' '…' > ~/.config/gbot-slack/app-token
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
| `gbot-slack gateway [--once] …` | Socket Mode (`apps.connections.open` + WebSocket) | **Two-way receive path** — human events as JSON |
| `gbot-slack listen [--once]` | Socket Mode | Same receive loop as gateway (minimal flags); prefer `gateway` |

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

### Gateway (Socket Mode — inbound transport)

`gateway` owns the Slack WebSocket, filters bot echoes and other noise, and either exits on the first human message (`--once`) or stays up and forwards events (`--webhook` and/or stdout stream). It never calls a model.

```bash
pip install websockets   # once, for gateway/listen
gbot-slack gateway --once
gbot-slack gateway --webhook http://127.0.0.1:8080/slack-event
gbot-slack gateway --allow-from U01234567 --allow-from U89ABCDEF
gbot-slack gateway --events-log ~/.config/gbot-slack/events.log
```

**Turn-based host pattern:** run `gbot-slack gateway --once`. When it prints one JSON object and exits 0, the **existing host agent** wakes on process exit, decides what to say (that logic stays in the host — not here), replies with the outbound CLI (`gbot-slack send` / `react` / `thinking`), then starts `gateway --once` again.

Inbound = this CLI. Outbound = this CLI. Reasoning = the host agent only.

Unlike gateways that invoke the model inside the channel process, **gbot-slack only moves bytes on the wire**: emit JSON (or POST `--webhook`), then get out of the way.

Each human event is one JSON object on stdout with `type`, `event_type`, `channel`, `user`, `ts`, `text`, and `thread_ts`. Behavior that matters in production:

- Ignores the bot’s own posts (Events API echo often has `type=message`, no subtype, `user` = the bot’s user id, sometimes `bot_id`).
- Ignores any event with `bot_id`.
- Keeps DM thread replies (`message` + `thread_ts`, no subtype).
- Wakes on `assistant_thread_started` when a user id is present.
- Logs unknown Events API types to stderr; never logs tokens.
- Reconnects on WebSocket `ConnectionClosed` or Slack `disconnect` — `--once` does **not** exit until a human event is actually received (or SIGINT/SIGTERM).
- Single-instance lock via `~/.config/gbot-slack/gateway.pid`. Slack load-balances Socket Mode across connections; a second `gateway`/`listen` exits with a clear error until you stop the other process.
- SIGINT/SIGTERM: remove the pidfile and exit 0.

### Listen (Socket Mode)

```bash
gbot-slack listen        # stream until SIGINT
gbot-slack listen --once # exit after first human event (same filters / reconnect as gateway)
```

`listen` shares the ignore-self / ignore-bot / reconnect / pidfile behavior with `gateway`. Prefer `gateway` when you need `--webhook`, `--allow-from`, or `--events-log`.

If `websockets` is not installed, `gateway` / `listen` exit with a clear error pointing at `pip install websockets`.

### Mentions note

`mentions` calls `search.messages`. Many bot tokens cannot use search (missing scope or token type). Prefer `gbot-slack gateway` (or `listen`) for live mentions, or:

- invite the bot into channels of interest
- poll with `gbot-slack history CHANNEL [limit]`
- discover rooms with `gbot-slack channels` / `gbot-slack dms`

`search:read` is intentionally not in the default scope list.

## Tests

```bash
python3 -m unittest test_gbot_slack.py
```

## Versioning

v1 was poll/send. v2 added `listen` / `react` / `thinking`. This release is **v3** (`gbot-slack --version`): `gateway` as the durable inbound transport, with listen fixed to the same human-event filters. Still transport-only — no agent runtime. Stdlib commands still need no pip packages.

## License

MIT — see [LICENSE](LICENSE).
