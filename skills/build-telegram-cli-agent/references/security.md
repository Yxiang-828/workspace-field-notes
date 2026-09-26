# Security And Stop Rules

Telegram-to-CLI bots bridge chat input into local machine execution. Treat that as high risk.

## Secret Handling

- Never print or quote values from `.env`, process env, or `C:/Users/xiang/.alibaba/keys.env`.
- Log env variable names only.
- Redact values for keys containing `TOKEN`, `KEY`, `SECRET`, `PASSWORD`, or `PAT`.
- Keep `.env` gitignored.
- Prefer project `.env` for app-specific values and shared keys for reusable machine credentials.

## Command Execution

- Use argv arrays and `shell=False`.
- Ask before enabling shell strings, PowerShell expressions, or user-editable command templates.
- Validate `cwd` exists.
- Use timeouts.
- Save stdout/stderr to task logs, but send only redacted summaries to Telegram.
- Do not allow non-owner users to change the command, cwd, env, model, or worker.

## Access Gates

- Require `OWNER_TELEGRAM_ID` for any owner-only command.
- Allow the owner everywhere.
- For non-owner access, require explicit user or chat allowlisting.
- In groups, require bot mention or reply unless the bot is intentionally a room listener.
- If added to an unknown group by a non-owner, ignore or leave depending on the project requirement.

## Mutation Gates

If the CLI pipeline can change files, repositories, cloud resources, deployments, accounts, or payments:

- Make owner approval explicit.
- Separate read-only checks from mutating commands.
- Return a proposed plan instead of mutating when approval is missing.
- Never push, deploy, delete, rotate secrets, or alter remote state because a non-owner asked in Telegram.

## Stop And Ask

Stop and ask the user instead of building on weak input when:

- The user asks for a custom/nonstandard CLI pipeline but does not specify the command.
- The bot token is missing.
- The owner id is missing and owner-only controls are required.
- Group privacy requirements are ambiguous.
- The requested bot would expose arbitrary command execution to unknown users.
- The user asks to paste or handle tokens in chat.
