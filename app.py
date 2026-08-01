
import io
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
import streamlit as st
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from supabase import Client, create_client

st.set_page_config(page_title="O'Reilly Operations Assistant", page_icon="✅", layout="centered", initial_sidebar_state="collapsed")

STORE_NUMBER = "4691"
APP_TIMEZONE = ZoneInfo("America/Chicago")
PHOTO_BUCKET = "task-evidence"
AUDIT_SECTION = "End of Day - Store Condition Audit"

MANDATORY_PHOTO_TASKS = {
    "Verify all deposit tracer bags/combined into 1 deposit",
    "Enter delivery vehicle mileage in Asset Management",
    "Take deposit to bank before cutoff",
    "Return manifest completed/outgoing freight wrapped",
    "Verify all cash and delivery vehicle keys are locked in the safe after closing",
    "Parking Lot", "Trash", "Counter", "Aisle 1", "Aisle 2", "Aisle 3",
    "Aisle 4", "Aisle 5", "Aisle 6", "Oil Rack", "Battery Rack",
    "Restroom Mens", "Restroom Womens",
}

SECTIONS = [
    {"name":"Prior to Opening","icon":"🌅","tasks":[
        ("Open green bag/file returns manifest","MT",2),
        ("Print reports","MT",5),
        ("Count startup tracer bags and safe money; prepare cash drawers","MT",20),
        ("Verify all deposit tracer bags/combined into 1 deposit","MT",20),
        ("Verify and process ordered items","DE",15),
        ("Begin daily returns / credit memo","DE",60),
    ]},
    {"name":"Open – 9:00 AM","icon":"🕘","tasks":[
        ("Stock order check-in","DE",60),
        ("Verify freight over & short and post to inventory","MT",15),
        ("Send daily/weekly account statements","MT",5),
        ("Complete and file daily reports","MT",15),
        ("Update sales goals and complete Image Maker","MT",5),
        ("Review payroll and approve punches before 10:00 AM","M",5),
        ("Check Zipline and delegate assignments","MT",15),
        ("Enter delivery vehicle mileage in Asset Management","DE",5),
    ]},
    {"name":"9:00 – 10:00 AM","icon":"📧","tasks":[
        ("Check email","MT",5),
        ("Walk store aisle by aisle and create team to-do list","MT",15),
    ]},
    {"name":"10:00 – 11:00 AM","icon":"🗓️","tasks":[("Work schedule","MT",30)]},
    {"name":"11:00 AM – 1:00 PM","icon":"🏦","tasks":[
        ("Take deposit to bank before cutoff","MT",30),
        ("Verify cash drawers are locked and drops are being made","MT",5),
    ]},
    {"name":"2:00 – 3:00 PM","icon":"🔄","tasks":[
        ("Follow up on Zipline and daily assignments","MT",15),
    ]},
    {"name":"3:00 – 5:00 PM","icon":"📦","tasks":[
        ("Process outside purchase billing information","MT",10),
        ("Complete costing by 5:00 PM","DE",15),
        ("Check email","MT",10),
        ("Return manifest completed/outgoing freight wrapped","DE",10),
        ("Congratulate team for a job well done","MT",5),
    ]},
    {"name":"5:00 PM – Close","icon":"🔒","tasks":[
        ("Verify cash drawers are locked and drops are being made","MT",5),
        ("Complete Image Maker task","MT",10),
        ("Verify all cash and delivery vehicle keys are locked in the safe after closing","MT",5),
        ("Complete outstanding Image Maker and assigned tasks","MT",10),
        ("Secure delivery vehicles, park, lock and secure keys","MT",5),
    ]},
    {"name":"After Close","icon":"🌙","tasks":[
        ("Ensure coffee pot is unplugged","DE",1),
        ("Unplug battery chargers","DE",1),
        ("Run Dayend","MT",1),
        ("Count remaining drawers, final-count safe and secure all money","MT",10),
        ("Set alarm before leaving","MT",1),
    ]},
    {"name":AUDIT_SECTION,"icon":"📸","tasks":[
        ("Parking Lot","MT",3),("Trash","MT",3),("Counter","MT",3),
        ("Aisle 1","MT",3),("Aisle 2","MT",3),("Aisle 3","MT",3),
        ("Aisle 4","MT",3),("Aisle 5","MT",3),("Aisle 6","MT",3),
        ("Oil Rack","MT",3),("Battery Rack","MT",3),
        ("Restroom Mens","MT",3),("Restroom Womens","MT",3),
    ]},
]

