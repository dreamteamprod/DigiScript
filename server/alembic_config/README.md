# Alembic Database Migrations

This directory contains Alembic database migration scripts for DigiScript.

## Migration Revisions

1. **d4f66f58158b** - Initial Alembic Revision
2. **a44e01459595** - Add stage direction styles
3. **a39ac9e9f085** - Add user settings
4. **be353176c064** - Detach users from shows
5. **29471f7cf7d2** - User deletion
6. **a4d42ccfb71a** - Fix session table foreign key reference
7. **7df32f85a5a2** - Add SystemSettings table for JWT secret storage
8. **7fe8320b38c9** - Add interval state to show session
9. **bb9b28a04946** - Rename user_settings table to user_overrides
10. **ff9f875915b6** - Add user settings table
11. **f154c79d86de** - Add cue panel right setting
12. **49df18ea818d** - Add compiled scripts table
13. **8c78b9c89ee6** - Add user last seen time
14. **e1a2b3c4d5e6** - Add user API token
15. **42d0eaa5d07e** - Cleanup orphaned script objects (lines, parts, cuts, cues)
16. **fa8ee07e45fc** - Fix orphaned script revisions
17. **f365c2b2b234** - Add script_mode to show
18. **9f76c42e225e** - Replace stage_direction with line_type enum
19. **4632b14b6e67** - Add session tags and associations
20. **4400e44b4455** - Add script revision association to show session
21. **859636b5ffbb** - Add script text alignment user setting
22. **b5a760d2ee49** - Backfill and set script_text_alignment not null
23. **da55004052c1** - Add requires_password_change to user
24. **01fb1d6c6b08** - Add token_version to user

## Common Commands

```bash
# View migration history
alembic history --verbose

# Create a new migration
alembic revision --autogenerate -m "description"

# Upgrade to latest version
alembic upgrade head

# Downgrade one revision
alembic downgrade -1
```