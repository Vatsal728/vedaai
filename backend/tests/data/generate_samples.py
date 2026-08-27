"""
Generate sample PDFs for testing without needing real files.
Uses reportlab to create:
- sample_question_paper.pdf (2 pages, 13 questions inc 11a/11b)
- sample_answer_sheet.pdf (4 pages, handwritten-like with diagrams placeholder)
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def create_answer_image(path, text_lines, label="Q1"):
    # Create a handwritten-like image (lined paper)
    W, H = 800, 1000
    img = Image.new("RGB", (W, H), (254, 252, 240))
    draw = ImageDraw.Draw(img)
    # lines
    for y in range(80, H, 28):
        draw.line([(40, y), (W-20, y)], fill=(180, 200, 255), width=1)
    # margin
    draw.line([(60, 20), (60, H-20)], fill=(255, 150, 150), width=2)
    draw.line([(65, 20), (65, H-20)], fill=(255, 180, 180), width=1)
    # Try font
    try:
        font = ImageFont.truetype("arial.ttf", 22)
        small = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small = font
    y = 90
    draw.text((80, 40), label, fill=(20, 20, 120), font=font)
    for line in text_lines:
        draw.text((80, y), line, fill=(20, 40, 120), font=small)
        y += 30
        if y > H-50:
            break
    # simple diagram for Q1
    if "Photosynthesis" in " ".join(text_lines):
        # draw plant
        draw.ellipse([350, 300, 450, 360], outline=(255,180,0), width=2)  # sun
        for r in [[380,360,380,420],[370,380,360,400],[390,380,400,400]]:
            draw.line(r, fill=(255,180,0), width=1)
        # plant
        draw.line([400,420,400,550], fill=(60,120,40), width=3)
        draw.ellipse([370,430,390,460], fill=None, outline=(40,100,30), width=2)
        draw.ellipse([410,440,440,470], fill=None, outline=(40,100,30), width=2)
        draw.line([350,460,370,450], fill=(40,100,30), width=1)
        draw.line([440,460,470,450], fill=(40,100,30), width=1)
        draw.text((300,470), "Carbon", fill=(20,40,120), font=small)
        draw.text((290,490), "dioxide", fill=(20,40,120), font=small)
        draw.text((500,470), "Oxygen", fill=(20,40,120), font=small)
        draw.text((470,570), "Water", fill=(20,40,120), font=small)
        # equation box
        draw.rectangle([80,200,720,260], outline=(40,40,100), width=2)
        draw.text((120,210), "6CO2 + 6H2O  --Light/Chlorophyll-->  C6H12O6 + 6O2", fill=(20,20,100), font=small)
    img.save(path, "JPEG", quality=90)

def build_question_paper():
    out = os.path.join(OUT_DIR, "sample_question_paper.pdf")
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=18*mm, bottomMargin=15*mm, leftMargin=15*mm, rightMargin=15*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle('title', parent=styles['Title'], fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor("#B45309"))
    heading = ParagraphStyle('heading', parent=styles['Heading2'], fontSize=10, textColor=colors.HexColor("#333333"))
    qstyle = ParagraphStyle('q', parent=styles['Normal'], fontSize=9, leading=13, alignment=TA_LEFT, spaceAfter=6)
    story = []
    story.append(Paragraph("DELHI PUBLIC SCHOOL - BOKARO STEEL CITY", heading))
    story.append(Paragraph("Class 10 - Science (Biology) - Unit Test", title))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Time: 1 Hour &nbsp;&nbsp;&nbsp;&nbsp; Max Marks: 40 &nbsp;&nbsp;&nbsp;&nbsp; Instructions: Answer all questions.", styles['Normal']))
    story.append(Spacer(1, 10))
    questions = [
        ("1", None, "Which blood vessel carries blood away from the heart? &nbsp; [2]"),
        ("2", None, "Which of the following organelles is primarily involved in photosynthesis? &nbsp; [2]"),
        ("3", None, "Explain the role of chloroplasts in photosynthesis, naming the main pigments involved and briefly outlining the two major stages of the process. &nbsp; [2]"),
        ("4", None, "Describe the flow of blood through the human heart starting from the right atrium and ending at the aorta; include the names of valves crossed. &nbsp; [2]"),
        ("5", None, "Draw a labelled diagram of an alveolus showing capillaries and air space (label alveolar sac, capillary, and direction of gas exchange). &nbsp; [2]"),
        ("6", None, "Draw a neat labelled diagram of the human digestive system (stomach, small intestine, large intestine, liver, pancreas) and label the site where most absorption occurs. &nbsp; [5]"),
        ("7", None, "Draw and label a nephron (Bowman's capsule, glomerulus, proximal tubule, loop of Henle, distal tubule, collecting duct). &nbsp; [5]"),
        ("8", None, "Explain the structural differences between palisade mesophyll and spongy mesophyll and state how each structure aids its function in the leaf. &nbsp; [5]"),
        ("9", None, "Describe the process of transpiration in plants in two to three sentences and name two environmental factors that increase its rate. &nbsp; [5]"),
        ("10", None, "Explain how the structure of xylem vessels facilitates water transport in plants (mention one structural feature and its role). &nbsp; [4]"),
        ("11", "a", "A diagram shows two potted plants — Plant A in bright light with broad green leaves, Plant B kept in dim light with pale, elongated leaves. &nbsp; [2]"),
        ("11", "b", "Suggest one practical measure to help Plant B recover. &nbsp; [3]"),
        ("12", None, "A resting person has tidal volume (air per breath) of 0.5 L and breathes 12 times per minute. &nbsp; [5]"),
        ("13", None, "If dead space is 0.15 L per breath, calculate the alveolar ventilation per minute. Show working. &nbsp; [5]"),
    ]
    for label, sub, txt in questions:
        if sub:
            story.append(Paragraph(f"<b>{label} ({sub})</b> &nbsp; {txt}", qstyle))
        else:
            story.append(Paragraph(f"<b>{label}.</b> &nbsp; {txt}", qstyle))
        if label in ["5","7","10"]:
            # add extra space after diagram questions
            story.append(Spacer(1, 8))
    story.append(Spacer(1, 12))
    story.append(Paragraph("— End of Question Paper —", ParagraphStyle('end', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, textColor=colors.grey)))
    doc.build(story)
    print(f"Created {out} ({os.path.getsize(out)} bytes)")
    return out

def build_answer_sheet():
    out = os.path.join(OUT_DIR, "sample_answer_sheet.pdf")
    # Generate 4 pages of lined answer images then embed into PDF
    tmp_imgs = []
    pages_data = [
        ("Q1.", ["Photosynthesis is the process used by", "green plants and some other organisms", "to convert light energy into chemical", "energy.", "", "6CO2 + 6H2O  ->  C6H12O6 + 6O2", "(diagram below)"]),
        ("Q2.", ["The process mainly occurs in the", "chloroplast of the plant cell. It has", "two main stages:", "1. Light reaction - Captures light energy.", "2. Dark reaction - Uses energy to", "   make glucose."]),
        ("Q3.", ["Chloroplasts contain chlorophyll a and b.", "Light reaction in thylakoid captures", "energy, Dark reaction in stroma makes", "glucose. Pigments capture light."]),
        ("Q5.", ["Diagram of alveolus:", " - Alveolar sac", " - Capillary network", " - Direction of gas exchange (arrow)", " (neat diagram drawn)"]),
    ]
    # We'll create 4 images, 1 per page, but to test multi-page we make Q1 span 1 page, Q2 second, etc.
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer

    # First create image files
    img_dir = os.path.join(OUT_DIR, "tmp_answer_imgs")
    os.makedirs(img_dir, exist_ok=True)
    img_paths = []
    for idx, (label, lines) in enumerate(pages_data):
        p = os.path.join(img_dir, f"ans_{idx}.jpg")
        create_answer_image(p, lines, label=label)
        img_paths.append(p)

    # Now build PDF embedding those images
    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=10*mm, bottomMargin=10*mm, leftMargin=10*mm, rightMargin=10*mm)
    story = []
    for p in img_paths:
        # scale to fit
        story.append(RLImage(p, width=170*mm, height=220*mm))
        story.append(Spacer(1, 5))
    doc.build(story)
    print(f"Created {out} ({os.path.getsize(out)} bytes)")
    return out

def build_single_images():
    # Also create a single png for quick upload test
    img_dir = OUT_DIR
    p = os.path.join(img_dir, "sample_question_page.png")
    # reuse create_answer_image for question style but simple
    create_answer_image(p, ["Q1. Which blood vessel carries blood away from heart?", "A) Vein B) Artery C) Capillary", "Answer: Artery", "", "Q2. Which organelle for photosynthesis?", "Answer: Chloroplast"], label="Sample Q Paper (Image)")
    print(f"Created {p}")
    return p

if __name__ == "__main__":
    qp = build_question_paper()
    ans = build_answer_sheet()
    img = build_single_images()
    print("Done. Files in", OUT_DIR)
    for f in [qp, ans, img]:
        print(" -", f, os.path.getsize(f))
