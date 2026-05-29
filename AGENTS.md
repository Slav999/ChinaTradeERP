# Project instructions for Codex

## Project stack

- Backend: Django + Django REST Framework.
- Frontend: Vue + Bootstrap.
- Database: PostgreSQL in Docker.
- Do not modify production settings unless explicitly asked.

## Working rules

- Before big changes, first make a short plan.
- Make small, safe changes.
- Do not delete existing business logic.
- Do not rewrite the whole project unless explicitly asked.
- After edits, summarize changed files and what should be tested.

## Backend rules

- Check serializers, views, urls, permissions, and models together.
- Do not break authentication, email verification, JWT, password reset, throttling, or role logic.
- Run migrations only when model changes require it.

## Frontend rules

- Keep the existing Bootstrap style.
- Do not change the whole UI design unless asked.
- Prefer small component-level fixes.

## Useful commands

- Run backend: python manage.py runserver
- Make migrations: python manage.py makemigrations
- Apply migrations: python manage.py migrate
- Run tests: python manage.py test

## Frontend checks

- Do not run full frontend build after every small edit.
- For small UI or text changes, only update the code and summarize what changed.
- Run `npm run build` only after completing a meaningful frontend task or when checking compilation.
- Before running long commands, explain why they are needed.
