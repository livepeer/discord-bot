# Contributing

Thanks for helping improve the Discord moderation bot and community rules.

## Improving moderation rules

The rules in [`rules.md`](rules.md) are injected into the classifier prompt at startup. If a message is flagged incorrectly, or if a message should have been flagged but was not, please help improve the rules with a clear report and a proposed fix.

### When to open an issue

Open an issue when you have a concrete moderation example, such as:

- **False positive:** a message was flagged but should have been allowed.
- **False negative:** a message was not flagged but should have been flagged.
- **Ambiguous rule behavior:** the current rules do not make the expected decision clear.

Please include evidence, not just a conclusion. A useful issue should include:

1. The exact message text, or a redacted version that preserves the moderation-relevant wording.
2. Any needed conversation context, ideally the few messages before it.
3. What happened: flagged or not flagged.
4. What you expected instead.
5. Why, with references to the relevant section of `rules.md`.
6. A suggested rule change, if you have one.

Do not include private information, secrets, or unrelated personal details. Redact usernames or sensitive text when needed, while keeping enough context to understand the moderation call.

### Pull requests for rule fixes

After opening an issue, a fix can be proposed with a pull request that updates `rules.md`.

A good PR should:

- Link the issue it addresses, e.g. `Fixes #123`.
- Explain the false positive / false negative case.
- Keep the rule change as narrow as possible.
- Preserve the existing distinction between criticism of ideas/organizations and attacks on people or protected identities.
- Avoid adding one-off wording that only handles a single example unless that wording generalizes clearly.
- Update docs/tests only when the behavior or code changes require it.

Before a moderation rule PR is merged, at least two other known community members must review it, approve it, and comment their support on the PR.

## Code changes

For code changes, keep the bot lean and fail-open:

- Do not log API keys, Discord tokens, bearer headers, or full `.env` contents.
- Keep BlueClaw/API errors fail-open so the bot does not spam or block on provider failures.
- Add or update tests for parsing, prompt payloads, and formatting behavior.
- Run the test suite before submitting:

```bash
python -m py_compile bot.py moderation.py formatting.py tests/*.py
python tests/_run.py
```

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` locally. Never commit real secrets.
