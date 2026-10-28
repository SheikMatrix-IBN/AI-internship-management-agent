import os
from datetime import date, datetime, time, timedelta
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, String, Text, Date, DateTime, ForeignKey, Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from ai_service import explain_task, review_submission
from google_services import send_email, create_meet_event

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./internship.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), default="Assigned")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    review_number: Mapped[int] = mapped_column(Integer)
    transcript: Mapped[str] = mapped_column(Text)
    submission_evidence: Mapped[str] = mapped_column(Text)
    feedback: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    approved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    recipient: Mapped[str] = mapped_column(String(320), index=True)
    subject: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), default="sent")
    provider_id: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

st.set_page_config(page_title="Internship AI Agent", layout="wide")
st.title("AI Internship Management Agent")
st.caption("Full-system starter • 50–100 students • Human approval for evaluations")

with SessionLocal() as db:
    students = db.scalars(select(Student).where(Student.active == True).order_by(Student.name)).all()
    tasks = db.scalars(select(Task).order_by(Task.id.desc())).all()
    reviews = db.scalars(select(Review).order_by(Review.id.desc())).all()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active students", len(students))
    c2.metric("Tasks", len(tasks))
    c3.metric("Reviews", len(reviews))
    c4.metric("Pending tasks", sum(t.status != "Reviewed" for t in tasks))

tabs = st.tabs(["Students", "Tasks", "AI voice prep", "Review & scheduling", "History"])

with tabs[0]:
    st.subheader("Register student")
    with st.form("student_form", clear_on_submit=True):
        name = st.text_input("Full name")
        email = st.text_input("Email")
        add_student = st.form_submit_button("Add student")
    if add_student:
        if not name.strip() or "@" not in email:
            st.error("Enter a name and valid email.")
        else:
            with SessionLocal() as db:
                exists = db.scalar(select(Student).where(Student.email == email.strip().lower()))
                if exists:
                    st.error("Email already exists.")
                else:
                    db.add(Student(name=name.strip(), email=email.strip().lower()))
                    db.commit()
                    st.success("Student added.")
                    st.rerun()
    with SessionLocal() as db:
        rows = db.scalars(select(Student).order_by(Student.name)).all()
        st.dataframe([{"ID": x.id, "Name": x.name, "Email": x.email, "Active": x.active} for x in rows],
                     use_container_width=True)

with tabs[1]:
    st.subheader("Create and assign task")
    with SessionLocal() as db:
        students = db.scalars(select(Student).where(Student.active == True).order_by(Student.name)).all()
    if not students:
        st.info("Add at least one student first.")
    else:
        student_options = {f"{s.name} — {s.email}": s.id for s in students}
        with st.form("task_form", clear_on_submit=True):
            selected = st.selectbox("Student", list(student_options))
            title = st.text_input("Task title")
            description = st.text_area("Task description and acceptance criteria", height=140)
            deadline = st.date_input("Deadline", value=date.today() + timedelta(days=7))
            create_task = st.form_submit_button("Create task")
        if create_task:
            if not title.strip() or not description.strip():
                st.error("Task title and description are required.")
            else:
                with SessionLocal() as db:
                    task = Task(student_id=student_options[selected], title=title.strip(),
                                description=description.strip(), deadline=deadline)
                    db.add(task)
                    db.commit()
                    task_id = task.id
                st.success(f"Task #{task_id} created.")
    st.subheader("Send task email")
    with SessionLocal() as db:
        tasks = db.scalars(select(Task).order_by(Task.id.desc())).all()
        student_lookup = {s.id: s for s in db.scalars(select(Student)).all()}
        task_options = {f"#{t.id} | {student_lookup[t.student_id].name} | {t.title}": t.id for t in tasks}
    if task_options:
        task_label = st.selectbox("Choose task to email", list(task_options), key="email_task")
        if st.button("Send task email"):
            with SessionLocal() as db:
                task = db.get(Task, task_options[task_label])
                student = db.get(Student, task.student_id)
                subject = f"Internship task: {task.title}"
                body = (f"Hello {student.name},\n\nTask: {task.title}\n\n"
                        f"Instructions:\n{task.description}\n\nDeadline: {task.deadline}\n\n"
                        "Your review invitation will be sent separately.")
                try:
                    provider_id = send_email(student.email, subject, body)
                    db.add(EmailLog(recipient=student.email, subject=subject, status="sent", provider_id=provider_id))
                    db.commit()
                    st.success("Task email sent.")
                except Exception as exc:
                    db.add(EmailLog(recipient=student.email, subject=subject, status="failed"))
                    db.commit()
                    st.error(f"Email failed. Check Google OAuth setup. Details: {exc}")
    with SessionLocal() as db:
        rows = db.scalars(select(Task).order_by(Task.id.desc())).all()
        lookup = {s.id: s.name for s in db.scalars(select(Student)).all()}
        st.dataframe([{"ID": t.id, "Student": lookup.get(t.student_id), "Task": t.title,
                       "Deadline": str(t.deadline), "Status": t.status} for t in rows],
                     use_container_width=True)

