# Security Policy

## Supported Versions

Currently, only the `main` branch (V3.6 Integration) is actively supported for security updates. 

| Version | Supported          |
| ------- | ------------------ |
| v3.6.x  | :white_check_mark: |
| < v3.6  | :x:                |

## Reporting a Vulnerability

If you discover any security vulnerability in the Thronos Discord Bot, **please do not report it through public GitHub issues.** 

Instead, please send an email directly to the core development team at `security@thronoschain.org` (or the equivalent maintainer email). We will review the submission within 48 hours.

## Credential Safety

If you are a contributor running the bot locally:
- **Never** commit your `.env` file or SQLite `data/thronos.db` database. 
- Ensure that the `.gitignore` correctly ignores these sensitive files before pushing upstream.
- Thronos Ecosystem APIs do not log user wallet private keys; the `!bind` command requires public addresses only. Never request private keys from users inside Discord.
