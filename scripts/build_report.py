#!/usr/bin/env python3
"""Build DOCX from the supplied Beihang template and PDF via ReportLab Platypus."""
from pathlib import Path
import re, html
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether, Image as RLImage

ROOT = Path(__file__).resolve().parents[1]
MD_PATH = ROOT / "report" / "SmartFind_Report.md"
TEMPLATE = ROOT / "docs" / "course_template" / "人工智能实践大作业(4).docx"
DOCX_OUT = ROOT / "report" / "SmartFind_Report.docx"
PDF_OUT = ROOT / "report" / "SmartFind_Report.pdf"
text = MD_PATH.read_text(encoding="utf-8")
lines = text.splitlines()
start = next(i for i, line in enumerate(lines) if line.startswith("# 1. Creative Background"))
body_lines = lines
status_note = 'Final audit: 41 isolated backend/migration tests and six local Playwright workflows pass. Lint, TypeScript and production build pass. Live Gemini text analysis and Chinese-to-English improvement returned google_gemini. Real image inference and pretrained E5/OpenCLIP remain unverified. Dedicated PostgreSQL concurrency/load testing, production deployment of this branch, legacy-cookie transition and backup restore remain release gates. See docs/verification/final-results.md.'

# ---------- Markdown block parser ----------
def parse_blocks(src_lines):
    blocks=[]; i=0; para=[]
    def flush():
        nonlocal para
        if para:
            blocks.append(("p", " ".join(x.strip() for x in para if x.strip())))
            para=[]
    while i < len(src_lines):
        line=src_lines[i]
        if not line.strip() or line.strip()=="---":
            flush(); i+=1; continue
        if line.startswith("# "):
            flush(); blocks.append(("h1",line[2:].strip())); i+=1; continue
        if line.startswith("## "):
            flush(); blocks.append(("h2",line[3:].strip())); i+=1; continue
        if line.startswith("### "):
            flush(); blocks.append(("h3",line[4:].strip())); i+=1; continue
        if line.startswith("!["):
            flush()
            match=re.match(r"!\[(.*?)\]\((.*?)\)",line.strip())
            if match: blocks.append(("image",(match.group(1),match.group(2))))
            i+=1; continue
        if line.startswith("|"):
            flush(); table=[]
            while i < len(src_lines) and src_lines[i].strip().startswith("|"):
                row=[cell.strip() for cell in src_lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", cell.replace(" ","")) for cell in row):
                    table.append(row)
                i+=1
            blocks.append(("table",table)); continue
        if line.startswith("- "):
            flush(); items=[]
            while i < len(src_lines) and src_lines[i].startswith("- "):
                items.append(src_lines[i][2:].strip()); i+=1
            blocks.append(("ul",items)); continue
        if re.match(r"^\d+\. ",line):
            flush(); items=[]
            while i < len(src_lines) and re.match(r"^\d+\. ",src_lines[i]):
                items.append(re.sub(r"^\d+\. ","",src_lines[i]).strip()); i+=1
            blocks.append(("ol",items)); continue
        if line.startswith("> "):
            flush(); blocks.append(("quote",line[2:].strip())); i+=1; continue
        para.append(line); i+=1
    flush()
    return blocks

blocks=parse_blocks(body_lines)

# ---------- DOCX using the supplied template's page setup/styles ----------
doc = Document(str(TEMPLATE))
body = doc._element.body
for child in list(body):
    if child.tag != qn("w:sectPr"):
        body.remove(child)
section=doc.sections[0]
section.top_margin=Inches(0.78); section.bottom_margin=Inches(0.72)
section.left_margin=Inches(0.85); section.right_margin=Inches(0.85)

styles=doc.styles
normal=styles["Normal"]
normal.font.name="Times New Roman"; normal.font.size=Pt(10.5); normal.font.color.rgb=RGBColor(35,48,64)
normal.paragraph_format.space_after=Pt(6); normal.paragraph_format.line_spacing=1.12
for stylename,size,color in [("Heading 1",15,"173B63"),("Heading 2",12,"245F91"),("Heading 3",10.5,"48627D")]:
    st=styles[stylename]; st.font.name="Times New Roman"; st.font.size=Pt(size); st.font.bold=True; st.font.color.rgb=RGBColor.from_string(color)
    st.paragraph_format.space_before=Pt(12); st.paragraph_format.space_after=Pt(5); st.paragraph_format.keep_with_next=True

# Header and footer based on the course template's academic identity.
header=section.header.paragraphs[0]
header.text="BEIHANG UNIVERSITY  |  ARTIFICIAL INTELLIGENCE PRACTICE"
header.alignment=WD_ALIGN_PARAGRAPH.CENTER
for run in header.runs:
    run.font.name="Times New Roman"; run.font.size=Pt(8); run.font.color.rgb=RGBColor(120,135,150)
footer=section.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run("Beihang SmartFind  |  Page ")
r.font.name="Times New Roman"; r.font.size=Pt(8); r.font.color.rgb=RGBColor(130,140,150)
fld=OxmlElement("w:fldSimple"); fld.set(qn("w:instr"),"PAGE"); footer._p.append(fld)

def add_docx_rich(paragraph, value):
    parts=re.split(r"(\*\*.*?\*\*|`.*?`|\*.*?\*)",value)
    for part in parts:
        if not part: continue
        if part.startswith("**") and part.endswith("**"):
            run=paragraph.add_run(part[2:-2]); run.bold=True
        elif part.startswith("`") and part.endswith("`"):
            run=paragraph.add_run(part[1:-1]); run.font.name="Consolas"; run.font.size=Pt(9)
        elif part.startswith("*") and part.endswith("*"):
            run=paragraph.add_run(part[1:-1]); run.italic=True
        else:
            run=paragraph.add_run(part)
        if run.font.name is None: run.font.name="Times New Roman"

# Cover page reconstructed from the original template, preserving its page geometry.
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(62)
r=p.add_run("北京航空航天大学"); r.bold=True; r.font.name="SimSun"; r.font.size=Pt(20); r.font.color.rgb=RGBColor(20,45,78)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run("2026-2027 Academic Year, First Semester"); r.font.size=Pt(12); r.font.name="Times New Roman"
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(35)
r=p.add_run("《Artificial Intelligence Practice》"); r.bold=True; r.font.size=Pt(16)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run("FINAL PROJECT EXPERIMENT REPORT"); r.bold=True; r.font.size=Pt(13); r.font.color.rgb=RGBColor(65,83,104)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(28)
r=p.add_run("Beihang SmartFind"); r.bold=True; r.font.size=Pt(24); r.font.color.rgb=RGBColor(20,45,78)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run("北航校园智能失物招领系统"); r.font.name="SimSun"; r.font.size=Pt(15); r.font.color.rgb=RGBColor(36,95,145)
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=p.add_run("An AI-Powered Multimodal Campus Lost-and-Found Platform"); r.italic=True; r.font.size=Pt(11)
for _ in range(2): doc.add_paragraph()
cover_table=doc.add_table(rows=4,cols=2); cover_table.alignment=WD_TABLE_ALIGNMENT.CENTER; cover_table.autofit=False
cover_table.columns[0].width=Inches(1.45); cover_table.columns[1].width=Inches(4.2)
cover_data=[("Student Name","________________________"),("Student ID","________________________"),("Class","________________________"),("Grade","________________________")]
for row,(label,value) in zip(cover_table.rows,cover_data):
    row.cells[0].text=label; row.cells[1].text=value
    for cell in row.cells:
        cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for pp in cell.paragraphs:
            pp.paragraph_format.space_after=Pt(4)
            for rr in pp.runs: rr.font.name="Times New Roman"; rr.font.size=Pt(10)
    row.cells[0].paragraphs[0].runs[0].bold=True
p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before=Pt(32)
r=p.add_run("November 2026"); r.font.size=Pt(11)
doc.add_page_break()

p=doc.add_paragraph("Implementation Status",style="Heading 1")
p=doc.add_paragraph(); add_docx_rich(p,status_note)
p.paragraph_format.left_indent=Inches(0.15); p.paragraph_format.right_indent=Inches(0.15)
# Static table of contents consistent with the course template.
doc.add_paragraph("Contents",style="Heading 1")
for entry in ["1. Creative Background","2. Selected Large Model","3. Overall Design Plan","4. Experimental Steps","5. Program Running Effect","6. Experimental Summary","7. Course Learning Summary","8. Main Reference Materials","9. Core Code Explanation"]:
    p=doc.add_paragraph(entry); p.paragraph_format.left_indent=Inches(0.18); p.paragraph_format.space_after=Pt(3)
doc.add_page_break()

for kind,value in blocks:
    if kind=="h1":
        if value.startswith(tuple(f"{i}." for i in range(2,10))): doc.add_page_break()
        doc.add_paragraph(value,style="Heading 1")
    elif kind=="h2": doc.add_paragraph(value,style="Heading 2")
    elif kind=="h3": doc.add_paragraph(value,style="Heading 3")
    elif kind=="p":
        p=doc.add_paragraph(); add_docx_rich(p,value)
    elif kind=="quote":
        p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.2); p.paragraph_format.right_indent=Inches(0.2)
        for run in p.add_run(value),: run.italic=True; run.font.color.rgb=RGBColor(90,105,120)
    elif kind in {"ul","ol"}:
        for idx,item in enumerate(value,1):
            p=doc.add_paragraph(); p.paragraph_format.left_indent=Inches(0.25)
            marker="•  " if kind=="ul" else f"{idx}.  "
            p.add_run(marker); add_docx_rich(p,item)
    elif kind=="image":
        alt, relative_path = value
        image_path = ROOT / "docs" / "evaluation" / Path(relative_path).name
        if image_path.exists():
            p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(image_path), width=Inches(5.7))
            cap=doc.add_paragraph(alt); cap.alignment=WD_ALIGN_PARAGRAPH.CENTER
            for run in cap.runs: run.italic=True; run.font.size=Pt(8); run.font.color.rgb=RGBColor(110,120,130)
    elif kind=="table":
        if not value: continue
        table=doc.add_table(rows=1,cols=len(value[0])); table.alignment=WD_TABLE_ALIGNMENT.CENTER; table.style="Table Grid"
        for cell,txt in zip(table.rows[0].cells,value[0]): cell.text=txt
        for rowdata in value[1:]:
            cells=table.add_row().cells
            for cell,txt in zip(cells,rowdata): cell.text=txt
        for row_index,row in enumerate(table.rows):
            for cell in row.cells:
                for pp in cell.paragraphs:
                    pp.paragraph_format.space_after=Pt(2)
                    for rr in pp.runs:
                        rr.font.name="Times New Roman"; rr.font.size=Pt(8.5)
                        if row_index==0: rr.bold=True

