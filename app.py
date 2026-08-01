
import io
from datetime import datetime
from typing import Dict, List

import streamlit as st
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
)

st.set_page_config(
    page_title="O'Reilly Operations Assistant",
    page_icon="✅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f7f6; }
    .block-container {
        max-width: 760px;
        padding-top: .8rem;
        padding-bottom: 3rem;
    }
    .hero {
        background: linear-gradient(135deg, #0b5d36, #16864f);
        color: white;
        border-radius: 22px;
        padding: 22px;
        margin-bottom: 14px;
        box-shadow: 0 10px 26px rgba(0,0,0,.13);
    }
    .hero h1 { margin: 0; font-size: 1.7rem; line-height: 1.15; }
    .hero p { margin: 8px 0 0 0; opacity: .93; }
    .module-card {
        background: white;
        border-radius: 18px;
        border: 1px solid #e2e7e4;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,.04);
    }
    .status-complete { color: #0b7a42; font-weight: 800; }
    .status-progress { color: #b46a00; font-weight: 800; }
    .status-pending { color: #6b7280; font-weight: 800; }
    .section-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #174b37;
        margin-top: 14px;
        margin-bottom: 8px;
    }
    div.stButton > button, div.stDownloadButton > button {
        width: 100%;
        border-radius: 12px;
        min-height: 46px;
        font-weight: 700;
    }
    [data-testid="stMetricValue"] { font-size: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

SECTIONS = [
    {
        "name": "Prior to Opening",
        "icon": "🌅",
        "tasks": [
            ("Open green bag/file returns manifest", "MT", 2, False),
            ("Print reports", "MT", 5, False),
            ("Count startup tracer bags and safe money; prepare cash drawers", "MT", 20, True),
            ("Verify deposit tracer bags and combine into one deposit", "MT", 20, True),
            ("Verify and process ordered items", "DE", 15, False),
            ("Begin daily returns / credit memo", "DE", 60, False),
        ],
    },
    {
        "name": "Open – 9:00 AM",
        "icon": "🕘",
        "tasks": [
            ("Stock order check-in", "DE", 60, False),
            ("Verify freight over & short and post to inventory", "MT", 15, False),
            ("Send daily/weekly account statements", "MT", 5, False),
            ("Complete and file daily reports", "MT", 15, False),
            ("Update sales goals and complete Image Maker", "MT", 5, True),
            ("Review payroll and approve punches before 10:00 AM", "M", 5, False),
            ("Check Zipline and delegate assignments", "MT", 15, False),
            ("Enter delivery vehicle mileage in Asset Management", "DE", 5, True),
        ],
    },
    {
        "name": "9:00 – 10:00 AM",
        "icon": "📧",
        "tasks": [
            ("Check email", "MT", 5, False),
            ("Walk store aisle by aisle and create team to-do list", "MT", 15, True),
        ],
    },
    {
        "name": "10:00 – 11:00 AM",
        "icon": "🗓️",
        "tasks": [
            ("Work schedule", "MT", 30, False),
        ],
    },
    {
        "name": "11:00 AM – 1:00 PM",
        "icon": "🏦",
        "tasks": [
            ("Take deposit to bank before cutoff", "MT", 30, True),
            ("Verify cash drawers are locked and drops are being made", "MT", 5, True),
        ],
    },
    {
        "name": "2:00 – 3:00 PM",
        "icon": "🔄",
        "tasks": [
            ("Follow up on Zipline and daily assignments", "MT", 15, False),
        ],
    },
    {
        "name": "3:00 – 5:00 PM",
        "icon": "📦",
        "tasks": [
            ("Process outside purchase billing information", "MT", 10, False),
            ("Complete costing by 5:00 PM", "DE", 15, False),
            ("Check email", "MT", 10, False),
            ("Complete returns manifest/outgoing freight and add green bag", "DE", 10, True),
            ("Congratulate team for a job well done", "MT", 5, False),
        ],
    },
    {
        "name": "5:00 PM – Close",
        "icon": "🔒",
        "tasks": [
            ("Verify cash drawers are locked and drops are being made", "MT", 5, True),
            ("Complete Image Maker task", "MT", 10, True),
            ("Verify cash and delivery vehicle keys are locked in safe", "MT", 5, True),
            ("Complete outstanding Image Maker and assigned tasks", "MT", 10, False),
            ("Secure delivery vehicles, park, lock and secure keys", "MT", 5, True),
        ],
    },
    {
        "name": "After Close",
        "icon": "🌙",
        "tasks": [
            ("Ensure coffee pot is unplugged", "DE", 1, True),
            ("Unplug battery chargers", "DE", 1, True),
            ("Run Dayend", "MT", 1, False),
            ("Count remaining drawers, final-count safe and secure all money", "MT", 10, True),
            ("Set alarm before leaving", "MT", 1, True),
        ],
    },
    {
        "name": "End of Day - Store Condition Audit",
        "icon": "📸",
        "tasks": [
            ("Parking Lot", "MT", 3, True),
            ("Trash", "MT", 3, True),
            ("Counter", "MT", 3, True),
            ("Aisle 1", "MT", 3, True),
            ("Aisle 2", "MT", 3, True),
            ("Aisle 3", "MT", 3, True),
            ("Aisle 4", "MT", 3, True),
            ("Aisle 5", "MT", 3, True),
            ("Aisle 6", "MT", 3, True),
            ("Oil Rack", "MT", 3, True),
            ("Battery Rack", "MT", 3, True),
            ("Restroom Mens", "MT", 3, True),
            ("Restroom Womens", "MT", 3, True),
        ],
    },

]

FLAT_TASKS = []
for section in SECTIONS:
    for task in section["tasks"]:
        FLAT_TASKS.append(
            {
                "section": section["name"],
                "icon": section["icon"],
                "task": task[0],
                "owner": task[1],
                "minutes": task[2],
                "photo": task[3],
            }
        )

def init_state() -> None:
    if "manager_name" not in st.session_state:
        st.session_state.manager_name = ""
    if "selected_section" not in st.session_state:
        st.session_state.selected_section = None
    if "task_data" not in st.session_state:
        st.session_state.task_data = {
            i: {
                "done": False,
                "comment": "",
                "photo_bytes": None,
                "completed_at": None,
            }
            for i in range(len(FLAT_TASKS))
        }

def section_counts(section_name: str):
    indexes = [i for i, task in enumerate(FLAT_TASKS) if task["section"] == section_name]
    completed = sum(1 for i in indexes if st.session_state.task_data[i]["done"])
    return completed, len(indexes)

def section_status(section_name: str) -> str:
    completed, total = section_counts(section_name)
    if completed == total:
        return "Complete"
    if completed > 0:
        return "In Progress"
    return "Pending"

def section_status_class(status: str) -> str:
    return {
        "Complete": "status-complete",
        "In Progress": "status-progress",
        "Pending": "status-pending",
    }[status]

def image_for_pdf(photo_bytes: bytes, width: float = 3.0 * inch):
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    image.thumbnail((1100, 850))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=72, optimize=True)
    output.seek(0)
    ratio = image.height / image.width
    return RLImage(output, width=width, height=width * ratio)

def generate_pdf(manager_name: str) -> bytes:
    """
    Generates a maximum 4-page report:
    Page 1: Executive summary and section scores
    Pages 2-3: Detailed tasks
    Page 4: Store Condition Audit photo contact sheet
    """
    output = io.BytesIO()
    styles = getSampleStyleSheet()

    task_style = styles["BodyText"]
    task_style.fontSize = 6.6
    task_style.leading = 7.8

    small_style = styles["BodyText"]
    small_style.fontSize = 6.2
    small_style.leading = 7.2

    section_style = styles["Heading3"]
    section_style.fontSize = 8.8
    section_style.leading = 9.8
    section_style.textColor = colors.HexColor("#0b5d36")
    section_style.spaceBefore = 3
    section_style.spaceAfter = 2

    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=0.24 * inch,
        leftMargin=0.24 * inch,
        topMargin=0.24 * inch,
        bottomMargin=0.24 * inch,
    )

    now = datetime.now()
    completed = sum(
        1 for value in st.session_state.task_data.values() if value["done"]
    )
    total = len(FLAT_TASKS)
    operations_score = completed / total * 100 if total else 0

    audit_indexes_local = [
        i for i, task in enumerate(FLAT_TASKS)
        if task["section"] == "End of Day - Store Condition Audit"
    ]
    audit_completed_local = sum(
        1 for i in audit_indexes_local
        if st.session_state.task_data[i]["done"]
        and st.session_state.task_data[i]["photo_bytes"]
    )
    audit_total_local = len(audit_indexes_local)
    audit_score_local = (
        audit_completed_local / audit_total_local * 100
        if audit_total_local else 0
    )
    overall_score_local = (
        (operations_score + audit_score_local) / 2
        if audit_total_local else operations_score
    )

    story = [
        Paragraph("O'REILLY OPERATIONS ASSISTANT", styles["Title"]),
        Paragraph("Store 4691 - Daily Operations Report", styles["Heading2"]),
        Spacer(1, 5),
    ]

    summary = [
        ["Date", now.strftime("%m/%d/%Y"), "Manager", manager_name or "Not entered"],
        ["Generated", now.strftime("%I:%M %p"), "Overall Score", f"{overall_score_local:.0f}%"],
        ["Operations", f"{operations_score:.0f}%", "Store Condition", f"{audit_score_local:.0f}%"],
        ["Completed", str(completed), "Pending", str(total - completed)],
    ]
    summary_table = Table(
        summary,
        colWidths=[0.85 * inch, 2.15 * inch, 1.05 * inch, 2.65 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8ecea")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#e8ecea")),
                ("FONTSIZE", (0, 0), (-1, -1), 8.1),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 6)])

    section_rows = [["Section", "Completed", "Total", "Score"]]
    for section in SECTIONS:
        done, sec_total = section_counts(section["name"])
        # Store Condition counts only items with both check and photo.
        if section["name"] == "End of Day - Store Condition Audit":
            done = sum(
                1 for i in audit_indexes_local
                if st.session_state.task_data[i]["done"]
                and st.session_state.task_data[i]["photo_bytes"]
            )
        section_rows.append(
            [
                section["name"],
                done,
                sec_total,
                f"{(done / sec_total * 100):.0f}%" if sec_total else "0%",
            ]
        )

    section_table = Table(
        section_rows,
        colWidths=[4.0 * inch, 0.85 * inch, 0.75 * inch, 0.85 * inch],
    )
    section_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b5d36")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7.2),
            ]
        )
    )
    story.extend([section_table, Spacer(1, 5)])

    pending = []
    for i, task in enumerate(FLAT_TASKS):
        data = st.session_state.task_data[i]
        photo_missing = task["photo"] and not data["photo_bytes"]
        if not data["done"] or photo_missing:
            reason = data["comment"] or (
                "Required photo missing" if photo_missing else "No explanation entered"
            )
            pending.append((task["task"], reason))

    story.append(Paragraph("<b>Pending / Exceptions</b>", styles["Heading3"]))
    if not pending:
        story.append(Paragraph("No pending tasks.", styles["BodyText"]))
    else:
        for task_name, note in pending[:8]:
            story.append(Paragraph(f"- {task_name}: {note}", small_style))

    # Pages 2-3: detailed tasks, excluding audit photos from the long task tables.
    story.append(PageBreak())
    story.append(Paragraph("Detailed Daily Routine", styles["Heading2"]))

    for section in SECTIONS:
        if section["name"] == "End of Day - Store Condition Audit":
            continue

        story.append(Paragraph(section["name"], section_style))
        rows = [["Status", "Task", "Owner", "Est.", "Completed", "Comment"]]

        for i, task in enumerate(FLAT_TASKS):
            if task["section"] != section["name"]:
                continue

            data = st.session_state.task_data[i]
            status = "DONE" if data["done"] else "PENDING"
            rows.append(
                [
                    status,
                    Paragraph(task["task"], task_style),
                    task["owner"],
                    f"{task['minutes']}m",
                    data["completed_at"] or "-",
                    Paragraph(data["comment"] or "-", task_style),
                ]
            )

        detail_table = Table(
            rows,
            colWidths=[
                0.48 * inch,
                2.65 * inch,
                0.40 * inch,
                0.42 * inch,
                1.30 * inch,
                1.75 * inch,
            ],
            repeatRows=1,
        )
        detail_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#aeb6b1")),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfe9e3")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#153e2f")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 6.3),
                    ("FONTSIZE", (0, 1), (-1, -1), 6.1),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 2.2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
                ]
            )
        )
        story.append(detail_table)
        story.append(Spacer(1, 2))

    # Page 4: mandatory store-condition audit photos.
    story.append(PageBreak())
    story.append(Paragraph("End of Day - Store Condition Audit", styles["Heading2"]))
    story.append(
        Paragraph(
            f"Completed with photo: {audit_completed_local}/{audit_total_local} "
            f"({audit_score_local:.0f}%)",
            styles["BodyText"],
        )
    )
    story.append(Spacer(1, 4))

    audit_cards = []
    for i in audit_indexes_local:
        task = FLAT_TASKS[i]
        data = st.session_state.task_data[i]

        if data["photo_bytes"]:
            try:
                photo = image_for_pdf(data["photo_bytes"], width=1.35 * inch)
                caption = Paragraph(
                    f"<b>{task['task']}</b><br/>"
                    f"{data['completed_at'] or ''}<br/>"
                    f"{data['comment'] or ''}",
                    small_style,
                )
                card = Table([[photo], [caption]], colWidths=[1.45 * inch])
            except Exception:
                card = Paragraph(f"<b>{task['task']}</b><br/>Photo error", small_style)
        else:
            card = Paragraph(
                f"<b>{task['task']}</b><br/>PHOTO MISSING",
                small_style,
            )

        audit_cards.append(card)

    # 4 columns x 4 rows fits all 13 areas on one page.
    grid = []
    for start in range(0, len(audit_cards), 4):
        row = audit_cards[start:start + 4]
        while len(row) < 4:
            row.append("")
        grid.append(row)

    audit_table = Table(
        grid,
        colWidths=[1.75 * inch] * 4,
        rowHeights=[2.35 * inch] * len(grid),
    )
    audit_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(audit_table)

    doc.build(story)
    output.seek(0)
    return output.getvalue()