with tabs[2]:
    st.subheader("AI task explanation and voice")
    with SessionLocal() as db:
        tasks = db.scalars(select(Task).order_by(Task.id.desc())).all()
        students = {s.id: s.name for s in db.scalars(select(Student)).all()}
    task_options = {f"#{t.id} | {students.get(t.student_id)} | {t.title}": t.id for t in tasks}
    if not task_options:
        st.info("Create a task first.")
    else:
        chosen = st.selectbox("Task", list(task_options), key="explain_task")
        if st.button("Generate explanation"):
            with SessionLocal() as db:
                task = db.get(Task, task_options[chosen])
                try:
                    st.session_state["task_explanation"] = explain_task(task.title, task.description, str(task.deadline))
                except Exception as exc:
                    st.error(f"AI failed: {exc}")
        explanation = st.session_state.get("task_explanation", "")
        if explanation:
            st.markdown(explanation)
            if st.button("Generate speech audio"):
                try:
                    from openai import OpenAI
                    client = OpenAI()
                    audio = client.audio.speech.create(
                        model=os.getenv("TTS_MODEL", "gpt-4o-mini-tts"),
                        voice=os.getenv("TTS_VOICE", "coral"),
                        input=explanation[:4000],
                    )
                    st.session_state["task_audio"] = audio.read()
                except Exception as exc:
                    st.error(f"Text-to-speech failed: {exc}")
            if st.session_state.get("task_audio"):
                st.audio(st.session_state["task_audio"], format="audio/mp3")
        st.info("Audio plays in this web app; it does not join or speak inside Google Meet.")

