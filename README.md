# StudyFlow 2.0 — Cloud-Based Smart Study Planner

A beautiful, feature-rich academic planning system built with Python Flask.

## Features
- ✅ Smart exam timetable import (auto-detects dates & subjects)
- ✅ Unavailable date marking with auto-redistribution
- ✅ Syllabus auto-detection (units, chapters, topics)
- ✅ Balanced daily subject mixing (all subjects every day)
- ✅ Routine-aware scheduling (calculates real free hours)
- ✅ Hour-by-hour daily timetable
- ✅ Full month-by-month calendar view
- ✅ Task completion tracking with live progress bars
  

## Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
# Visit http://localhost:5000
```



## Project Structure
```
studyflow/
├── app.py              # Flask backend + schedule generation logic
├── app.yaml            # Google App Engine config
├── requirements.txt    # Python dependencies
└── templates/
    ├── index.html      # Landing page
    ├── planner.html    # 5-step schedule creation wizard
    └── calendar.html   # Calendar view + task tracking
```

## How It Works
1. **Step 1 — Dates**: Set study start/end dates, mark unavailable days
2. **Step 2 — Exams**: Paste your exam timetable (any format)
3. **Step 3 — Subjects**: Add subjects with color-coded syllabus parsing
4. **Step 4 — Routine**: Enter wake time, sleep hours, college schedule
5. **Step 5 — Generate**: Get your complete personalized schedule

The backend calculates:
- Available study days (excluding exams and unavailable dates)
- Free hours per day (24 - sleep - college - meals - other)
- Balanced subject distribution (equal time per subject per day)
- Hour-by-hour daily timetables with correct wake/sleep timing