init_state()
today = datetime.now()

st.markdown(
    f"""
    <div class="hero">
        <h1>O'Reilly Operations Assistant</h1>
        <p>Store 4691 · {today.strftime("%A, %B %d, %Y")}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.session_state.manager_name = st.text_input(
    "Manager on Duty",
    value=st.session_state.manager_name,
    placeholder="Enter name",
)

completed_total = sum(1 for value in st.session_state.task_data.values() if value["done"])
pending_total = len(FLAT_TASKS) - completed_total
score = completed_total / len(FLAT_TASKS) * 100 if FLAT_TASKS else 0

audit_indexes = [
    i for i, task in enumerate(FLAT_TASKS)
    if task["section"] == "End of Day - Store Condition Audit"
]
audit_completed = sum(
    1 for i in audit_indexes
    if st.session_state.task_data[i]["done"]
    and st.session_state.task_data[i]["photo_bytes"]
)
audit_total = len(audit_indexes)
audit_score = (audit_completed / audit_total * 100) if audit_total else 0
overall_score = ((score + audit_score) / 2) if audit_total else score

c1, c2, c3, c4 = st.columns(4)
c1.metric("Completed", completed_total)
c2.metric("Pending", pending_total)
c3.metric("Operations", f"{score:.0f}%")
c4.metric("Store Condition", f"{audit_score:.0f}%")
st.progress(overall_score / 100)
st.caption(f"Overall Daily Score: {overall_score:.0f}%")

if st.session_state.selected_section is None:
    st.markdown('<div class="section-title">Daily Routine</div>', unsafe_allow_html=True)

    for section in SECTIONS:
        done, total = section_counts(section["name"])
        status = section_status(section["name"])
        css_class = section_status_class(status)

        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"### {section['icon']} {section['name']}\n"
                    f"<span class='{css_class}'>{status}</span> · {done}/{total} tasks",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("Open", key=f"open_{section['name']}", use_container_width=True):
                    st.session_state.selected_section = section["name"]
                    st.rerun()

else:
    selected = st.session_state.selected_section
    if st.button("← Back to Daily Routine", use_container_width=True):
        st.session_state.selected_section = None
        st.rerun()

    st.markdown(f'<div class="section-title">{selected}</div>', unsafe_allow_html=True)

    for i, task in enumerate(FLAT_TASKS):
        if task["section"] != selected:
            continue

        data = st.session_state.task_data[i]

        with st.container(border=True):
            done = st.checkbox(
                task["task"],
                value=data["done"],
                key=f"done_{i}",
            )

            st.caption(
                f"Owner: {task['owner']} · Estimated: {task['minutes']} min"
                + (" · Photo required" if task["photo"] else "")
            )

            comment = st.text_input(
                "Comment",
                value=data["comment"],
                key=f"comment_{i}",
                placeholder="Optional comment or exception",
            )

            uploaded = st.file_uploader(
                "Take or upload photo",
                type=["jpg","jpeg","png"],
                key=f"photo_{i}",
            )

            photo_bytes = uploaded.getvalue() if uploaded else data["photo_bytes"]
            if photo_bytes:
                st.image(photo_bytes, use_container_width=True)

            data["done"] = bool(done)
            data["comment"] = comment
            data["photo_bytes"] = photo_bytes

            if done and not data["completed_at"]:
                data["completed_at"] = datetime.now().strftime("%m/%d/%Y %I:%M %p")
            elif not done:
                data["completed_at"] = None

            if done and task["photo"] and not photo_bytes:
                st.warning("This task requires photographic evidence.")

st.divider()

missing_required = [
    FLAT_TASKS[i]["task"]
    for i, data in st.session_state.task_data.items()
    if data["done"] and FLAT_TASKS[i]["photo"] and not data["photo_bytes"]
]

if missing_required:
    st.error("Missing required evidence for: " + "; ".join(missing_required))

audit_missing = [
    FLAT_TASKS[i]["task"]
    for i in audit_indexes
    if not st.session_state.task_data[i]["done"]
    or not st.session_state.task_data[i]["photo_bytes"]
]

if audit_missing:
    st.warning(
        "End-of-day audit incomplete. The following areas still require completion and a photo: "
        + "; ".join(audit_missing)
    )

pdf_bytes = generate_pdf(st.session_state.manager_name)

st.download_button(
    "Download Daily PDF",
    data=pdf_bytes,
    file_name=f"Store4691_Daily_Report_{today.strftime('%Y-%m-%d')}.pdf",
    mime="application/pdf",
    disabled=bool(missing_required or audit_missing),
    use_container_width=True,
)

if st.button("Reset Today", use_container_width=True):
    for i in range(len(FLAT_TASKS)):
        st.session_state.task_data[i] = {
            "done": False,
            "comment": "",
            "photo_bytes": None,
            "completed_at": None,
        }
    st.session_state.selected_section = None
    st.rerun()

st.caption(
    "Version 1.0 · Detailed daily routine, mandatory 13-area closing audit and 4-page PDF. "
    "Permanent cloud history will be added next."
)