FLAT_TASKS = []
for section in SECTIONS:
    for position, (task_name, owner, minutes) in enumerate(section["tasks"], start=1):
        task_key = re.sub(r"[^a-z0-9]+", "-", f"{section['name']}-{task_name}".lower()).strip("-")
        FLAT_TASKS.append({
            "task_key":task_key,"section":section["name"],"icon":section["icon"],
            "task":task_name,"owner":owner,"minutes":minutes,"position":position,
            "photo_required":task_name in MANDATORY_PHOTO_TASKS,
        })

st.markdown("""
<style>
.stApp{background:#f5f7f6}.block-container{max-width:780px;padding-top:.8rem;padding-bottom:3rem}
.hero{background:linear-gradient(135deg,#0b5d36,#16864f);color:white;border-radius:22px;padding:22px;margin-bottom:14px;box-shadow:0 10px 26px rgba(0,0,0,.13)}
.hero h1{margin:0;font-size:1.7rem;line-height:1.15}.hero p{margin:8px 0 0;opacity:.93}
.status-complete{color:#0b7a42;font-weight:800}.status-progress{color:#b46a00;font-weight:800}.status-pending{color:#6b7280;font-weight:800}
.section-title{font-size:1.15rem;font-weight:800;color:#174b37;margin:14px 0 8px}
div.stButton>button,div.stDownloadButton>button{width:100%;border-radius:12px;min-height:46px;font-weight:700}
[data-testid="stMetricValue"]{font-size:1.75rem}
</style>
""", unsafe_allow_html=True)

def now_local(): return datetime.now(APP_TIMEZONE)
def iso_now(): return now_local().isoformat()
def work_date(): return now_local().date().isoformat()

def display_datetime(value):
    if not value: return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z","+00:00"))
        return dt.astimezone(APP_TIMEZONE).strftime("%m/%d/%Y %I:%M:%S %p %Z")
    except Exception:
        return str(value)

@st.cache_resource
def get_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except KeyError as exc:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in Streamlit Secrets.") from exc

def public_photo_url(path):
    return f"{str(st.secrets['SUPABASE_URL']).rstrip('/')}/storage/v1/object/public/{PHOTO_BUCKET}/{path}"

def initialize_today(client):
    today = work_date()
    client.table("daily_runs").upsert(
        {"store_number":STORE_NUMBER,"work_date":today,"day_started_at":iso_now()},
        on_conflict="store_number,work_date", ignore_duplicates=True
    ).execute()
    rows = [{
        "store_number":STORE_NUMBER,"work_date":today,"task_key":t["task_key"],
        "section_name":t["section"],"task_name":t["task"],"completed":False,
        "updated_at":iso_now()
    } for t in FLAT_TASKS]
    client.table("daily_tasks").upsert(
        rows,on_conflict="store_number,work_date,task_key",ignore_duplicates=True
    ).execute()

def load_rows(client):
    r=(client.table("daily_tasks").select("*").eq("store_number",STORE_NUMBER)
       .eq("work_date",work_date()).execute())
    return r.data or []

def load_run(client):
    r=(client.table("daily_runs").select("*").eq("store_number",STORE_NUMBER)
       .eq("work_date",work_date()).limit(1).execute())
    return r.data[0] if r.data else {}

def update_manager(client, manager):
    client.table("daily_runs").upsert(
        {"store_number":STORE_NUMBER,"work_date":work_date(),
         "manager_on_duty":manager.strip() or None},
        on_conflict="store_number,work_date"
    ).execute()