doc.core_properties.title="Beihang SmartFind — Final Project Experiment Report"
doc.core_properties.subject="Artificial Intelligence Practice AI+X project"
doc.core_properties.author="________________________"
doc.core_properties.keywords="Beihang, SmartFind, Gemini, computer vision, multilingual retrieval"
doc.save(DOCX_OUT)

# ---------- PDF via ReportLab Platypus ----------
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
styles=getSampleStyleSheet()
body_style=ParagraphStyle("SmartBody",parent=styles["BodyText"],fontName="STSong-Light",fontSize=9.1,leading=13.2,spaceAfter=6,textColor=colors.HexColor("#243447"),alignment=TA_LEFT)
h1_style=ParagraphStyle("SmartH1",parent=styles["Heading1"],fontName="STSong-Light",fontSize=15,leading=19,spaceBefore=12,spaceAfter=8,textColor=colors.HexColor("#173B63"),keepWithNext=True)
h2_style=ParagraphStyle("SmartH2",parent=styles["Heading2"],fontName="STSong-Light",fontSize=11.5,leading=15,spaceBefore=9,spaceAfter=5,textColor=colors.HexColor("#245F91"),keepWithNext=True)
h3_style=ParagraphStyle("SmartH3",parent=styles["Heading3"],fontName="STSong-Light",fontSize=10,leading=13,spaceBefore=7,spaceAfter=4,textColor=colors.HexColor("#48627D"),keepWithNext=True)
small_style=ParagraphStyle("SmartSmall",parent=body_style,fontSize=8,leading=11,spaceAfter=3)
center_style=ParagraphStyle("SmartCenter",parent=body_style,alignment=TA_CENTER,spaceAfter=10)
cover_title=ParagraphStyle("CoverTitle",parent=center_style,fontSize=23,leading=29,textColor=colors.HexColor("#142D4E"),spaceBefore=20,spaceAfter=8)
cover_sub=ParagraphStyle("CoverSub",parent=center_style,fontSize=13,leading=18,textColor=colors.HexColor("#245F91"))

