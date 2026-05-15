# Input: sdlc-init / personal-todo-app

## Initial state
- Greenfield project. No `docs/`, no `src/`, no `README.md`.
- User runs `/sdlc-init` in a fresh chat.

## Interview answers (one per question, in order)

1. **What is the product name and what problem does it solve?**
   > "Personal Todo. People keep TODOs in scattered notes apps and forget them. This is a single per-user list with reminders, hosted self-serve."

2. **Who are the target users and what are their primary goals?**
   > "Individuals (not teams). Primary goal: capture tasks fast and not lose them."

3. **What does success look like — functionally, non-functionally, and for the business?**
   > "Functional: a user can add a task and see it on another device within 5s. Non-functional: P95 page load < 1.5s, no data loss. Business: at least 100 weekly-active users in 3 months."

4. **What is explicitly in scope, and what is explicitly out of scope?**
   > "In: per-user list, due dates, reminders by email. Out: collaboration/sharing, mobile native app, integrations (Slack/etc)."

5. **Who are the key stakeholders and what is each one's interest?**
   > "Me (solo dev) — ship and learn. Hypothetical end users — reliability over features."

6. **What technology stack do you plan to use?**
   > "Python + FastAPI + SQLite for v1. HTMX for the UI. Deployed on a single VPS."

7. **Are there any architectural constraints or non-negotiables?**
   > "No paid services. No JavaScript framework (HTMX only). Single binary deploy if possible."

8. **How is quality measured?**
   > "Pytest for unit + integration. Manual smoke test before deploy. No formal SLOs yet."

9. **What environments will exist?**
   > "Just dev (laptop) and prod (VPS). No staging."
