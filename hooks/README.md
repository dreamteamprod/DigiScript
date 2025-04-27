# DigiScript Git Hooks

This directory contains git hooks for the DigiScript repository.

## Available Hooks

- **pre-commit**: Runs linting and formatting on changed files before committing
  - For Python (server) code: runs black, isort, and pylint
  - For JavaScript/Vue (client) code: runs eslint

## Setup

To set up the hooks, run the setup script:

```bash
./hooks/setup-hooks.sh
```

This will create symlinks from the git hooks directory to the hooks in this directory.

## How It Works

The pre-commit hook:

1. Detects which files are staged for commit
2. Runs the appropriate linting and formatting tools on those files
3. Automatically fixes issues when possible and adds the fixed files to the commit
4. Prevents the commit if there are errors that can't be fixed automatically

## Manual Usage

You can also run the hooks manually:

```bash
./hooks/pre-commit
```
