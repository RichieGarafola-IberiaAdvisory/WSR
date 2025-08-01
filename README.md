# Iberia Team Performance Tracker

A modular, Streamlit-based internal platform empowering HR and management to log, analyze, and optimize contractor contributions across teams, vendors, and divisions. The system combines structured data collection with dynamic reporting tools to ensure transparency, accountability, and operational insight.

---

## Core Features

### Weekly Report Submission
- Spreadsheet-like interface to capture weekly contractor activity and level of effort.
- Auto-normalization of contractor names and vendors.
- Robust get_or_create logic prevents duplicates.
- Auditing fields (CreatedAt, EnteredBy) automatically logged for traceability.

### Accomplishment Logging
- Submit up to five qualitative accomplishments per week.
- Smart uniqueness checks using SHA-256 hash.
- Linked to employees and workstreams for deeper reporting.

### Management Dashboard
Visualize performance across vendors, divisions, and contractors using:
- Treemaps of effort allocation
- Downloadable filtered datasets
- Dynamic date/vendor/contractor filtering

### HR KPIs Dashboard
Track compliance and coverage using:
- Planned vs unplanned effort tracking.
- Contractor submission compliance and non-reporting checks.
- Labor category distribution analysis.
- Monthly hours heatmap by contractor.
- Export-ready CSV data for leadership.

### Filtered CSV Export
Download exactly what you see, in clean CSV format—ideal for internal reviews, audits, or leadership updates.

### Consistent Branding
Professional visual presentation aligned with Iberia Advisory’s identity.

---

## Technology Stack

| Layer        | Tools                        |
|--------------|------------------------------|
| **Frontend** | Streamlit                    |
| **Backend**  | Azure SQL (via SQLAlchemy)  |
| **Viz**      | Plotly, Pandas               |
| **Cache**    | Streamlit `@st.cache_data` and `@st.cache_resource` |
| **Testing**  | Pytest (unit and smoke tests) |
| **Hosting**  | Streamlit Cloud, Azure-ready |

---

## Setup Instructions

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
Ensure Azure SQL is running and create a database:
```sql
CREATE DATABASE Iberia_BackOffice;
```

Required tables:
- `employees`
- `weeklyreports`
- `workstreams`
- `accomplishments`
- `hourstracking`

Set connection string via environment variable or st.secrets:
```python
DATABASE_URL="Driver={ODBC Driver 18 for SQL Server};Server=...;Database=Iberia_BackOffice;UID=...;PWD=..."
```

### 4. Run the Application
```bash
streamlit run app.py
```

---

## File Structure

```
.
├── app.py                     # Home page
├── pages/
│   ├── 01_Form_Submission.py        # Weekly reports + accomplishments
│   ├── 02_Management_Dashboard.py   # Performance overview
│   ├── 03_HR_KPIs.py                # HR dashboard
│   └── 04_Accomplishments_Dashboard.py  # Accomplishment reporting
├── utils/
│   ├── db.py                  # Central DB config and schema reflection. Engine, caching, session handling
│   ├── helpers.py             # Shared utility functions. Auditing, normalization, helper functions
│   └── queries.py             # SQL queries
├── tests/                     # Pytest coverage
├── images/
│   └── Iberia-Advisory.png    # Branding
├── requirements.txt
└── README.md
```

---

## Usage Tips

- All **dashboards use sidebar filters and reset buttons** (date, vendor, contractor, workstream).
- **Submitters** can dynamically add rows using spreadsheet-like editors.
- **Accomplishments** allow up to 5 entries per person per week.
- All charts are **interactive**: hover, zoom, or download.
- Exports are cleanly formatted and filtered for leadership-ready deliverables.
- Contractor non-reporting checks highlight missing submissions.
- Caching minimizes DB load and speeds up navigation.
- Error handling gracefully handles offline DB or empty datasets.

---

## Data Quality & Integrity

- All inputs are normalized (case, whitespace, etc.) before database insert.
- Enum fields (e.g., `"planned"`, `"unplanned"`) are enforced in lowercase.
- Unique hash keys prevent duplicates.
- Schema interactions are safely abstracted using SQLAlchemy core.
- Auditing columns track record creation.
- Foreign key integrity ensures clean relations.

---

## Roadmap & Future Enhancements

- Role-based access (submitters vs viewers)
- Scheduled reminders for missing reports
- Monthly/Quarterly trend reports
- Mobile-friendly layout
- Integrated reporting PDFs for leadership
- Unit test coverage for form submission and KPIs

---

## Acknowledgments

Built with 💼 by the Iberia BackOffice Team.  
Designed by Richie Garafola — July 2025  
📧 RGarafola@IberiaAdvisory.com  
🔗 www.linkedin.com/in/richiegarafola  

**For internal use only.**
