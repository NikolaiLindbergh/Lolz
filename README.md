# ClinAI – Healthcare AI Clinical Decision Support System
**Research Paper:** Healthcare Professionals: Perspectives on AI Integration in Clinical Practice  
**Group:** BSIT-AI22 Group 7 – Leyte Normal University  
**Members:** Ligutan, Ram V. · Caindoy, Nikolai Lindbergh M. · Bautista, Paul Kristoffer · Palmitos, Czarisha Liz D.

---

## 📁 Project Structure
```
healthcare_ai_system/
├── app.py                  ← Main Flask app (run this)
├── config.py               ← App configuration
├── requirements.txt        ← Python dependencies
├── .env.example            ← Copy to .env and fill in your API key
├── database/
│   ├── __init__.py
│   └── models.py           ← Database tables (User, Patient, Consultation, AuditLog)
├── routes/
│   ├── auth.py             ← Login / Logout
│   ├── admin.py            ← Admin-only routes (/admin/...)
│   └── user.py             ← Healthcare staff routes (/user/...)
├── ai/
│   └── clinical_ai.py      ← Claude AI integration
├── templates/
│   ├── base.html           ← Shared layout
│   ├── index.html          ← Landing page
│   ├── auth/login.html
│   ├── admin/              ← Admin pages
│   └── user/               ← Staff pages
└── static/
    ├── css/style.css
    └── js/main.js
```

---

## 🚀 HOW TO SET UP (Step-by-Step)

### Step 1 – Install Python
Download from https://python.org (version 3.10 or newer)  
✅ Check "Add Python to PATH" during installation!

### Step 2 – Open the Project in VS Code
1. Open VS Code
2. File → Open Folder → select the `healthcare_ai_system` folder
3. Open the Terminal: View → Terminal

### Step 3 – Create a Virtual Environment
In the terminal, type:
```bash
python -m venv venv
```
Then activate it:
- **Windows:** `venv\Scripts\activate`
- **Mac/Linux:** `source venv/bin/activate`

You should see `(venv)` at the start of your terminal line.

### Step 4 – Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5 – Set Up Your API Key
1. Copy `.env.example` and rename it to `.env`
2. Go to https://console.anthropic.com and get your API key
3. Open `.env` and replace `your-anthropic-api-key-here` with your real key

```
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXX...
```

### Step 6 – Run the App
```bash
python app.py
```

You will see:
```
✅ Default admin created → username: admin | password: Admin@1234
* Running on http://127.0.0.1:8080
```

### Step 7 – Open in Browser
Go to: **http://127.0.0.1:8080**

Admin pages use **`/admin/...`** and user pages use **`/user/...`**. For example:
- Admin dashboard: **`http://127.0.0.1:8080/admin/dashboard`**
- User dashboard: **`http://127.0.0.1:8080/user/dashboard`**

---

## 🔐 Default Login Credentials

| Role  | Username | Password   |
|-------|----------|------------|
| Admin | admin    | Admin@1234 |

⚠️ **Change these credentials after logging in for the first time!**

---

## 👥 Role Differences

### Admin (`/admin/...`)
- View system-wide dashboard with stats
- Manage all staff accounts (add, activate, deactivate)
- View all patient records across the system
- Generate reports (including research evaluation scores)
- View complete audit log of all actions

### Healthcare Staff / User (`/user/...`)
- Personal dashboard with their own stats
- Register and manage their own patients
- Start AI consultations (enter symptoms → get AI analysis)
- View consultation history per patient
- Update their own profile

---

## 🤖 How the AI Works

1. Staff selects a patient and clicks **"Start AI Consultation"**
2. Enters the patient's symptoms, chief complaint, and vital signs
3. The system sends patient data + symptoms to **Claude AI (Anthropic)**
4. Claude returns:
   - Clinical summary
   - Possible diagnoses (with likelihood: High/Moderate/Low)
   - Recommended diagnostic tests
   - Red flags / warning signs
   - Clinical recommendations
5. Results are saved in the database and linked to the patient's consultation history

> ⚠️ **Important:** The AI is a DECISION SUPPORT TOOL only. It should never replace a licensed healthcare professional's judgment.

---

## 🗄️ Database

The system uses **SQLite** (no separate server needed!). The database file `healthcare.db` is automatically created in the project folder when you first run the app.

Tables:
- `users` – Staff and admin accounts
- `patients` – Patient records
- `consultations` – AI consultation history
- `audit_logs` – All actions logged for security

---

## 🎓 For Your Defense

Key points to explain:
1. **Role-based access control** – Admin and user have separate routes and permissions
2. **AI integration** – Real Claude AI analyzing patient symptoms
3. **Security** – Passwords are hashed, sessions are managed, all actions are audit-logged
4. **Research alignment** – Reports page shows your actual evaluation scores from the paper
5. **TAM compliance** – Interface is simple (low cognitive load), useful for clinical tasks

---

## ❓ Common Issues

**"ModuleNotFoundError"** → Make sure your virtualenv is activated (`venv\Scripts\activate`)  
**"AI Error: Invalid API key"** → Check your `.env` file has the correct key  
**Page not loading** → Make sure you ran `python app.py` and it says "Running on http://127.0.0.1:5000"