def save_task(client, task, completed, operator, comment, uploaded, current):
    if not operator.strip():
        raise ValueError("Enter your name before saving a task.")
    photo_url=current.get("photo_url")
    photo_taken=current.get("photo_taken_at")
    if uploaded is not None:
        ext=Path(uploaded.name).suffix.lower() or ".jpg"
        stamp=now_local().strftime("%Y%m%d-%H%M%S-%f")
        path=f"store-{STORE_NUMBER}/{work_date()}/{task['task_key']}/{stamp}{ext}"
        client.storage.from_(PHOTO_BUCKET).upload(
            path, uploaded.getvalue(),
            file_options={"content-type":uploaded.type or "image/jpeg"}
        )
        photo_url=public_photo_url(path)
        photo_taken=iso_now()
    if task["photo_required"] and completed and not photo_url:
        raise ValueError("This task requires a photo before completion.")
    completed_at=current.get("completed_at")
    completed_by=current.get("completed_by")
    if completed and not current.get("completed"):
        completed_at=iso_now(); completed_by=operator.strip()
    elif not completed:
        completed_at=None; completed_by=None
    payload={
        "store_number":STORE_NUMBER,"work_date":work_date(),"task_key":task["task_key"],
        "section_name":task["section"],"task_name":task["task"],"completed":completed,
        "completed_by":completed_by,"completed_at":completed_at,
        "comment":comment.strip() or None,"photo_url":photo_url,
        "photo_taken_at":photo_taken,"updated_at":iso_now()
    }
    client.table("daily_tasks").upsert(
        payload,on_conflict="store_number,work_date,task_key"
    ).execute()

def reset_today(client):
    client.table("daily_tasks").delete().eq("store_number",STORE_NUMBER).eq("work_date",work_date()).execute()
    client.table("daily_runs").delete().eq("store_number",STORE_NUMBER).eq("work_date",work_date()).execute()
    initialize_today(client)

def section_counts(name, rows_by_key):
    tasks=[t for t in FLAT_TASKS if t["section"]==name]
    done=0
    for t in tasks:
        row=rows_by_key.get(t["task_key"],{})
        valid=bool(row.get("completed"))
        if t["photo_required"]: valid=valid and bool(row.get("photo_url"))
        done+=int(valid)
    return done,len(tasks)

def section_status(done,total):
    if total and done==total:return "Complete","status-complete"
    if done:return "In Progress","status-progress"
    return "Pending","status-pending"

def fetch_image(url):
    if not url:return None
    try:
        r=requests.get(url,timeout=12);r.raise_for_status();return r.content
    except Exception:return None

def image_for_pdf(data,width):
    img=Image.open(io.BytesIO(data)).convert("RGB");img.thumbnail((900,700))
    out=io.BytesIO();img.save(out,"JPEG",quality=68,optimize=True);out.seek(0)
    return RLImage(out,width=width,height=width*(img.height/img.width))

