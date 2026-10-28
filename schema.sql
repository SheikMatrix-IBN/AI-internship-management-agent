-- Reference schema. app.py creates equivalent tables through SQLAlchemy.
CREATE TABLE students (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(320) NOT NULL UNIQUE,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE tasks (
  id BIGSERIAL PRIMARY KEY,
  student_id BIGINT NOT NULL REFERENCES students(id),
  title VARCHAR(250) NOT NULL,
  description TEXT NOT NULL,
  deadline DATE NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'Assigned',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE reviews (
  id BIGSERIAL PRIMARY KEY,
  task_id BIGINT NOT NULL REFERENCES tasks(id),
  review_number INTEGER NOT NULL,
  transcript TEXT NOT NULL,
  submission_evidence TEXT NOT NULL,
  feedback TEXT NOT NULL,
  score INTEGER,
  next_review_at TIMESTAMP,
  meeting_link TEXT,
  approved BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE email_logs (
  id BIGSERIAL PRIMARY KEY,
  recipient VARCHAR(320) NOT NULL,
  subject VARCHAR(300) NOT NULL,
  status VARCHAR(40) NOT NULL,
  provider_id VARCHAR(300),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
