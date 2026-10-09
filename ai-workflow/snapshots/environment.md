# Relevant environment and permissions — sanitized summary

- Workspace: the assignment repository. Local environment/DB/cache files are ignored.
- Shell: zsh on macOS; an isolated Python runtime was installed for this task.
- Git metadata and network operations required scoped execution approval in the coding tool.
  The initial sandbox allowed workspace writes but treated Git metadata as read-only.
- uv, GitHub CLI, and Gitleaks were installed from Homebrew for the approved task.
- GitHub CLI sign-in was completed by the user. Token/keychain values are not exported.
  Git identity is repository-local; no global AI settings were changed.
- Model credential is supplied by `MODEL_API_KEY`, excluded from public settings and Git.
- Application runtime uses HTTPX directly, with a fixed Cohere endpoint and no model tools.
- Codex app tools attached created PRs. Browser tooling inspected the localhost interface.
- No application MCP server, external messaging integration, AI hook, or cloud resource was added.
- Provider-managed coding-tool permissions and hidden instructions cannot be exported as files;
  this summary records observable exercise-relevant behavior without privileged prompt contents.
- No passwords, tokens, personal settings, private configuration URLs, or full chat logs are copied.
