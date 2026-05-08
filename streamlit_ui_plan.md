# Streamlit UI Implementation Plan

## Goal
Create a Streamlit UI that uses the existing enrollment service layer and seeded student data. The UI should support a student dashboard and a selected class page, with navigation and feedback state managed via `st.session_state`.

## Assumptions
- The student is already logged in as a seeded student named Alice.
- No login, registration, password handling, account creation, or authentication system will be built.
- The UI will rely on the service layer methods:
  - `enroll_with_key(user_id, email, enrollment_key)`
  - `get_dashboard_for_student(user_id)`
  - `get_student_enrollment_history(user_id)`
  - `get_student_summary(user_id)`
  - `soft_unenroll_student(user_id, course_id)`
- The existing backend should remain layered: persistence in the repository, business behavior in the service.

## Entry point and session initialization
1. Create a Streamlit app entrypoint file, e.g. `streamlit_app.py`.
2. Initialize the repository and service at startup.
3. Load the seeded student context for Alice and store her role/page state in `st.session_state`.
4. Session state keys:
   - `role`: `"student"`
   - `page`: `"dashboard"` or `"selected_class"`
   - `selected_class_id`: course id for the selected class
   - `feedback_message`: current message text
   - `feedback_type`: `"success"` or `"warning"`
   - `feedback_timestamp`: timestamp when message was set (for clearing after 2 seconds)
   - `enrollment_key_input`: latest typed enrollment key value

## Page structure

### Student dashboard page
Use `st.container` to separate dashboard UI sections.

Layout:
- Header / welcome text showing Alice and role.
- `st.text_input("Enter enrollment key")` for enrollment key entry.
- `st.select_box("Choose enrolled class", options=enrolled_class_options)` for currently active classes.
- Two buttons:
  - `st.button("Go to class")`
  - `st.button("Unenroll")`
- A status/summary section using the service:
  - `get_student_enrollment_history(user_id)` for history details
  - `get_student_summary(user_id)` for enrolled / unenrolled totals
- A feedback area that renders messages using `st.success` or `st.warning`.

Behavior:
- If the user submits an enrollment key:
  - call `service.enroll_with_key(user_id, email, enrollment_key)`
  - on success, update dashboard state and show `st.success`
  - on failure, show `st.warning`
- If `Go to class` is clicked:
  - ensure a valid selected class exists
  - update `st.session_state.page = "selected_class"`
  - store `st.session_state.selected_class_id`
  - optionally set a success message or clear prior warnings
- If `Unenroll` is clicked from dashboard:
  - call `service.soft_unenroll_student(user_id, course_id)` for the selected class
  - show `st.success` on completion or `st.warning` if invalid
  - refresh the enrolled classes and summary display

### Selected class page
Use `st.container` for page organization.

Layout:
- Header displaying the selected class name and student details.
- `st.dataframe` showing class metadata for the selected course:
  - course id
  - course name
  - instructor
  - enrollment status
  - enrolled at timestamp
- A form using `with st.form("unenroll_form"):` and `st.form_submit_button("Unenroll from this class")`.
- A button or link to return to dashboard if needed.

Behavior:
- When the selected class page loads, read the selected course details from the service layer using `service.get_student_course_record(user_id, course_id)` or `service.get_student_enrollments(user_id)` plus filtering.
- On form submit:
  - call `service.soft_unenroll_student(user_id, course_id)`
  - if successful, set a `st.success` message and navigate back to `dashboard`
  - if failure, set a `st.warning` message and keep the page displayed

## Navigation flow
1. App initializes with `page = "dashboard"` by default.
2. The student dashboard is displayed first.
3. When `Go to class` is clicked, the UI switches to the selected class page.
4. When unenroll completes on either page, the UI returns to the dashboard and refreshes data.
5. The selected class page content should vary depending on the chosen class from dashboard state.

## Feedback and timing
- Use one shared feedback area at the top of the page to show messages.
- Store message text and type in session state.
- After each action, update the feedback in `st.session_state`.
- Plan for a message refresh/clear cycle after two seconds using a small timed rerun strategy.
- Appropriate display logic:
  - `st.success(feedback_message)` when `feedback_type == "success"`
  - `st.warning(feedback_message)` when `feedback_type == "warning"`

## Data and service usage
- Use `service.get_dashboard_for_student(user_id)` to retrieve dashboard data if available; otherwise use the layered service methods to assemble the student view.
- Use `service.get_student_enrollment_history(user_id)` to show history details.
- Use `service.get_student_summary(user_id)` to show the student's enrollment summary.
- Use `service.enroll_with_key(user_id, email, enrollment_key)` for new enrollments.
- Use `service.soft_unenroll_student(user_id, course_id)` to begin the soft unenroll flow.
- Use `service.get_student_course_record(user_id, course_id)` to populate the selected class page.

## Implementation notes
- Do not add authentication or an account management flow.
- Keep all business decisions in the service layer; the Streamlit app only orchestrates interaction and presentation.
- Keep session state minimal but explicit for page navigation and selected class behavior.
- Ensure the selected class page content updates based on actions taken on the dashboard page.
- Keep the dashboard and selected class page clearly separated, with `st.container` used to group controls and results.

## Review checkpoints
- Two pages are clearly defined and navigable.
- `st.session_state` tracks role, page, selected class, and messages.
- Dashboard includes `st.text_input`, `st.select_box`, and two `st.button` controls.
- Selected class page includes `st.dataframe` and `st.form_submit_button`.
- Success/warning flow is defined with timed reset behavior.
- The plan stays within the existing student seed context and avoids building any new authentication layer.