with tabs[3]:
    st.subheader("Review analysis")
    with SessionLocal() as db:
        tasks = db.scalars(select(Task).order_by(Task.id.desc())).all()
        student_lookup = {s.id: s for s in db.scalars(select(Student)).all()}
    task_options = {f"#{t.id} | {student_lookup[t.student_id].name} | {t.title}": t.id for t in tasks}
    if not task_options:
        st.info("Create a task first.")
    else:
        chosen = st.selectbox("Reviewed task", list(task_options), key="review_task")
        review_no = st.selectbox("Review number", [1, 2, 3, 4, 5])
        transcript = st.text_area("Paste transcript or student's explanation")
        evidence = st.text_area("Submitted work evidence (tests, report, repo notes)")
        if st.button("Analyze review"):
            if not transcript.strip() or not evidence.strip():
                st.warning("Both transcript and submission evidence are required.")
            else:
                with SessionLocal() as db:
                    task = db.get(Task, task_options[chosen])
                    try:
                        st.session_state["review_feedback"] = review_submission(
                            task.title, task.description, transcript, evidence
                        )
                        st.session_state["review_task_id"] = task.id
                        st.session_state["review_no"] = review_no
                        st.session_state["review_transcript"] = transcript
                        st.session_state["review_evidence"] = evidence
                    except Exception as exc:
                        st.error(f"Review analysis failed: {exc}")
        feedback = st.session_state.get("review_feedback", "")
        if feedback:
            st.markdown("### AI draft — verify before sending")
            st.markdown(feedback)
            next_day = st.date_input("Next review date", value=date.today() + timedelta(days=7))
            next_time = st.time_input("Next review time", value=time(10, 0))
            approved = st.checkbox("I have checked and approve this feedback.")
            if st.button("Save review"):
                if not approved:
                    st.error("Approval is required.")
                else:
                    import re
                    match = re.search(r"(?i)(?:score|mark|rating)\D{0,20}(\d{1,3})\s*(?:/|out of)?\s*100?", feedback)
                    score = min(100, int(match.group(1))) if match else None
                    with SessionLocal() as db:
                        review = Review(
                            task_id=st.session_state["review_task_id"],
                            review_number=st.session_state["review_no"],
                            transcript=st.session_state["review_transcript"],
                            submission_evidence=st.session_state["review_evidence"],
                            feedback=feedback,
                            score=score,
                            next_review_at=datetime.combine(next_day, next_time),
                            approved=True,
                        )
                        db.add(review)
                        task = db.get(Task, st.session_state["review_task_id"])
                        task.status = "Reviewed"
                        db.commit()
                    st.success("Review saved.")
            if st.button("Create next Meet event and email feedback"):
                if not approved:
                    st.error("Approve the feedback first.")
                else:
                    with SessionLocal() as db:
                        task = db.get(Task, st.session_state["review_task_id"])
                        student = db.get(Student, task.student_id)
                        try:
                            start_dt = datetime.combine(next_day, next_time)
                            event = create_meet_event(
                                f"Review {st.session_state['review_no'] + 1}: {task.title}",
                                "Please prepare your updated work and demonstration.",
                                student.email, start_dt
                            )
                            if not event.get("meet_link"):
                                st.error("Meet link is pending. Check Google Calendar before sending the invitation.")
                            else:
                                with SessionLocal() as db2:
                                    saved_review = db2.scalar(
                                        select(Review).where(
                                            Review.task_id == st.session_state["review_task_id"],
                                            Review.review_number == st.session_state["review_no"]
                                        ).order_by(Review.id.desc())
                                    )
                                    if saved_review:
                                        saved_review.meeting_link = event["meet_link"]
                                        db2.commit()
                                subject = f"Review feedback and next meeting: {task.title}"
                                body = (f"Hello {student.name},\n\nFeedback:\n{feedback}\n\n"
                                        f"Next review: {start_dt.strftime('%Y-%m-%d %H:%M')} (Asia/Kolkata)\n"
                                        f"Meet link: {event['meet_link']}\n")
                                provider_id = send_email(student.email, subject, body)
                                with SessionLocal() as db2:
                                    db2.add(EmailLog(recipient=student.email, subject=subject,
                                                     status="sent", provider_id=provider_id))
                                    db2.commit()
                                st.success("Calendar event and feedback email created.")
                        except Exception as exc:
                            st.error(f"Scheduling/email failed: {exc}")

with tabs[4]:
    st.subheader("Review and email history")
    with SessionLocal() as db:
        rows = db.scalars(select(Review).order_by(Review.id.desc())).all()
        task_lookup = {t.id: t for t in db.scalars(select(Task)).all()}
        student_lookup = {s.id: s for s in db.scalars(select(Student)).all()}
        st.dataframe([{
            "Review ID": r.id,
            "Student": student_lookup[task_lookup[r.task_id].student_id].name if r.task_id in task_lookup else "",
            "Task": task_lookup[r.task_id].title if r.task_id in task_lookup else "",
            "Review #": r.review_number,
            "Score": r.score,
            "Next review": str(r.next_review_at or ""),
            "Meet link": r.meeting_link or "",
            "Approved": r.approved
        } for r in rows], use_container_width=True)
        emails = db.scalars(select(EmailLog).order_by(EmailLog.id.desc())).all()
        st.dataframe([{"To": e.recipient, "Subject": e.subject, "Status": e.status,
                       "Provider ID": e.provider_id, "Created": str(e.created_at)} for e in emails],
                     use_container_width=True)
