# This file is a placeholder for any reusable raw SQL query strings. We’ll only define one right now (used in the Management Dashboard), and grow this as needed.

weekly_reports_with_employees = """
SELECT 
    wr.weekstartdate AS "Reporting Week",
    e.vendorname AS "Vendor Name",
    wr.divisioncommand AS "Division/Command",
    wr.workproducttitle AS "Work Product Title",
    wr.contributiondescription AS "Brief description of individual's contribution",
    wr.status AS "Work Product Status",
    wr.plannedorunplanned AS "Planned or Unplanned",
    wr.datecompleted AS "If Completed, Date Completed",
    wr.distinctnfr AS "Distinct NFR",
    wr.distinctcap AS "Distinct CAP",
    wr.effortpercentage AS "Level of Effort (%)",
    e.name AS "Contractor (Last Name, First Name)",
    wr.govttaname AS "Govt TA (Last Name, First Name)",
    e.laborcategory AS "Labor Category"
FROM weeklyreports wr
JOIN employees e ON wr.employeeid = e.employeeid
"""