def pdf_inline(value):
    value=html.escape(value)
    value=re.sub(r"\*\*(.*?)\*\*",r"<b>\1</b>",value)
    value=re.sub(r"`(.*?)`",r"<font name='STSong-Light'>\1</font>",value)
    value=re.sub(r"\*(.*?)\*",r"<i>\1</i>",value)
    return value

story=[]
story += [Spacer(1,28*mm),Paragraph("北京航空航天大学",ParagraphStyle("cn",parent=center_style,fontSize=19,leading=25)),Spacer(1,5*mm),Paragraph("2026-2027 Academic Year, First Semester",center_style),Spacer(1,12*mm),Paragraph("《Artificial Intelligence Practice》",ParagraphStyle("course",parent=center_style,fontSize=15,leading=20)),Paragraph("FINAL PROJECT EXPERIMENT REPORT",center_style),Spacer(1,13*mm),Paragraph("Beihang SmartFind",cover_title),Paragraph("北航校园智能失物招领系统",cover_sub),Spacer(1,3*mm),Paragraph("An AI-Powered Multimodal Campus Lost-and-Found Platform",center_style),Spacer(1,16*mm)]
cover_rows=[[Paragraph("<b>Student Name</b>",small_style),Paragraph("________________________",small_style)],
            [Paragraph("<b>Student ID</b>",small_style),Paragraph("________________________",small_style)],
            [Paragraph("<b>Class</b>",small_style),Paragraph("________________________",small_style)],
            [Paragraph("<b>Grade</b>",small_style),Paragraph("________________________",small_style)]]
