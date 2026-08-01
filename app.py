import io
from datetime import datetime
import streamlit as st
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak

st.set_page_config(page_title="O'Reilly Operations Assistant", page_icon="✅", layout="centered")

st.markdown("""
<style>
.stApp { background-color:#f6f7f8; }
.block-container { max-width:760px; padding-top:1rem; padding-bottom:3rem; }
.hero { background:linear-gradient(135deg,#0b5d36,#138a4b); color:white; border-radius:18px; padding:20px; margin-bottom:16px; box-shadow:0 8px 24px rgba(0,0,0,.12); }
.hero h1 { margin:0; font-size:1.65rem; }
.hero p { margin:5px 0 0 0; opacity:.92; }
.section-label { font-weight:800; font-size:1.12rem; color:#153e2f; margin:18px 0 8px 0; }
div.stButton > button, div.stDownloadButton > button { width:100%; border-radius:12px; min-height:46px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

TASKS = [
("Prior to Opening","Open green bag/file returns manifest","MT",2,False),
("Prior to Opening","Print reports","MT",5,False),
("Prior to Opening","Count startup tracer bags and safe money; prepare cash drawers","MT",20,True),
("Prior to Opening","Verify deposit tracer bags and combine into one deposit","MT",20,True),
("Prior to Opening","Verify and process ordered items","DE",15,False),
("Prior to Opening","Begin daily returns / credit memo","DE",60,False),
("Open – 9:00 AM","Stock order check-in","DE",60,False),
("Open – 9:00 AM","Verify freight over & short and post to inventory","MT",15,False),
("Open – 9:00 AM","Complete and file daily reports","MT",15,False),
("Open – 9:00 AM","Update sales goals and complete Image Maker","MT",5,True),
("Open – 9:00 AM","Review payroll and approve punches before 10:00 AM","M",5,False),
("Open – 9:00 AM","Check Zipline and delegate assignments","MT",15,False),
("Open – 9:00 AM","Enter delivery vehicle mileage in Asset Management","DE",5,True),
("9:00 – 10:00 AM","Check email","MT",5,False),
("9:00 – 10:00 AM","Walk store aisle by aisle and create team to-do list","MT",15,True),
]

if "task_data" not in st.session_state:
    st.session_state.task_data = {i:{"done":False,"comment":"","photo":None,"time":None} for i in range(len(TASKS))}
if "manager" not in st.session_state:
    st.session_state.manager = ""

def image_for_pdf(photo_bytes):
    image = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    image.thumbnail((1200,900))
    out = io.BytesIO(); image.save(out,"JPEG",quality=72,optimize=True); out.seek(0)
    return RLImage(out,width=3.0*inch,height=2.0*inch)

def make_pdf(manager, score):
    out = io.BytesIO(); styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(out,pagesize=letter,rightMargin=.35*inch,leftMargin=.35*inch,topMargin=.35*inch,bottomMargin=.35*inch)
    story=[Paragraph("O'REILLY OPERATIONS ASSISTANT",styles["Title"]),Paragraph("Store 4691 – Daily Opening Report",styles["Heading2"]),Spacer(1,8)]
    now=datetime.now(); done=sum(1 for d in st.session_state.task_data.values() if d["done"]); total=len(TASKS)
    summary=[["Date",now.strftime("%m/%d/%Y"),"Manager",manager or "Not entered"],["Generated",now.strftime("%I:%M %p"),"Score",f"{score:.0f}%"],["Completed",str(done),"Pending",str(total-done)]]
    t=Table(summary,colWidths=[.9*inch,2.1*inch,.9*inch,2.8*inch]); t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.lightgrey),("BACKGROUND",(2,0),(2,-1),colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),8)])); story += [t,Spacer(1,10)]
    rows=[["Status","Task","Owner","Time","Comment"]]
    for i,(section,task,owner,mins,photo_req) in enumerate(TASKS):
        d=st.session_state.task_data[i]; rows.append(["Complete" if d["done"] else "Pending",task,owner,f"{mins} min",d["comment"]])
    ct=Table(rows,colWidths=[.65*inch,3.25*inch,.55*inch,.65*inch,1.95*inch],repeatRows=1)
    ct.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0b5d36")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),7)])); story.append(ct)
    photos=[(TASKS[i],d) for i,d in st.session_state.task_data.items() if d["photo"]][:12]
    for start in range(0,len(photos),4):
        story.append(PageBreak()); story.append(Paragraph("Photographic Evidence",styles["Heading2"]))
        grid=[]; row=[]
        for task_data,d in photos[start:start+4]:
            section,task,owner,mins,photo_req=task_data
            try:
                img=image_for_pdf(d["photo"])
                cap=Paragraph(f"<b>{task}</b><br/>{d['time'] or ''}<br/>{d['comment'] or ''}",styles["BodyText"])
                row.append(Table([[img],[cap]],colWidths=[3.15*inch]))
                if len(row)==2: grid.append(row); row=[]
            except Exception:
                pass
        if row: row.append(""); grid.append(row)
        pt=Table(grid,colWidths=[3.35*inch,3.35*inch]); pt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.3,colors.grey),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(pt)
    doc.build(story); out.seek(0); return out.getvalue()

now=datetime.now()
st.markdown(f"<div class='hero'><h1>O'Reilly Operations Assistant</h1><p>Store 4691 · {now.strftime('%A, %B %d, %Y')}</p></div>", unsafe_allow_html=True)
manager=st.text_input("Manager on Duty",value=st.session_state.manager,placeholder="Enter name"); st.session_state.manager=manager
completed=sum(1 for d in st.session_state.task_data.values() if d["done"]); score=completed/len(TASKS)*100
c1,c2,c3=st.columns(3); c1.metric("Completed",completed); c2.metric("Pending",len(TASKS)-completed); c3.metric("Score",f"{score:.0f}%"); st.progress(score/100)

for section in dict.fromkeys(t[0] for t in TASKS):
    st.markdown(f"<div class='section-label'>{section}</div>",unsafe_allow_html=True)
    for i,(sec,task,owner,mins,photo_req) in enumerate(TASKS):
        if sec != section: continue
        d=st.session_state.task_data[i]
        with st.container(border=True):
            done=st.checkbox(task,value=d["done"],key=f"done_{i}")
            st.caption(f"Owner: {owner} · Estimated: {mins} min" + (" · Photo required" if photo_req else ""))
            comment=st.text_input("Comment",value=d["comment"],key=f"comment_{i}",placeholder="Optional comment or exception")
            upload=st.file_uploader("Take or upload photo",type=["jpg","jpeg","png"],key=f"photo_{i}")
            photo=upload.getvalue() if upload else d["photo"]
            if photo: st.image(photo,caption="Evidence preview",use_container_width=True)
            if done and photo_req and not photo: st.warning("This task requires photographic evidence.")
            d["done"]=done; d["comment"]=comment; d["photo"]=photo
            if done and not d["time"]: d["time"]=datetime.now().strftime("%m/%d/%Y %I:%M %p")
            if not done: d["time"]=None

missing=[TASKS[i][1] for i,d in st.session_state.task_data.items() if d["done"] and TASKS[i][4] and not d["photo"]]
if missing: st.error("Missing required evidence for: " + "; ".join(missing))
pdf=make_pdf(manager,score)
st.download_button("Generate / Download Daily PDF",data=pdf,file_name=f"Store4691_Opening_{now.strftime('%Y-%m-%d')}.pdf",mime="application/pdf",disabled=bool(missing),use_container_width=True)
if st.button("Reset today's checklist",use_container_width=True):
    st.session_state.task_data={i:{"done":False,"comment":"","photo":None,"time":None} for i in range(len(TASKS))}; st.rerun()
st.caption("Version 0.1 · Data is stored only during the current session. Cloud history will be added next.")