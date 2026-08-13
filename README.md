# gbot-slack

Tiny Python 3 CLI so any Grok Bot (or similar) agent can send and receive Slack messages **as itself** through its own Slack bot app.

This is a shared adapter: one Slack app per agent identity, bot token supplied by the operator, Web API only. No pip dependencies. No telemetry. No hardcoded workspace IDs.

## Requirements

- Python 3.8+
- A Slack bot token for the agent’s own Slack app

## Install

```bash
git clone https://github.com/bcharleson/gbot-slack.git
cd gbot-slack
chmod +x gbot-slack
export PATH="$PWD:$PATH"
gbot-slack --help
```

`gbot-slack --help` works without a token.

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

5. **Install to Workspace** and approve.
6. Copy the **Bot User OAuth Token** (starts with `xoxb-`) into a local secret store only — never commit it.

Optional: under **App Home**, enable the bot user if prompted by Slack’s UI.

## Put the token where the CLI can read it

Resolution order:

1. `SLACK_BOT_TOKEN` environment variable
2. `GBOT_SLACK_TOKEN_FILE` environment variable pointing at a local file path you choose
3. Default file: `~/.config/gbot-slack/bot-token`

Examples (local machine only):

```bash
export SLACK_BOT_TOKEN='xoxb-your-bot-token'
# or
mkdir -p ~/.config/gbot-slack
chmod 700 ~/.config/gbot-slack
printf '%s\n' 'xoxb-your-bot-token' > ~/.config/gbot-slack/bot-token
chmod 600 ~/.config/gbot-slack/bot-token
```

`.gitignore` ignores `.env`, `*.token`, `bot-token`, `.config/`, and similar credential paths. Do not commit tokens.

## Invite the bot

For private channels (and often for reliable history), invite the bot:

```text
/invite @YourBotName
```

Public channels may be addressable with `chat:write.public`, but membership still matters for history and mentions workflows.

## Commands

| Command | Slack API | Purpose |
| --- | --- | --- |
| `gbot-slack whoami` | `auth.test` | Show bot identity |
| `gbot-slack send CHANNEL message...` | `chat.postMessage` | Post as the bot |
| `gbot-slack history CHANNEL [limit]` | `conversations.history` | Recent messages (default limit 20) |
| `gbot-slack dms [limit]` | `conversations.list` + `conversations.history` | IM list with last message |
| `gbot-slack mentions [limit]` | `search.messages` (best effort) | Mentions of the bot |
| `gbot-slack channels` | `conversations.list` | Conversations the bot can see |

`CHANNEL` may be a Slack ID (`C…` / `D…` / `G…`) or a `#name` the bot can see.

### Mentions note

`mentions` calls `search.messages`. Many bot tokens cannot use search (missing scope or token type). If that fails, the CLI exits with a short message and suggests:

- invite the bot into channels of interest
- poll with `gbot-slack history CHANNEL [limit]`
- discover rooms with `gbot-slack channels` / `gbot-slack dms`

`search:read` is intentionally not in the default v1 scope list; agents are expected to poll history.

## v1 scope

v1 is **poll/read + send** over the Slack Web API so any agent can shell out to this CLI without a public URL.

Socket Mode and the Events API are out of scope for v1.

## License

MIT — see [LICENSE](LICENSE).
