"""Create a secure local environment without overwriting an existing .env."""
from pathlib import Path
import secrets

root=Path(__file__).resolve().parents[1]
target=root/'.env'
if target.exists():
    print('Existing .env preserved. Verify configured secrets and PBI_E2E_PASSWORD before bootstrap.')
else:
    text=(root/'.env.example').read_text()
    replacements={
        'replace-with-a-long-random-secret-at-least-32-characters':secrets.token_urlsafe(48),
        'replace-with-a-separate-one-time-random-secret':secrets.token_urlsafe(48),
        'replace-with-a-different-random-secret-at-least-32-characters':secrets.token_urlsafe(48),
        'optional-local-smoke-test-password-of-12-or-more-characters':secrets.token_urlsafe(24),
    }
    for old,new in replacements.items():text=text.replace(old,new)
    target.write_text(text);target.chmod(0o600)
    print('Created .env with unique local secrets. The local demo password is stored in PBI_E2E_PASSWORD; keep it private.')
