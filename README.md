![SustainHub Banner](static/description/icon.png)
# SustainHub: Smart CSR & Sustainability Tracker

A comprehensive sustainability and CSR tracking system with AI-powered insights, reporting, and integration with Odoo modules.

## Features
- **Pledges & Initiatives**: Track CSR pledges with progress monitoring
- **Progress Tracking**: Log progress updates with automatic calculations
- **KPIs & Metrics**: Real-time KPI dashboard with visual indicators
- **AI-Powered Reports**: Generate professional PDF reports using AI
- **Dashboard**: Interactive dashboard with charts and statistics
- **Module Integration**: Seamless integration with Projects, HR, CRM, and Website modules
- **Smart Analytics**: AI-generated summaries and recommendations


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
-  Search for `SustainHub` and click **Install**
---

## Usage

Once installed, navigate to **SustainHub** from the main menu to access:

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

> *“Measure what matters — and make it count.”*


© 2025 CSR360. Built with ❤️ using Odoo.
