# Car Tracking System - CIIC 4060/ICOM 5016 – Introduction to Database Systems Fall 2026

This repository presents the work done for the Car Tracking System term project. The project's purpose is tracking vehicles, and their location pings, fuel type, status, type, assignment, and driver, as well as parking areas, road segments, and trips.

# Render cloud hostname/URL
This URL is intended to test the services implemented in this project.

https://database-management-project.onrender.com

# Render Database Credentials
### Name
database-car-tracking-system

### Hostname
dpg-dbias67lk1mc73fpaj0g-a.viriginia-postgres.render.com

### Port
5432

### Database
dbproject26

### Username
tasnim2204

### Password
pj4qwMtMhq0qMh8Tny8prDPo4vzEdbOF

### Internal Database URL
postgresql://tasnim2204:pj4qwMtMhq0qMh8Tny8prDPo4vzEdbOF@dpg-dbias67lk1mc73fpaj0g-a/dbproject26

### External Database URL
postgresql://tasnim2204:pj4qwMtMhq0qMh8Tny8prDPo4vzEdbOF@dpg-dbias67lk1mc73fpaj0g-a.virginia-postgres.render.com/dbproject26

### PSQL Command
PGPASSWORD=pj4qwMtMhq0qMh8Tny8prDPo4vzEdbOF psql -h dpg-dbias67lk1mc73fpaj0g-a.virginia-postgres.render.com -U tasnim2204 dbproject26

# Project Structure

Database-Management-Project/\
`├── ETL/`\
`│   ├── phase1_official_dataset/`\
`│   │   ├── (.parquet files)`\
`│   ├── extract.py`\
`│   ├── transform.py`\
`│   └── load.py`
`├── backend/`\
`│   ├── config/`\
`│   │   ├── __init__.py`\
`│   │   ├── dbconfig.py`\
`│   ├── dao/`\
`│   │   ├── driver.py`\
`│   │   ├── location_ping.py`\
`│   │   ├── parking_area.py`\
`│   │   ├── road_segments.py`\
`│   │   ├── trip.py`\
`│   │   ├── vehicle_assignment.py`\
`│   │   ├── vehicles.py`\
`│   ├── handler/`\
`│   │   ├── driver.py`\
`│   │   ├── location_ping.py`\
`│   │   ├── parking_area.py`\
`│   │   ├── road_segments.py`\
`│   │   ├── trip.py`\
`│   │   ├── vehicle_assignment.py`\
`│   │   ├── vehicles.py`\
`│   ├── main.py`\
`│   └── requirements.txt`

# Database Environment Variables
Set these before running the ETL scripts:

- `PGUSER`
- `PGPASSWORD`
- `PGHOST`
- `PGPORT`
- `PGDATABASE`