t=Table(cover_rows,colWidths=[35*mm,90*mm],hAlign="CENTER")
t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BOTTOMPADDING",(0,0),(-1,-1),8),("TOPPADDING",(0,0),(-1,-1),8),("LINEBELOW",(0,0),(-1,-1),0.3,colors.HexColor("#DDE5EE"))]))
story += [t,Spacer(1,18*mm),Paragraph("November 2026",center_style),PageBreak(),Paragraph("Implementation Status",h1_style),Paragraph(pdf_inline(status_note),body_style),Paragraph("Contents",h1_style)]
for entry in ["1. Creative Background","2. Selected Large Model","3. Overall Design Plan","4. Experimental Steps","5. Program Running Effect","6. Experimental Summary","7. Course Learning Summary","8. Main Reference Materials","9. Core Code Explanation"]:
    story.append(Paragraph(pdf_inline(entry),body_style))
story.append(PageBreak())
for kind,value in blocks:
    if kind=="h1":
        if value.startswith(tuple(f"{i}." for i in range(2,10))): story.append(PageBreak())
        story.append(Paragraph(pdf_inline(value),h1_style))
    elif kind=="h2": story.append(Paragraph(pdf_inline(value),h2_style))
    elif kind=="h3": story.append(Paragraph(pdf_inline(value),h3_style))
    elif kind=="p": story.append(Paragraph(pdf_inline(value),body_style))
    elif kind=="quote": story.append(Paragraph(pdf_inline(value),small_style))
    elif kind in {"ul","ol"}:
        for idx,item in enumerate(value,1):
            marker="-" if kind=="ul" else f"{idx}."
            story.append(Paragraph(f"{marker} &nbsp; {pdf_inline(item)}",body_style))
    elif kind=="image":
        alt, relative_path = value
        image_path = ROOT / "docs" / "evaluation" / Path(relative_path).name
        if image_path.exists():
            story += [Spacer(1,3),RLImage(str(image_path),width=145*mm,height=82*mm,kind="proportional"),Paragraph(pdf_inline(alt),small_style),Spacer(1,6)]
    elif kind=="table":
        if not value: continue
        data=[[Paragraph(pdf_inline(cell),small_style) for cell in row] for row in value]
        col_width=(A4[0]-36*mm)/len(data[0])
        table=Table(data,colWidths=[col_width]*len(data[0]),repeatRows=1,hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#EAF1F8")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#173B63")),("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#D7E0EA")),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        story += [Spacer(1,3),table,Spacer(1,7)]

def page_decor(canvas, doc_obj):
    canvas.saveState()
    canvas.setFont("STSong-Light",7)
    canvas.setFillColor(colors.HexColor("#8290A0"))
    canvas.drawCentredString(A4[0]/2, A4[1]-12*mm, "BEIHANG UNIVERSITY  |  ARTIFICIAL INTELLIGENCE PRACTICE")
    canvas.drawCentredString(A4[0]/2, 9*mm, f"Beihang SmartFind  |  Page {doc_obj.page}")
    canvas.restoreState()

pdf=SimpleDocTemplate(str(PDF_OUT),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=19*mm,bottomMargin=17*mm,title="Beihang SmartFind — Final Project Experiment Report",author="________________________")
pdf.build(story,onFirstPage=page_decor,onLaterPages=page_decor)

# Re-open and verify outputs.
check=Document(str(DOCX_OUT))
print({"docx":str(DOCX_OUT),"docx_paragraphs":len(check.paragraphs),"pdf":str(PDF_OUT),"docx_bytes":DOCX_OUT.stat().st_size,"pdf_bytes":PDF_OUT.stat().st_size})
