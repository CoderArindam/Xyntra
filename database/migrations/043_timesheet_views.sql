-- 043_timesheet_views.sql
-- Enterprise Timesheet System Canonical Views

-- 1. v_timesheets_canonical
CREATE OR REPLACE VIEW v_timesheets_canonical AS
SELECT 
  t.id,
  t.org_id,
  t.user_id,
  t.week_start_date,
  t.week_end_date,
  t.status,
  t.total_hours,
  t.submitted_at,
  t.reviewed_at,
  t.approver_id,
  t.approver_comment,
  t.member_note,
  t.created_at,
  t.updated_at,
  COALESCE(NULLIF(TRIM(CONCAT(u.first_name, ' ', u.last_name)), ''), u.email) AS submitter_name, 
  u.email AS submitter_email,
  COALESCE(NULLIF(TRIM(CONCAT(a.first_name, ' ', a.last_name)), ''), a.email) AS approver_name, 
  a.email AS approver_email,
  COALESCE(p.week_start_day, 'monday'::week_start_day) AS week_start_day, 
  COALESCE(p.standard_hours_per_week, 40.00) AS standard_hours_per_week, 
  COALESCE(p.standard_hours_per_day, 8.00) AS standard_hours_per_day,
  COALESCE(p.overtime_policy, 'flag_only'::overtime_policy) AS overtime_policy, 
  COALESCE(p.allow_member_recall, true) AS allow_member_recall,
  COUNT(e.id)::INTEGER AS entry_count
FROM timesheets t
JOIN users u ON (u.id::text = t.user_id::text OR u.id::text = LTRIM(RIGHT(t.user_id::text, 12), '0') OR u.email = t.user_id::text)
LEFT JOIN users a ON (a.id::text = t.approver_id::text OR a.id::text = LTRIM(RIGHT(t.approver_id::text, 12), '0') OR a.email = t.approver_id::text)
LEFT JOIN timesheet_policies p ON (p.org_id::text = t.org_id::text OR LTRIM(RIGHT(p.org_id::text, 12), '0') = LTRIM(RIGHT(t.org_id::text, 12), '0'))
LEFT JOIN timesheet_entries e ON e.timesheet_id = t.id
GROUP BY 
  t.id, t.org_id, t.user_id, t.week_start_date, t.week_end_date, t.status, t.total_hours, 
  t.submitted_at, t.reviewed_at, t.approver_id, t.approver_comment, t.member_note, t.created_at, t.updated_at,
  u.first_name, u.last_name, u.email, 
  a.first_name, a.last_name, a.email, 
  p.week_start_day, p.standard_hours_per_week, p.standard_hours_per_day, p.overtime_policy, p.allow_member_recall;


-- 2. v_timesheet_entries_canonical
CREATE OR REPLACE VIEW v_timesheet_entries_canonical AS
SELECT 
  e.id,
  e.timesheet_id,
  e.user_id,
  e.board_id,
  e.task_id,
  e.entry_date,
  e.hours,
  e.entry_type,
  e.description,
  e.is_overtime,
  e.created_at,
  e.updated_at,
  b.name AS board_name,
  tk.title AS task_title,
  t.week_start_date, 
  t.week_end_date, 
  t.status AS timesheet_status
FROM timesheet_entries e
JOIN timesheets t ON t.id = e.timesheet_id
LEFT JOIN boards b ON (b.id::text = e.board_id::text OR b.id::text = LTRIM(RIGHT(e.board_id::text, 12), '0') OR e.board_id::text = LTRIM(RIGHT(b.id::text, 12), '0'))
LEFT JOIN tasks tk ON (tk.id::text = e.task_id::text OR tk.id::text = LTRIM(RIGHT(e.task_id::text, 12), '0') OR e.task_id::text = LTRIM(RIGHT(tk.id::text, 12), '0'));



-- 3. v_timesheet_audit_canonical
CREATE OR REPLACE VIEW v_timesheet_audit_canonical AS
SELECT 
  ta.id,
  ta.timesheet_id,
  ta.actor_user_id,
  ta.from_status,
  ta.to_status,
  ta.comment,
  ta.ip_address,
  ta.user_agent,
  ta.created_at,
  COALESCE(NULLIF(TRIM(CONCAT(u.first_name, ' ', u.last_name)), ''), u.email) AS actor_name, 
  u.email AS actor_email,
  t.user_id AS owner_user_id, 
  t.week_start_date
FROM timesheet_audit_log ta
JOIN users u ON (u.id::text = ta.actor_user_id::text OR u.id::text = LTRIM(RIGHT(ta.actor_user_id::text, 12), '0') OR u.email = ta.actor_user_id::text)
JOIN timesheets t ON t.id = ta.timesheet_id;


-- 4. v_timesheet_approver_assignments_canonical
DROP VIEW IF EXISTS v_timesheet_approver_assignments_canonical CASCADE;
CREATE OR REPLACE VIEW v_timesheet_approver_assignments_canonical AS
SELECT 
  taa.id,
  taa.org_id,
  taa.approver_user_id,
  taa.assigned_by,
  taa.is_active,
  taa.created_at,
  COALESCE(NULLIF(TRIM(CONCAT(u.first_name, ' ', u.last_name)), ''), u.email) AS approver_name, 
  u.email AS approver_email,
  COALESCE(NULLIF(TRIM(CONCAT(ab.first_name, ' ', ab.last_name)), ''), ab.email) AS assigned_by_name
FROM timesheet_approver_assignments taa
JOIN users u ON (u.id::text = taa.approver_user_id::text OR u.id::text = LTRIM(RIGHT(taa.approver_user_id::text, 12), '0') OR u.email = taa.approver_user_id::text)
JOIN users ab ON (ab.id::text = taa.assigned_by::text OR ab.id::text = LTRIM(RIGHT(taa.assigned_by::text, 12), '0') OR ab.email = taa.assigned_by::text)
WHERE taa.is_active = true;


-- 5. v_timesheet_policy_canonical
CREATE OR REPLACE VIEW v_timesheet_policy_canonical AS
SELECT 
  tp.id,
  tp.org_id,
  tp.week_start_day,
  tp.standard_hours_per_day,
  tp.standard_hours_per_week,
  tp.max_hours_per_day,
  tp.overtime_policy,
  tp.submission_deadline_days,
  tp.allow_future_entry,
  tp.allow_past_entry_days,
  tp.require_task_link,
  tp.allow_member_recall,
  tp.created_at,
  tp.updated_at,
  o.name AS org_name, 
  LOWER(REGEXP_REPLACE(o.name, '\s+', '-', 'g')) AS org_slug
FROM timesheet_policies tp
JOIN organizations o ON (o.id::text = tp.org_id::text OR o.id::text = LTRIM(RIGHT(tp.org_id::text, 12), '0') OR LOWER(REGEXP_REPLACE(o.name, '\s+', '-', 'g')) = tp.org_id::text);