def generate_pdf(rows_by_key,run):
    out=io.BytesIO();styles=getSampleStyleSheet()
    body=styles["BodyText"];body.fontSize=6.1;body.leading=7.0
    tiny=styles["BodyText"];tiny.fontSize=5.6;tiny.leading=6.4
    secstyle=styles["Heading3"];secstyle.fontSize=8.4;secstyle.leading=9
    secstyle.textColor=colors.HexColor("#0b5d36");secstyle.spaceBefore=3;secstyle.spaceAfter=2
    doc=SimpleDocTemplate(out,pagesize=letter,rightMargin=.22*inch,leftMargin=.22*inch,topMargin=.22*inch,bottomMargin=.22*inch)
    ops=[t for t in FLAT_TASKS if t["section"]!=AUDIT_SECTION]
    aud=[t for t in FLAT_TASKS if t["section"]==AUDIT_SECTION]
    ops_done=sum(1 for t in ops if rows_by_key.get(t["task_key"],{}).get("completed") and (not t["photo_required"] or rows_by_key.get(t["task_key"],{}).get("photo_url")))
    aud_done=sum(1 for t in aud if rows_by_key.get(t["task_key"],{}).get("completed") and rows_by_key.get(t["task_key"],{}).get("photo_url"))
    ops_score=ops_done/len(ops)*100;aud_score=aud_done/len(aud)*100;overall=(ops_score+aud_score)/2
    story=[Paragraph("O'REILLY OPERATIONS ASSISTANT",styles["Title"]),
           Paragraph("Store 4691 - Shared Daily Operations Report",styles["Heading2"]),Spacer(1,5)]
    summary=[
        ["Date",work_date(),"Manager",run.get("manager_on_duty") or "Not entered"],
        ["Generated",display_datetime(iso_now()),"Overall",f"{overall:.0f}%"],
        ["Operations",f"{ops_score:.0f}%","Store Condition",f"{aud_score:.0f}%"],
        ["Day Started",display_datetime(run.get("day_started_at")),"Users","Management Team"],
    ]
    t=Table(summary,colWidths=[.85*inch,2.15*inch,1.05*inch,2.65*inch])
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8ecea")),
        ("BACKGROUND",(2,0),(2,-1),colors.HexColor("#e8ecea")),
        ("FONTSIZE",(0,0),(-1,-1),7.7)]))
    story += [t,Spacer(1,5)]
    sr=[["Section","Completed","Total","Score"]]
    for s in SECTIONS:
        d,total=section_counts(s["name"],rows_by_key);sr.append([s["name"],d,total,f"{d/total*100:.0f}%"])
    stbl=Table(sr,colWidths=[4*inch,.85*inch,.75*inch,.85*inch])
    stbl.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0b5d36")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTSIZE",(0,0),(-1,-1),6.8)]))
    story.append(stbl);story.append(PageBreak());story.append(Paragraph("Detailed Daily Routine",styles["Heading2"]))
    for s in SECTIONS:
        if s["name"]==AUDIT_SECTION:continue
        story.append(Paragraph(s["name"],secstyle))
        rows=[["Status","Task","By","Completed","Comment"]]
        for task in FLAT_TASKS:
            if task["section"]!=s["name"]:continue
            row=rows_by_key.get(task["task_key"],{})
            comment=row.get("comment") or "-"
            if row.get("photo_taken_at"):comment+=f"<br/><b>Photo:</b> {display_datetime(row.get('photo_taken_at'))}"
            rows.append(["DONE" if row.get("completed") else "PENDING",
                         Paragraph(task["task"],body),row.get("completed_by") or "-",
                         display_datetime(row.get("completed_at")),Paragraph(comment,body)])
        dt=Table(rows,colWidths=[.48*inch,2.75*inch,.85*inch,1.35*inch,1.65*inch],repeatRows=1)
        dt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.22,colors.HexColor("#aeb6b1")),
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#dfe9e3")),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),6),
            ("FONTSIZE",(0,1),(-1,-1),5.9),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),2.5),("RIGHTPADDING",(0,0),(-1,-1),2.5),
            ("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        story += [dt,Spacer(1,2)]
    story.append(PageBreak());story.append(Paragraph("Required Photographic Evidence",styles["Heading2"]))
    cards=[]
    for task in [t for t in FLAT_TASKS if t["photo_required"]]:
        row=rows_by_key.get(task["task_key"],{});data=fetch_image(row.get("photo_url"))
        if data:
            try:
                photo=image_for_pdf(data,1.2*inch)
                cap=Paragraph(f"<b>{task['task']}</b><br/>{row.get('completed_by') or '-'}<br/>{display_datetime(row.get('photo_taken_at'))}",tiny)
                card=Table([[photo],[cap]],colWidths=[1.35*inch])
            except Exception:card=Paragraph(f"<b>{task['task']}</b><br/>Photo error",tiny)
        else:card=Paragraph(f"<b>{task['task']}</b><br/>PHOTO MISSING",tiny)
        cards.append(card)
    grid=[]
    for i in range(0,len(cards),4):
        row=cards[i:i+4]
        while len(row)<4:row.append("")
        grid.append(row)
    sheet=Table(grid,colWidths=[1.75*inch]*4,rowHeights=[1.95*inch]*len(grid))
    sheet.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.25,colors.grey),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),3),
        ("RIGHTPADDING",(0,0),(-1,-1),3),("TOPPADDING",(0,0),(-1,-1),3)]))
    story.append(sheet);doc.build(story);out.seek(0);return out.getvalue()

