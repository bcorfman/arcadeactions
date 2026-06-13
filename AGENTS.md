Read before coding:
- Follow docs in order: `docs/prd.md` -> `docs/api_usage_guide.md` -> `docs/testing_guide.md`.
- Refer to `/docs` for any context or patterns before implementation.

Design priorities (in order): dev experience, simplicity, fit with underlying APIs, API quality, testability, best practices.

Structure/complexity:
- Keep modules around ~500 lines and functions around ~20 cyclomatic complexity.
- Split modules/functions intelligently to avoid high complexity or large files.
- If splitting would reduce clarity, ask for a decision before doing it.

Hard rules:
- Avoid dataclasses unless there is a clear, documented benefit.
- Avoid runtime type/attribute checks (hasattr/getattr/isinstance/EAFP-with-pass).
- No silent EAFP; `except AttributeError: pass` is forbidden.
- Use `uv run python` (never plain `python`).
- Define and use explicit Protocols/adapters for sprite/window/action interfaces; validate at boundaries instead of ad-hoc attribute probes.

Dependency/testability:
- Accept dependencies via constructors; avoid hidden instantiation inside methods.
- Avoid circular dependencies.
- Prefer composition over inheritance for dependencies.

E2E verification (required when fixing failures):
- When addressing an E2E failure (local or CI), re-run E2E locally for the browser/project(s) that failed (e.g. Playwright `--project=<name>` / `PW_PROJECT=<name>`), not just a default browser.
- If you can’t run the failing browser(s) locally, explicitly state why and run the closest equivalent verification (and call out the remaining risk).
