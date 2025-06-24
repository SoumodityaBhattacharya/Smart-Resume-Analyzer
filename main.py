from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from courses import resume_videos, interview_videos
import random
import os
import shutil
import fitz  # PyMuPDF
import docx
import re
import spacy
from pytube import YouTube
app = FastAPI()

UPLOAD_DIR = "uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/pdfs", StaticFiles(directory=UPLOAD_DIR), name="pdfs")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/static_2", StaticFiles(directory="static_2"), name="static_2")

templates = Jinja2Templates(directory="templates")



@app.get("/", response_class=HTMLResponse)
async def show_upload_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def show_resume_tips(resume_text):
    Score = 0
    tips = []
    # resume_text = resume_text.lower()

    if 'Objective' in resume_text or 'OBJECTIVE' in resume_text:
        Score += 20
        tips.append(("positive", "[+] Awesome! You have added Objective 💡"))
    else:
        tips.append(("warning", "[-] Please add your career objective. It shows your career intention to recruiters."))

    if 'About' in resume_text or 'ABOUT' in resume_text:
        Score += 20
        tips.append(("positive", "[+] Awesome! You have added information about you. ✍"))
    else:
        tips.append(("warning", "[-] Please add a 'About Me' section. It shows authenticity of your resume."))

    if 'Experience' in resume_text or 'EXPERIENCE' in resume_text:
        Score += 20
        tips.append(("positive", "[+] Awesome! You have added your work experience."))
    else:
        tips.append(("warning", "[-] Please add Work Experience."
        " It helps recruiters to understand your Relevnat Skills and whether your fast experience fits their role or company domain."))

    if 'Achievements' in resume_text or 'ACHIEVEMENTS' in resume_text:
        Score += 20
        tips.append(("positive", "[+] Awesome! You have added your Achievements 🏅"))
    else:
        tips.append(("warning", "[-] Please add Achievements. It shows you're capable for the position."))

    if 'Projects' in resume_text or 'PROJECTS' in resume_text :
        Score += 20
        tips.append(("positive", "[+] Awesome! You have added Projects 👨‍💻"))
    else:
        tips.append(("warning", "[-] Please add Projects. It highlights relevant work experience."))

    return {
        "Score": Score,
        "Tips": tips
    }

def extract_name_from_text(text):
    lines = text.split('\n')
    potential_names = []

    blacklist = {'profile', 'education', 'experience', 'skills', 'summary', 
                 'projects', 'certifications', 'interests', 'contact', 'work history'}

    for line in lines[:10]:  # Focus on top 10 lines for performance and accuracy
        clean_line = line.strip()

        if not clean_line or clean_line.lower() in blacklist:
            continue

        if (
            re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$", clean_line) or
            re.match(r"^[A-Z]+\s[A-Z]+$", clean_line) or
            re.match(r"^[a-z]+\s[a-z]+$", clean_line) or
            re.match(r"^[A-Z]\.\s?[A-Z][a-z]+$", clean_line) or
            re.match(r"^[A-Z][a-z]+[A-Z][a-z]+$", clean_line)
        ):
            potential_names.append(clean_line)

        if re.fullmatch(r"[A-Z\s]+", line) and clean_line.lower() not in blacklist:
            cleaned = re.sub(r"\s{2,}", " ", clean_line)
            potential_names.append(cleaned)

    if potential_names:
        return max(potential_names, key=lambda x: len(x.split()) + len(x))

    # 🔁 Use spaCy NER as fallback
    try:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
    except Exception:
        pass

    return None