if "operator_name" not in st.session_state:
    st.session_state.operator_name = ""
if "selected_section" not in st.session_state:
    st.session_state.selected_section = None
require_login()

try:
    supabase=get_supabase();initialize_today(supabase)
except Exception as exc:
    st.error(f"Database connection error: {exc}");st.stop()

with st.sidebar:
    st.header("Shared App")
    st.success(f"Signed in as: {st.session_state.operator_name}")
    st.caption("Changes are saved immediately in Supabase. Tap Refresh to load changes made on another device.")
    if st.button("Refresh shared checklist", use_container_width=True):
        st.rerun()
    logout_button()

rows=load_rows(supabase);rows_by_key={r["task_key"]:r for r in rows};run=load_run(supabase)
today=now_local()
st.markdown(f"""<div class="hero"><h1>O'Reilly Operations Assistant</h1>
<p>Store {STORE_NUMBER} · {today.strftime("%A, %B %d, %Y")}</p><p>Shared Management Team Checklist</p></div>""",unsafe_allow_html=True)
st.info(f"Signed in as **{st.session_state.operator_name}**")

manager=st.text_input("Manager on Duty",value=run.get("manager_on_duty") or "",placeholder="Manager on Duty")
if manager!=(run.get("manager_on_duty") or ""):
    if st.button("Save Manager on Duty",use_container_width=True):
        update_manager(supabase,manager);st.success("Manager on Duty saved.");st.rerun()

ops=[t for t in FLAT_TASKS if t["section"]!=AUDIT_SECTION];aud=[t for t in FLAT_TASKS if t["section"]==AUDIT_SECTION]
ops_done=sum(1 for t in ops if rows_by_key.get(t["task_key"],{}).get("completed") and (not t["photo_required"] or rows_by_key.get(t["task_key"],{}).get("photo_url")))
aud_done=sum(1 for t in aud if rows_by_key.get(t["task_key"],{}).get("completed") and rows_by_key.get(t["task_key"],{}).get("photo_url"))
ops_score=ops_done/len(ops)*100;aud_score=aud_done/len(aud)*100;overall=(ops_score+aud_score)/2
c1,c2,c3,c4=st.columns(4)
c1.metric("Completed",ops_done+aud_done);c2.metric("Pending",len(FLAT_TASKS)-ops_done-aud_done)
c3.metric("Operations",f"{ops_score:.0f}%");c4.metric("Condition",f"{aud_score:.0f}%")
st.progress(overall/100);st.caption(f"Overall Daily Score: {overall:.0f}% · Last refreshed: {now_local().strftime('%I:%M:%S %p %Z')}")

if st.session_state.selected_section is None:
    st.markdown('<div class="section-title">Daily Routine</div>',unsafe_allow_html=True)
    for s in SECTIONS:
        d,total=section_counts(s["name"],rows_by_key);status,css=section_status(d,total)
        with st.container(border=True):
            l,r=st.columns([4,1])
            with l:st.markdown(f"### {s['icon']} {s['name']}\n<span class='{css}'>{status}</span> · {d}/{total} tasks",unsafe_allow_html=True)
            with r:
                if st.button("Open",key=f"open-{s['name']}",use_container_width=True):
                    st.session_state.selected_section=s["name"];st.rerun()
