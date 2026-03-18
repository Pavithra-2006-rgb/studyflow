import os
from flask import Flask, render_template, request, jsonify, session
import re, hashlib, json
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'studyflow_mysql_secret_2024'

# ═══════════════════════════════════════════════════════════════
# DATABASE CONFIG  — edit DB_CONFIG to match your MySQL setup
# ═══════════════════════════════════════════════════════════════
DB_CONFIG = {
    'host':     'localhost',
    'user':     'root',
    'password': 'pavi@2006',   # ← CHANGE THIS
    'database': 'studyflow',
    'charset':  'utf8mb4',
}

def get_db():
    import mysql.connector
    return mysql.connector.connect(**DB_CONFIG)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in', 'redirect': '/login'}), 401
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/planner')
def planner():
    return render_template('planner.html')

@app.route('/calendar')
def calendar_view():
    return render_template('calendar.html')

# ═══════════════════════════════════════════════════════════════
# AUTH API
# ═══════════════════════════════════════════════════════════════

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data     = request.json
    username = data.get('username','').strip()
    name     = data.get('name','').strip()
    password = data.get('password','')
    if not username or not name or not password:
        return jsonify({'error': 'All fields are required.'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters.'}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username: letters, numbers and _ only.'}), 400
    try:
        db  = get_db(); cur = db.cursor(dictionary=True)
        cur.execute('SELECT id FROM users WHERE username=%s', (username,))
        if cur.fetchone():
            db.close(); return jsonify({'error': 'Username already taken.'}), 400
        cur.execute('INSERT INTO users (username, full_name, password) VALUES (%s,%s,%s)',
                    (username, name, hash_pw(password)))
        db.commit(); user_id = cur.lastrowid; db.close()
        session['user_id'] = user_id
        session['username'] = username
        session['full_name'] = name
        return jsonify({'success': True, 'name': name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data     = request.json
    username = data.get('username','').strip()
    password = data.get('password','')
    if not username or not password:
        return jsonify({'error': 'Please fill in all fields.'}), 400
    try:
        db  = get_db(); cur = db.cursor(dictionary=True)
        cur.execute('SELECT * FROM users WHERE username=%s AND password=%s',
                    (username, hash_pw(password)))
        user = cur.fetchone(); db.close()
        if not user:
            return jsonify({'error': 'Incorrect username or password.'}), 401
        session['user_id']   = user['id']
        session['username']  = user['username']
        session['full_name'] = user['full_name']
        return jsonify({'success': True, 'name': user['full_name']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/auth/me', methods=['GET'])
def api_me():
    if 'user_id' in session:
        return jsonify({'logged_in': True,
                        'name': session.get('full_name'),
                        'username': session.get('username')})
    return jsonify({'logged_in': False})

# ═══════════════════════════════════════════════════════════════
# SCHEDULE SAVE / LOAD (per user in MySQL)
# ═══════════════════════════════════════════════════════════════

@app.route('/api/schedule/delete', methods=['POST'])
@login_required
def delete_schedule():
    try:
        db  = get_db(); cur = db.cursor()
        cur.execute('DELETE FROM schedules WHERE user_id=%s', (session['user_id'],))
        db.commit(); db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/save', methods=['POST'])
@login_required
def save_schedule():
    sched_json = json.dumps(request.json.get('schedule', {}))
    try:
        db  = get_db(); cur = db.cursor()
        cur.execute('''INSERT INTO schedules (user_id, schedule_json)
            VALUES (%s,%s) ON DUPLICATE KEY UPDATE schedule_json=%s, updated_at=NOW()''',
            (session['user_id'], sched_json, sched_json))
        db.commit(); db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/load', methods=['GET'])
@login_required
def load_schedule():
    try:
        db  = get_db(); cur = db.cursor(dictionary=True)
        cur.execute('SELECT schedule_json, updated_at FROM schedules WHERE user_id=%s',
                    (session['user_id'],))
        row = cur.fetchone(); db.close()
        if row:
            return jsonify({'found': True,
                            'schedule': json.loads(row['schedule_json']),
                            'saved_at': str(row['updated_at'])})
        return jsonify({'found': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/completion/save', methods=['POST'])
@login_required
def save_completion():
    data = request.json
    done = 1 if data.get('completed') else 0
    try:
        db  = get_db(); cur = db.cursor()
        cur.execute('''INSERT INTO completions (user_id, date_str, subject, completed)
            VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE completed=%s''',
            (session['user_id'], data.get('date'), data.get('subject'), done, done))
        db.commit(); db.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/completion/load', methods=['GET'])
@login_required
def load_completions():
    try:
        db  = get_db(); cur = db.cursor(dictionary=True)
        cur.execute('SELECT date_str, subject, completed FROM completions WHERE user_id=%s',
                    (session['user_id'],))
        rows = cur.fetchall(); db.close()
        comp = {f"{r['date_str']}|{r['subject']}": bool(r['completed']) for r in rows}
        return jsonify({'completions': comp})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ═══════════════════════════════════════════════════════════════
# SCHEDULE GENERATION
# ═══════════════════════════════════════════════════════════════

@app.route('/api/generate_schedule', methods=['POST'])
def generate_schedule():
    data              = request.json
    start_date_str    = data.get('start_date')
    end_date_str      = data.get('end_date')
    exam_timetable    = data.get('exam_timetable', '')
    unavailable_dates = data.get('unavailable_dates', [])
    unavailable_hours = data.get('unavailable_hours', [])   # NEW
    subjects          = data.get('subjects', [])
    routine           = data.get('routine', {})

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date   = datetime.strptime(end_date_str,   '%Y-%m-%d')
    exam_days  = parse_exam_timetable(exam_timetable)

    # Build unavailable_hours lookup: date → [{from_min, to_min, reason}]
    uh_map = {}
    for uh in unavailable_hours:
        d = uh.get('date')
        if not d: continue
        fh, fm = parse_time(uh.get('from', '00:00'))
        th, tm = parse_time(uh.get('to',   '00:00'))
        uh_map.setdefault(d, []).append({
            'from_min': fh*60+fm, 'to_min': th*60+tm,
            'reason':   uh.get('reason', 'Personal'),
        })

    all_days = []
    d = start_date
    while d <= end_date:
        ds       = d.strftime('%Y-%m-%d')
        day_type = 'study'; exam_subjects = []
        for ex in exam_days:
            if ex['date'] == ds:
                day_type = 'exam'; exam_subjects.append(ex['subject'])
        if ds in unavailable_dates:
            day_type = 'unavailable'
        all_days.append({'date': ds, 'day_type': day_type,
                         'exam_subjects': exam_subjects, 'weekday': d.strftime('%A'),
                         'blocked_hours': uh_map.get(ds, [])})
        d += timedelta(days=1)

    for subj in subjects:
        subj['units']            = parse_syllabus(subj.get('syllabus',''))
        total_topics             = sum(u['topic_count'] for u in subj['units'])
        subj['total_topics']     = max(total_topics, 1)
        subj['needed_hours']     = max(total_topics, 1)
        subj['completed_topics'] = 0

    free_hours          = calculate_free_hours(routine)
    subject_daily_hours = compute_proportional_hours(subjects, free_hours)
    study_days          = [d for d in all_days if d['day_type'] == 'study']
    schedule            = assign_study_tasks(study_days, subjects, subject_daily_hours,
                                             free_hours, routine)
    sched_map = {s['date']: s for s in schedule}

    for day in all_days:
        if day['date'] in sched_map:
            day.update(sched_map[day['date']])
            # If this study day has partial blocked hours, rebuild its timetable
            if day['blocked_hours']:
                day['hourly'] = build_partial_day_timetable(
                    day, day['blocked_hours'], routine, subjects)
        elif day['day_type'] == 'unavailable':
            day['hourly']     = build_unavailable_routine(routine, subjects, subject_daily_hours)
            day['tasks']      = []
            day['free_hours'] = 0

    return jsonify({
        'days': all_days, 'subjects': subjects,
        'free_hours_per_day': free_hours,
        'subject_daily_hours': subject_daily_hours,
        'routine': routine, 'exam_days': exam_days,
        'total_study_days': len(study_days),
    })


@app.route('/api/parse_syllabus', methods=['POST'])
def api_parse_syllabus():
    units = parse_syllabus(request.json.get('text',''))
    return jsonify({'units': units})


# ═══════════════════════════════════════════════════════════════
# SCHEDULING HELPERS
# ═══════════════════════════════════════════════════════════════

def compute_proportional_hours(subjects, free_hours):
    if not subjects: return {}
    total = sum(s.get('needed_hours',1) for s in subjects) or len(subjects)
    usable = free_hours * 0.90
    result = {s['name']: round(max(0.5, min(3.5, usable * s.get('needed_hours',1)/total)), 1)
              for s in subjects}
    tot = sum(result.values())
    if tot > free_hours:
        result = {k: round(v * free_hours/tot, 1) for k,v in result.items()}
    return result

def calculate_free_hours(routine):
    try:
        return max(24 - float(routine.get('sleep_hours',7))
                      - float(routine.get('college_hours',6))
                      - float(routine.get('meal_hours',1.5))
                      - float(routine.get('other_hours',1)), 2.0)
    except: return 6.0

def assign_study_tasks(study_days, subjects, subject_daily_hours, free_hours, routine):
    if not subjects or not study_days: return []
    wake_h,wake_m = parse_time(routine.get('wake_time','06:00'))
    col_h,col_m   = parse_time(routine.get('college_start','09:00'))
    col_hrs  = float(routine.get('college_hours',6))
    sleep_hrs= float(routine.get('sleep_hours',7))
    meal_hrs = float(routine.get('meal_hours',1.5))
    result = []
    for day in study_days:
        tasks = [{'subject':s['name'],'color':s.get('color','#2563eb'),
                  'hours':subject_daily_hours.get(s['name'],1.0),
                  'completed':False,'needed_hours':s.get('needed_hours',1)}
                 for s in subjects]
        hourly = build_hourly_timetable(wake_h,wake_m,col_h,col_m,col_hrs,sleep_hrs,meal_hrs,tasks)
        result.append({'date':day['date'],'tasks':tasks,'hourly':hourly,'free_hours':free_hours})
    return result

def build_hourly_timetable(wake_h,wake_m,col_h,col_m,col_dur,sleep_hrs,meal_hrs,tasks):
    blocks=[]; cur=wake_h*60+wake_m
    def fmt(m): return f"{(m//60)%24:02d}:{m%60:02d}"
    def add(t,act,dur,bt,sub=None,col=None):
        b={'time':fmt(t),'activity':act,'duration':dur,'type':bt}
        if sub: b['subject']=sub
        if col: b['color']=col
        blocks.append(b); return t+dur
    col_start  = col_h*60+col_m
    sleep_start= min(wake_h*60+wake_m+int((24-sleep_hrs)*60), 23*60+30)
    dinner_s   = sleep_start-75; wind_s=sleep_start-30
    cur=add(cur,'🌅 Wake Up & Morning Routine',30,'routine')
    bfast=max(col_start-30,cur+30); mwin=bfast-cur
    tmin={t['subject']:int(t['hours']*60) for t in tasks}
    if mwin>=45:
        bud=mwin
        for t in tasks:
            if bud<30: break
            av=min(tmin.get(t['subject'],0),bud,90)
            if av>=30:
                cur=add(cur,f"📖 Morning Study: {t['subject']}",av,'study',t['subject'],t.get('color'))
                tmin[t['subject']]-=av; bud-=av
                if bud>=20: cur=add(cur,'☕ Short Break',10,'break'); bud-=10
    cur=add(bfast,'🍳 Breakfast',30,'meal')
    cur=add(col_start,'🏫 College / Classes',int(col_dur*60),'college')
    cur=add(cur,'🍱 Lunch Break',45,'meal')
    awin=dinner_s-cur
    if awin>=30:
        for t in tasks:
            rem=tmin.get(t['subject'],0)
            if rem<=0: continue
            av=min(rem,awin)
            if av<15: continue
            cur=add(cur,f"📚 Study: {t['subject']}",av,'study',t['subject'],t.get('color'))
            tmin[t['subject']]-=av; awin-=av
            if awin>=25: cur=add(cur,'☕ Short Break',15,'break'); awin-=15
    if cur<dinner_s-10: cur=add(cur,'🎵 Free Time / Relax',dinner_s-cur,'free')
    cur=add(dinner_s,'🍽️ Dinner',45,'meal')
    if wind_s>cur: cur=add(wind_s,'🌙 Wind Down / Personal Time',30,'routine')
    add(sleep_start,'😴 Sleep',int(sleep_hrs*60),'sleep')
    return blocks

def build_partial_day_timetable(day_data, blocked_hours, routine, subjects):
    """Study day with some hours blocked — smart scheduling around the blocked window."""
    wake_h,wake_m = parse_time(routine.get('wake_time','06:00'))
    sleep_hrs     = float(routine.get('sleep_hours',7))
    blocks        = []; wake_start=wake_h*60+wake_m
    sleep_start   = min(wake_start+int((24-sleep_hrs)*60),23*60+30)
    dinner_s      = sleep_start-75; wind_s=sleep_start-30
    def fmt(m): return f"{(m//60)%24:02d}:{m%60:02d}"
    def add(t,act,dur,bt,sub=None,col=None):
        b={'time':fmt(t),'activity':act,'duration':dur,'type':bt}
        if sub: b['subject']=sub
        if col: b['color']=col
        blocks.append(b); return t+dur
    bw          = sorted(blocked_hours, key=lambda x: x['from_min'])
    total_blk   = sum(max(0,b['to_min']-b['from_min']) for b in bw)
    study_tasks = day_data.get('tasks',[])
    # Reduce study time proportional to how much of the day is blocked
    tmin = {t['subject']: max(int(t['hours']*60*(1-total_blk/480)),30) for t in study_tasks}
    emojis={'wedding':'💒','marriage':'💒','travel':'✈️','temple':'🛕',
            'hospital':'🏥','function':'🎊','party':'🎉','personal':'🙏','outing':'🚗'}
    cur = wake_start
    cur = add(cur,'🌅 Wake Up & Morning Routine',30,'routine')
    cur = add(cur,'🍳 Breakfast',30,'meal')
    for bk in bw:
        bf=bk['from_min']; bt2=bk['to_min']; rsn=bk['reason']
        icon=next((v for k,v in emojis.items() if k in rsn.lower()),'📌')
        # Study before block
        win_before=bf-cur
        if win_before>=45:
            for t in study_tasks:
                rem=tmin.get(t['subject'],0)
                av=min(rem,win_before-15,90)
                if av>=30:
                    cur=add(cur,f"📚 Study: {t['subject']}",av,'study',t['subject'],t.get('color'))
                    tmin[t['subject']]-=av; win_before-=av
                    if win_before>20: cur=add(cur,'☕ Break',10,'break'); win_before-=10
        # Get ready
        if bf-cur>=30: cur=add(bf-30,f"👔 Get Ready for {rsn}",30,'routine')
        # Blocked event
        cur=add(bf,f"{icon} {rsn}",bt2-bf,'blocked')
        # Rest after
        if bt2+30<=dinner_s: cur=add(bt2,'🛋️ Rest & Freshen Up',30,'free')
        else: cur=bt2
    # Afternoon study after all blocked windows
    awin=dinner_s-cur
    if awin>=30:
        for t in study_tasks:
            rem=tmin.get(t['subject'],0)
            if rem<=0: continue
            av=min(rem,awin)
            if av<20: continue
            cur=add(cur,f"📖 Study: {t['subject']}",av,'study',t['subject'],t.get('color'))
            tmin[t['subject']]-=av; awin-=av
            if awin>=20: cur=add(cur,'☕ Short Break',15,'break'); awin-=15
    # Guarantee at least 1h study
    studied=sum(b['duration'] for b in blocks if b['type']=='study')
    if studied<60 and dinner_s-cur>=60 and study_tasks:
        t=study_tasks[0]
        cur=add(cur,f"📖 Revision: {t['subject']}",60,'study',t['subject'],t.get('color'))
    if cur<dinner_s-10: cur=add(cur,'🎵 Free Time',dinner_s-cur,'free')
    cur=add(dinner_s,'🍽️ Dinner',45,'meal')
    if wind_s>cur: cur=add(wind_s,'🌙 Wind Down',30,'routine')
    add(sleep_start,'😴 Sleep',int(sleep_hrs*60),'sleep')
    return blocks

def build_unavailable_routine(routine, subjects=None, subject_daily_hours=None):
    """
    Full unavailable day routine.
    - Morning: wake, breakfast, get ready, head out
    - Daytime: OUT (event/personal) — blocked
    - Evening: Return home, rest 30m, then FILL ALL remaining free time with study
      (not just 1h — if 3h free after returning, do 3h study)
    - Then dinner, wind down, sleep
    """
    wake_h, wake_m = parse_time(routine.get('wake_time', '06:00'))
    sleep_hrs      = float(routine.get('sleep_hours', 7))
    blocks         = []
    wake_s         = wake_h * 60 + wake_m
    sleep_s        = min(wake_s + int((24 - sleep_hrs) * 60), 23 * 60 + 30)
    dinner_s       = sleep_s - 75
    wind_s         = sleep_s - 30

    def fmt(m):
        return f"{(m//60)%24:02d}:{m%60:02d}"

    def add(t, act, dur, bt, sub=None, col=None):
        b = {'time': fmt(t), 'activity': act, 'duration': dur, 'type': bt}
        if sub: b['subject'] = sub
        if col: b['color']   = col
        blocks.append(b)
        return t + dur

    cur = wake_s

    # Morning — wake, breakfast, get ready, leave
    cur = add(cur, '🌅 Wake Up & Morning Routine', 30, 'routine')
    cur = add(cur, '🍳 Breakfast',                  30, 'meal')
    cur = add(cur, '👔 Get Ready & Head Out',        30, 'routine')

    # OUT for the day — assume person is out until ~3h before dinner
    # This leaves enough time to rest + study after returning
    return_time  = dinner_s - 180      # return 3h before dinner
    out_duration = return_time - cur
    if out_duration > 0:
        cur = add(cur, '🎉 Out — Personal / Event / Activity', out_duration, 'blocked')

    # Return home — rest 30m
    cur = add(return_time, '🛋️ Return Home & Rest', 30, 'free')

    # ── Fill ALL remaining free time with study ───────────────────
    # Window available for study = from now until dinner (minus a short free wind-down)
    free_wind = 20  # keep 20m gap before dinner as buffer
    study_window = dinner_s - cur - free_wind

    if study_window >= 30:
        # If we have subjects, cycle through them to fill the window
        if subjects:
            task_list  = [{'subject': s['name'], 'color': s.get('color','#2563eb'),
                           'hours': (subject_daily_hours or {}).get(s['name'], 1.0)}
                          for s in subjects]
            # Reduce hours to 60% on an off day (less intense)
            tmin       = {t['subject']: max(int(t['hours']*60*0.6), 30) for t in task_list}
            remaining  = study_window
            first      = True

            for t in task_list:
                if remaining < 25: break
                rem = tmin.get(t['subject'], 0)
                av  = min(rem, remaining, 90)   # max 90m per session
                if av < 25: continue

                if not first and remaining >= av + 15:
                    cur = add(cur, '☕ Short Break', 15, 'break')
                    remaining -= 15

                label = '📖 Light Revision' if first else '📚 Study'
                cur   = add(cur, f"{label}: {t['subject']}", av, 'study',
                            t['subject'], t.get('color'))
                tmin[t['subject']] -= av
                remaining -= av
                first = False

                # If more time left and subject still has content, do another round
                if remaining >= 30 and tmin.get(t['subject'], 0) > 0:
                    if remaining >= av + 15:
                        cur = add(cur, '☕ Short Break', 15, 'break')
                        remaining -= 15
                    av2 = min(tmin[t['subject']], remaining, 60)
                    if av2 >= 25:
                        cur = add(cur, f"📚 Continued: {t['subject']}", av2, 'study',
                                  t['subject'], t.get('color'))
                        remaining -= av2
        else:
            # No subjects info — generic revision block filling the whole window
            sessions = study_window // 75   # 60m study + 15m break
            remaining = study_window
            for i in range(max(sessions, 1)):
                if remaining < 30: break
                slot = min(60, remaining)
                cur  = add(cur, f"📖 Light Revision (Session {i+1})", slot, 'study')
                remaining -= slot
                if remaining >= 20:
                    cur = add(cur, '☕ Short Break', 15, 'break')
                    remaining -= 15

    # Small free gap before dinner if any time left
    if dinner_s - cur > 10:
        cur = add(cur, '🎵 Unwind / Free Time', dinner_s - cur, 'free')

    cur = add(dinner_s, '🍽️ Dinner',    45, 'meal')
    if wind_s > cur:
        cur = add(wind_s, '🌙 Wind Down', 30, 'routine')
    add(sleep_s, '😴 Sleep', int(sleep_hrs * 60), 'sleep')

    return blocks

def parse_time(s):
    try: h,m=map(int,str(s).split(':')); return h,m
    except: return 6,0

def parse_exam_timetable(text):
    if not text: return []
    pats=[r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',r'(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})',
          r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})',
          r'(\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4})']
    result=[]
    for line in text.strip().split('\n'):
        line=line.strip()
        if not line: continue
        fd=None
        for p in pats:
            m=re.search(p,line,re.IGNORECASE)
            if m: fd=parse_date_flexible(m.group(1)); break
        if fd:
            st=line
            for p in pats: st=re.sub(p,'',st,flags=re.IGNORECASE)
            st=re.sub(r'[:\-|]',' ',st).strip()
            result.append({'date':fd,'subject':' '.join(st.split()) or 'Exam'})
    return result

def parse_date_flexible(s):
    for fmt in ['%d/%m/%Y','%m/%d/%Y','%Y/%m/%d','%d-%m-%Y','%m-%d-%Y','%Y-%m-%d',
                '%d.%m.%Y','%B %d, %Y','%b %d, %Y','%d %B %Y','%d %b %Y','%d/%m/%y']:
        try: return datetime.strptime(s.strip(),fmt).strftime('%Y-%m-%d')
        except: pass
    return None

def parse_syllabus(text):
    if not text: return []
    lines=text.split('\n')
    unit_re=re.compile(r'^\s*(?:unit|module|chapter|section|part)\s*[-:.]?\s*(\d+|[IVXivx]+)[^\n]*',re.IGNORECASE)
    topic_re=re.compile(r'^\s*[\d\u2022\-\*\u25ba\u2013]+[.)]\s*.+|^\s+.{3,}')
    units,cu,ct=[],None,[]
    for line in lines:
        line=line.rstrip()
        if not line: continue
        um=unit_re.match(line)
        if um:
            if cu: cu.update({'topics':ct,'topic_count':max(len(ct),1)}); units.append(cu)
            cu={'name':line.strip(),'number':um.group(1)}; ct=[]
        elif cu and (topic_re.match(line) or len(line.strip())>3): ct.append(line.strip())
    if cu: cu.update({'topics':ct,'topic_count':max(len(ct),1)}); units.append(cu)
    if not units:
        src=[l.strip() for l in lines if l.strip()]
        units=[{'name':'Full Syllabus','number':'1','topics':src,'topic_count':max(len(src),1)}]
    return units

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