def extract_resume_details(text):
    name = extract_name_from_text(text)
    email = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    phone = re.search(r'(\+?\d[\d -]{8,}\d)', text)

    skill_keywords = [
        "python", "java", "C++", "C", "sql", "javascript", "html", "css", "Django",
        "aws", "docker", "kubernetes", "git", "linux", "react", "node.js", "Flask"
        "machine learning", "data analysis", "excel", "tensorflow", "pandas"
    ]

    course_recommendations = {
        "python": [("Python for Beginners – Coursera", "https://www.coursera.org/learn/python")],
        "Java": [("Free Java Course Online - (GeeksforGeeks)","https://www.geeksforgeeks.org/courses/free-java-course-online"),
                 ("Free Java Course with Certificate - (Scaler)","https://www.scaler.com/topics/course/java-beginners/")],
        "JavaScript":[("Free JavaScript Course with Certification - (Scaler)","https://www.scaler.com/topics/course/javascript-beginners/"),
                      ("JavaScript Full Course for Free - (YouTube)","https://www.youtube.com/watch?v=lfmg-EJ8gm4")],
        "C++":[("Free C++ Course with Certificate - (GeeksforGeeks)","https://www.geeksforgeeks.org/courses/free-cpp-course-online-certification"),
               ("C++ Tutorial for Complete Beginners - (Udemy, free) ","https://www.udemy.com/course/free-learn-c-tutorial-beginners/")],
        "Node.js":[("Free Node.js Crash Course - (YouTube via freeCodeCamp)","https://youtu.be/tPavCLJp0Cc")],
        "Django":[("Free Django Course with Certificate - (SkillUp/Simplilearn)"," https://www.simplilearn.com/free-python-django-course-skillup")],
        "Flask":[("Free Flask Video Tutorial - (Udemy)","https://www.udemy.com/course/python-flask-for-beginners/")],
        "machine learning": [("Machine Learning by Andrew Ng – Coursera", "https://www.coursera.org/learn/machine-learning")],
        "sql": [("SQL for Data Science – Coursera", "https://www.coursera.org/learn/sql-for-data-science")],
        "excel": [("Excel Skills for Business – Coursera", "https://www.coursera.org/specializations/excel")],
        "git": [("Git & GitHub Crash Course – Udemy", "https://www.udemy.com/course/git-and-github-crash-course/")],
        "docker": [("Docker Essentials – Pluralsight", "https://www.pluralsight.com/courses/docker-getting-started")],
        "react": [("React - The Complete Guide – Udemy", "https://www.udemy.com/course/react-the-complete-guide-incl-redux/")],
        "linux": [("Linux Command Line Basics – edX", "https://www.edx.org/course/introduction-to-linux")]
    }

    found_skills = [skill for skill in skill_keywords if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE)]
    missing_skills = [skill for skill in course_recommendations if skill not in found_skills]
    recommended_courses = {skill: course_recommendations[skill] for skill in missing_skills}

    return {
        "name": name,
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
        "skills": found_skills,
        "recommended_courses": recommended_courses
    }



@app.post("/analyze-resume", response_class=HTMLResponse)
async def analyze_resume(request: Request, file: UploadFile = File(...)):
    file_location = f"{UPLOAD_DIR}/{file.filename}"
    
    with open(file_location, "wb") as f:
        shutil.copyfileobj(file.file, f)

    ext = os.path.splitext(file.filename)[1].lower()
    
    try:
        if ext == ".pdf":
            text = extract_text_from_pdf(file_location)
        elif ext == ".docx":
            text = extract_text_from_docx(file_location)
        else:
            return templates.TemplateResponse("reupload.html", {"request": request})

        parsed_info = extract_resume_details(text)
        res_score = show_resume_tips(text)
        resume_video_data = random.choice(resume_videos)
        res_video_link = resume_video_data["link"]
        res_video_title = resume_video_data["title"]
        interview_video_data = random.choice(interview_videos)
        interview_video_link = interview_video_data["link"]
        interview_video_title = interview_video_data["title"]

        return templates.TemplateResponse("result.html", {
            "request": request,
            "filename": file.filename if ext == ".pdf" else None,
            "details": parsed_info ,   
            "Score": res_score,
            "res_video_title": res_video_title,
            "res_video_link": res_video_link,
            "interview_video_link": interview_video_link,
            "interview_video_title": interview_video_title
        })

    except Exception as e:
        return HTMLResponse(content=f"<h3>Error during analysis: {str(e)}</h3>")