else:
    selected=st.session_state.selected_section
    if st.button("← Back to Daily Routine",use_container_width=True):
        st.session_state.selected_section=None;st.rerun()
    st.markdown(f'<div class="section-title">{selected}</div>',unsafe_allow_html=True)
    for task in FLAT_TASKS:
        if task["section"]!=selected:continue
        row=rows_by_key.get(task["task_key"],{})
        with st.container(border=True):
            st.markdown(f"### {task['task']}")
            st.caption(f"Owner: {task['owner']} · Estimated: {task['minutes']} min"+(" · 📷 Photo required" if task["photo_required"] else ""))
            if row.get("completed"):st.success(f"Completed by {row.get('completed_by') or '-'} · {display_datetime(row.get('completed_at'))}")
            completed=st.checkbox("Completed",value=bool(row.get("completed")),key=f"done-{task['task_key']}")
            comment=st.text_input("Comment",value=row.get("comment") or "",key=f"comment-{task['task_key']}",placeholder="Optional comment or exception")
            uploaded=st.file_uploader("Take or upload photo",type=["jpg","jpeg","png"],key=f"photo-{task['task_key']}")
            if row.get("photo_url"):
                st.image(row["photo_url"],use_container_width=True)
                st.caption(f"Photo recorded: {display_datetime(row.get('photo_taken_at'))}")
            if st.button("Save task",key=f"save-{task['task_key']}",type="primary",use_container_width=True):
                try:
                    save_task(supabase,task,completed,st.session_state.operator_name,comment,uploaded,row)
                    st.success("Saved for the entire management team.");st.rerun()
                except Exception as exc:st.error(str(exc))

st.divider()
missing=[t["task"] for t in FLAT_TASKS if t["photo_required"] and (not rows_by_key.get(t["task_key"],{}).get("completed") or not rows_by_key.get(t["task_key"],{}).get("photo_url"))]
if missing:st.warning(f"{len(missing)} required-photo tasks remain incomplete.")
pdf=generate_pdf(rows_by_key,run)
st.download_button("Download Shared Daily PDF",data=pdf,file_name=f"Store4691_Shared_Report_{work_date()}.pdf",mime="application/pdf",disabled=bool(missing),use_container_width=True)

with st.expander("Manager controls"):
    st.warning("Reset Today deletes today's shared checklist for every user.")
    confirm=st.checkbox("I understand this affects everyone.")
    if st.button("Reset Today's Shared Checklist",disabled=not confirm,use_container_width=True):
        reset_today(supabase);st.success("Today's shared checklist was reset.");st.rerun()

st.caption("Multiuser Version 4.0 · Counter Login · Supabase shared database · Changes are saved for all users immediately and appear on other devices after refresh.")

def get_users():
    try:
        users = dict(st.secrets["users"])
    except Exception as exc:
        raise RuntimeError("Missing [users] section in Streamlit Secrets.") from exc
    return {str(counter).strip(): str(name).strip() for counter, name in users.items()}

def login_screen():
    st.markdown("""<div class="hero"><h1>O'Reilly Operations Assistant</h1><p>Store 4691 · Management Team Access</p></div>""", unsafe_allow_html=True)
    st.subheader("Enter your counter number")
    counter = st.text_input("Counter number", type="password", placeholder="Enter counter number", label_visibility="collapsed")
    if st.button("Sign in", type="primary", use_container_width=True):
        users = get_users()
        normalized = counter.strip()
        if normalized in users:
            st.session_state.authenticated = True
            st.session_state.operator_name = users[normalized]
            st.session_state.counter_number = normalized
            st.rerun()
        else:
            st.error("Counter number not recognized.")
    st.caption("Authorized management team members only. Counter numbers are not displayed or stored in reports.")

def require_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "counter_number" not in st.session_state:
        st.session_state.counter_number = ""
    if not st.session_state.authenticated:
        login_screen()
        st.stop()

def logout_button():
    if st.button("Log out / Change user", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.operator_name = ""
        st.session_state.counter_number = ""
        st.session_state.selected_section = None
        st.rerun()