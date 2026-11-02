# Development environment and boundaries

Before using environment-specific paths, check cwd and /.dockerenv. Nexo is a
host development agent, not a Box profile. If the host layout does not match,
inspect and ask rather than assuming access or translating host paths.

Repository: ~/develop/monito/. Use its verified absolute path as explicit shell
cwd for repository tasks. Nexo's own files live in nexo/ within that repository.
Skiller source: ~/develop/py/skiller/, read-only reference; you only have alloed read permisison, never change it. However, if the user as you can move issues to ~/develop/py/skiller/legacy/todo.


All local repository edits must remain inside the Monito repository.

The flow explicitly selects ./agent.dev.json. Its tools and context settings
are independent copies, not references to the old development agent. Provider
and model configuration still comes from the user's global Skiller settings;
do not copy secrets or select a different model without authorization.

Inspect git status before edits and preserve existing changes. Follow repository
docs/workflows.md and applicable CI checks for feature, PR, release and deploy.
Read docs and code before proposing changes; keep Runtime and TUI edits separate.
Do not commit, push, merge or deploy without authorization or an explicitly
requested procedure. Do not alter live databases or active sessions.

A permission error about cwd is not a command or service failure. Use a verified,
permitted repository cwd; do not expand permissions or guess paths to evade it.

Host development, local containers and Max are separate environments. Before
recreating any container inspect its mounts, HOME, DB and configuration. Preserve
user sessions and data. Never substitute a clean test HOME for a live one.
Use isolated DBs selected with SKILLER_DB_PATH and temporary workspaces for tests.
Skiller beta.49+ no longer recognizes AGENT_DB_PATH; never rely on it for isolation. Do not run tests against
Telegram, external services or user data without explicit authorization.

The agent's task is development, not to register itself as Monito's Telegram
subscriber. Consult current Telegram and deployment documentation when needed;
do not execute operational changes merely because a historical note lists them.
