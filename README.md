# 🌍 CSR360

**CSR360** is a corporate sustainability and student engagement platform built for **Odoo**.  
It integrates seamlessly with Odoo’s **HR**, **CRM**, and **Project** apps to help organizations and universities track initiatives, pledges, KPIs, and performance dashboards — all in one place.


## ✨ Key Features

- **Student & Volunteer Management**  
  Manage student profiles, enrollments, and participation in CSR or sustainability projects.

- **Performance Dashboards**  
  Real-time dashboards to visualize metrics, KPIs, and progress toward organizational goals.

- **Pledge Tracking**  
  Record, monitor, and manage pledges or commitments from participants, teams, or partners.

- **KPI Analytics**  
  Define and evaluate measurable goals with custom Key Performance Indicators.

- **CRM, HR, and Project Integration**  
  Extends Odoo’s core modules to create a unified CSR ecosystem:
  - CRM for partner and donor management  
  - HR for employee participation  
  - Project for initiative tracking and reporting

- **Demo Data**  
  Includes sample records for demonstration and testing (`data/demo_data.xml`).

---

## Module Structure

```
student_management/
├── __manifest__.py
├── __init__.py
├── data/
│   └── demo_data.xml
├── models/
│   ├── dashboard.py
│   ├── kpi.py
│   ├── pledge.py
│   ├── progress.py
│   ├── crm_inherit.py
│   ├── hr_employee_inherit.py
│   ├── project_inherit.py
│   └── ...
├── views/
│   ├── dashboard_views.xml
│   ├── kpi_views.xml
│   ├── pledge_views.xml
│   ├── progress_views.xml
│   ├── menu.xml
│   └── ...
├── security/
│   └── ir.model.access.csv
└── static/
    └── description/
        └── icon.png
```

---

## ⚙️ Installation

1. Start your postgres DB service on docker:
```bash
  docker run -d \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres \
  --name db \
  postgres:15
  ```

3. Then start your Odoo19.0 service on docker too:

```bash
docker run -p 8069:8069 \
  --name odoo \
  --link db:db \
  -t odoo:19.0
```
- Odoo will be accessible at: http://localhost:8069

4. Docker compose script + persistent data (recommended):
```yaml
version: '3.1'
services:
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres2
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo-db-data:/var/lib/postgresql/data

  odoo:
    image: odoo:19.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - ./addons:/mnt/extra-addons
      - odoo-web-data:/var/lib/odoo

volumes:
  odoo-db-data:
  odoo-web-data:
```

6. Log in and install your module

-  Go to → `http://localhost:8069`
-  Create a new database

   * Master password: `odoo`
-  Open **Apps**
-  Click the **debug menu** (bug icon top-right) → *Update Apps List*
-  Search for `CSR360` and click **Install**
---

## Usage

Once installed, navigate to **CSR360** from the main menu to access:

- **Dashboard** → Visual overview of active CSR projects and KPIs.  
- **Students / Volunteers** → Manage participants and engagement.  
- **Pledges** → View and track commitments and their progress.  
- **Reports** → Export data and performance insights.

## Compatibility

- **Odoo Version:** 16.0 or higher  
- **Python:** 3.10+  
- **Database:** PostgreSQL  


## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.


## 🤝 Contributing

Pull requests are welcome!  
If you plan major changes, please open an issue first to discuss what you’d like to modify or improve.


## Authors
- [Mousa Herzallah](https://www.linkedin.com/in/mousa-herzallah-326090272/)
- [Wardah Jamil](https://www.linkedin.com/in/wardah-jamil-5a121b278/)
- [Fatimetou A](https://www.linkedin.com/in/fatimetou-a-2b3162250/)
- [Abdulrahman Tamim](https://www.linkedin.com/in/abdulrahman-tamim-a7149a29b/)


## About CSR360

CSR360 is part of a larger initiative to combine **education**, **sustainability**, and **data-driven decision-making** into a single platform that empowers organizations to build measurable impact.

> *“Measure what matters — and make it count.”*


© 2025 CSR360. Built with ❤️ using Odoo.
