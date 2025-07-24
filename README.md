# 🧭 Iberia Team Performance Tracker

A modular, Streamlit-based internal platform empowering HR and management to log, analyze, and optimize contractor contributions across teams, vendors, and divisions. The system combines structured data collection with dynamic reporting tools to ensure transparency, accountability, and operational insight.

---

## 🚀 Core Features

### 📝 Weekly Report Submission
Capture contractor contributions and level of effort in an intuitive spreadsheet-style interface. Input is validated, normalized, and stored securely in PostgreSQL.

### 🏆 Accomplishment Logging
Enable team members to highlight weekly accomplishments by workstream—up to five per entry—with contextual tagging and clean formatting.

### 📊 Management Dashboard
Visualize performance across vendors, divisions, and contractors using:
- Treemaps of effort allocation
- Downloadable filtered datasets
- Dynamic date/vendor/contractor filtering

### 👥 HR KPIs Dashboard
Track compliance and coverage using:
- Unplanned vs planned work ratios
- Contractor activity monitoring
- Labor category analysis
- Time heatmaps by contractor/month

### 📁 Filtered CSV Export
Download exactly what you see, in clean CSV format—ideal for internal reviews, audits, or leadership updates.

### 🎨 Consistent Branding
Professional visual presentation aligned with Iberia Advisory’s identity. Minimalist, clear, and branded.

---

## 🧰 Technology Stack

| Layer        | Tools                        |
|--------------|------------------------------|
| **Frontend** | Streamlit                    |
| **Backend**  | PostgreSQL (via SQLAlchemy)  |
| **Viz**      | Plotly, Pandas               |
| **Cache**    | Streamlit `@st.cache_data`   |
| **Hosting**  | Local, or optionally Streamlit Cloud |

---

## 📦 Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/your-org/iberia-team-performance-tracker.git
cd iberia-team-performance-tracker
```

### 2. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate     # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Configure the Database
Ensure PostgreSQL is running and create a database:
```sql
CREATE DATABASE Iberia_BackOffice;
```

Required tables:
- `employees`
- `weeklyreports`
- `workstreams`
- `accomplishments`
- `hourstracking`

Update the connection string in the code (hardcoded in `utils/db.py` for local use):
```python
postgresql://postgres:postgres@localhost:5432/Iberia_BackOffice
```

### 4. Run the Application
```bash
streamlit run app.py
```

---

## 🗂 File Structure

```
.
├── app.py                     # Home page
├── pages/
│   ├── 01_Form_Submission.py        # Weekly reports + accomplishments
│   ├── 02_Management_Dashboard.py   # Performance overview
│   ├── 03_HR_KPIs.py                # HR dashboard
│   └── 04_Accomplishments_Dashboard.py  # Accomplishment reporting
├── utils/
│   ├── db.py                  # Central DB config and schema reflection
│   ├── helpers.py             # Shared utility functions
│   └── queries.py             # SQL queries
├── images/
│   └── Iberia-Advisory.png    # Branding
├── requirements.txt
└── README.md
```

---

## 🧠 Usage Tips

- All **dashboards use sidebar filters** (date, vendor, contractor, workstream).
- **Submitters** can dynamically add rows using spreadsheet-like editors.
- **Accomplishments** allow up to 5 entries per person per week.
- All charts are **interactive**: hover, zoom, or download.
- Exports are cleanly formatted and filtered for leadership-ready deliverables.

---

## 🧪 Data Quality & Integrity

- All inputs are normalized (case, whitespace, etc.) before database insert.
- Enum fields (e.g., `"planned"`, `"unplanned"`) are enforced in lowercase.
- Duplicate contractor/workstream entries are automatically de-duplicated using smart `get_or_create` logic.
- Schema interactions are safely abstracted using SQLAlchemy core.

---

## 📌 Roadmap & Future Enhancements

- 🔐 Role-based access (submitters vs viewers)
- 📧 Scheduled reminders for missing reports
- 📆 Monthly/Quarterly trend reports
- 📱 Mobile-friendly layout
- 🧾 Integrated reporting PDFs for leadership
- 🧪 Unit test coverage for form submission and KPIs

---

## 🤝 Acknowledgments

Built with 💼 by the Iberia BackOffice Team.  
Designed by Richie Garafola — July 2025  
📧 RGarafola@IberiaAdvisory.com  
🔗 www.linkedin.com/in/richiegarafola  

**For internal use only.**
