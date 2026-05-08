import time

import streamlit as st

from enrollment_starter import (
    CURRENT_STUDENT,
    EnrollmentService,
    SQLiteEnrollmentRepository,
    STATUS_ENROLLED,
    STATUS_UNENROLLED,
)

PAGE_DASHBOARD = "dashboard"
PAGE_SELECTED_CLASS = "selected_class"
ROLE_STUDENT = "student"


def initialize_session_state() -> None:
    if "role" not in st.session_state:
        st.session_state.role = ROLE_STUDENT
    if "page" not in st.session_state:
        st.session_state.page = PAGE_DASHBOARD
    if "selected_class_id" not in st.session_state:
        st.session_state.selected_class_id = None
    if "enrollment_key_input" not in st.session_state:
        st.session_state.enrollment_key_input = ""
    if "feedback_message" not in st.session_state:
        st.session_state.feedback_message = ""
    if "feedback_type" not in st.session_state:
        st.session_state.feedback_type = ""
    if "feedback_timestamp" not in st.session_state:
        st.session_state.feedback_timestamp = 0.0


def set_feedback(message: str, message_type: str = "success") -> None:
    st.session_state.feedback_message = message
    st.session_state.feedback_type = message_type
    st.session_state.feedback_timestamp = time.time()


def render_feedback() -> None:
    if not st.session_state.feedback_message:
        return

    if st.session_state.feedback_type == "success":
        st.success(st.session_state.feedback_message)
    else:
        st.warning(st.session_state.feedback_message)

    time.sleep(2)
    st.session_state.feedback_message = ""
    st.session_state.feedback_type = ""
    st.session_state.feedback_timestamp = 0.0


def get_enrolled_course_options(service: EnrollmentService, user_id: str) -> tuple[list[str], dict[str, str]]:
    enrolled_courses = service.get_student_enrollments(user_id)
    course_options: dict[str, str] = {}
    for course in enrolled_courses:
        label = f"{course['course_id']} - {course['course_name']}"
        course_options[label] = course["course_id"]

    if not course_options:
        course_options["No enrolled classes available"] = ""

    return list(course_options.keys()), course_options


def render_dashboard(service: EnrollmentService, user_id: str, email: str) -> None:
    st.title("Student Dashboard")
    st.write(f"**Student:** {CURRENT_STUDENT['name']}  \\**Role:** {st.session_state.role}")

    with st.container():
        st.subheader("Enroll in a class")
        with st.form("enrollment_form"):
            enrollment_key = st.text_input(
                "Enter enrollment key",
                value=st.session_state.enrollment_key_input,
                placeholder="Example: MISY350-SPRING",
            )
            enroll_submit = st.form_submit_button("Enroll")

        st.session_state.enrollment_key_input = enrollment_key

        if enroll_submit:
            if not enrollment_key.strip():
                set_feedback("Please enter a valid enrollment key.", "warning")
            else:
                enrolled = service.enroll_with_key(user_id, email, enrollment_key)
                if enrolled:
                    set_feedback(
                        f"Successfully enrolled in {enrolled['course_id']}.",
                        "success",
                    )
                    st.session_state.enrollment_key_input = ""
                else:
                    set_feedback(
                        "Enrollment failed. Check the enrollment key and try again.",
                        "warning",
                    )

    with st.container():
        st.subheader("Current enrollment")
        option_labels, course_options = get_enrolled_course_options(service, user_id)
        selected_label = st.selectbox("Choose enrolled class", option_labels)
        selected_course_id = course_options.get(selected_label, "")

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("Go to class"):
                if selected_course_id:
                    st.session_state.selected_class_id = selected_course_id
                    st.session_state.page = PAGE_SELECTED_CLASS
                    st.experimental_rerun()
                else:
                    set_feedback("Select a class before navigating to it.", "warning")

        with button_col2:
            if st.button("Unenroll"):
                if selected_course_id:
                    success = service.soft_unenroll_student(user_id, selected_course_id)
                    if success:
                        set_feedback(
                            f"You have been unenrolled from {selected_course_id}.",
                            "success",
                        )
                    else:
                        set_feedback(
                            "Unable to unenroll from the selected class.",
                            "warning",
                        )
                else:
                    set_feedback("Select a class before attempting to unenroll.", "warning")

    with st.container():
        st.subheader("Student summary")
        summary = service.get_student_summary(user_id)
        st.metric("Enrolled", summary.get(STATUS_ENROLLED, 0))
        st.metric("Unenrolled", summary.get(STATUS_UNENROLLED, 0))
        st.metric("Total records", summary.get("total_records", 0))

    with st.container():
        st.subheader("Enrollment history")
        history = service.get_student_enrollment_history(user_id)
        if history:
            st.dataframe(history)
        else:
            st.info("No enrollment history is available for this student.")


def render_selected_class_page(service: EnrollmentService, user_id: str) -> None:
    selected_course_id = st.session_state.selected_class_id
    if not selected_course_id:
        set_feedback("No class is selected. Returning to the dashboard.", "warning")
        st.session_state.page = PAGE_DASHBOARD
        st.experimental_rerun()

    course_record = service.get_student_course_record(user_id, selected_course_id)
    if not course_record:
        set_feedback("Selected class data could not be found.", "warning")
        st.session_state.page = PAGE_DASHBOARD
        st.experimental_rerun()

    st.title("Selected Class")
    st.write(f"**Student:** {CURRENT_STUDENT['name']}  \\**Role:** {st.session_state.role}")
    st.markdown(f"### {course_record['course_id']} - {course_record['course_name']}")

    class_data = [
        {
            "Course ID": course_record["course_id"],
            "Course Name": course_record["course_name"],
            "Instructor": course_record["instructor"],
            "Status": course_record["status"],
            "Enrolled At": course_record["enrolled_at"],
        }
    ]
    st.dataframe(class_data)

    with st.form("unenroll_form"):
        submit_unenroll = st.form_submit_button("Unenroll from this class")

    if submit_unenroll:
        success = service.soft_unenroll_student(user_id, selected_course_id)
        if success:
            set_feedback(
                f"You have been unenrolled from {selected_course_id}.",
                "success",
            )
            st.session_state.page = PAGE_DASHBOARD
            st.experimental_rerun()
        else:
            set_feedback(
                "Unable to unenroll from this class.",
                "warning",
            )

    if st.button("Back to dashboard"):
        st.session_state.page = PAGE_DASHBOARD
        st.experimental_rerun()


def main() -> None:
    st.set_page_config(page_title="Student Enrollment Portal")
    initialize_session_state()

    repository = SQLiteEnrollmentRepository()
    repository.create_tables()
    repository.seed_sample_data()
    service = EnrollmentService(repository)

    render_feedback()

    user_id = CURRENT_STUDENT["user_id"]
    email = CURRENT_STUDENT["email"]

    if st.session_state.page == PAGE_DASHBOARD:
        render_dashboard(service, user_id, email)
    else:
        render_selected_class_page(service, user_id)


if __name__ == "__main__":
    main()
