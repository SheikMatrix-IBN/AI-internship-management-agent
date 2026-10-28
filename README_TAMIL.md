# AI Internship Management Agent — Starter

## என்ன இதில் வேலை செய்கிறது?
- Student registration
- Task creation and assignment
- AI task explanation
- Text-to-speech playback inside the dashboard
- Transcript + submission evidence based review draft
- Human approval before saving/sending
- Gmail email sending using OAuth
- Google Calendar event + Meet link request
- PostgreSQL-compatible SQLAlchemy models; SQLite local default
- Email log and review history

## முக்கிய limitation
இந்த starter Google Meet-க்குள் AI participant ஆக join ஆகாது. Google Meet Media API currently no longer accepts new signups according to Google developer docs. AI voice is played in the dashboard. Meet participant functionality requires an eligible supported integration or a third-party meeting-bot service.

## Windows setup
1. Install Python 3.12+ and (for production) PostgreSQL.
2. Open PowerShell in this folder:
   ```powershell
   python -m venv .venv
   .venv\\Scripts\\activate
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```
3. Edit `.env` and add your OpenAI API key. Use a model available to your API account.
4. Run:
   ```powershell
   streamlit run app.py
   ```
5. For Google email/calendar:
   - In Google Cloud Console, enable Gmail API and Calendar API.
   - Configure OAuth consent screen.
   - Create OAuth Desktop client and save as `credentials.json`.
   - The first Google action opens a browser for authorization.
6. Test with your own email before real students.

## Important production tasks still required
- Add login, role-based access control, CSRF-safe deployment, HTTPS, rate limiting.
- Use PostgreSQL and database migrations (Alembic).
- Run reminders in a separate durable worker/queue; implement retry + idempotency.
- Do not expose Streamlit directly to the public internet without authentication.
- Add CSV import, bulk task assignment, calendar collision detection and email delivery monitoring.
- Configure OAuth scopes carefully and review Google verification requirements before external production use.
- Obtain consent before recording/transcribing meetings.
- Keep human mentor approval for scoring and feedback.
- `worker.py` scans approved reviews due within 24 hours and sends reminder emails using `email_logs` to avoid repeat sends. Test thoroughly; production should use a durable queue and robust idempotency keys.
