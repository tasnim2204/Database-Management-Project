# Car Tracking System - CIIC 4060/ICOM 5016 – Introduction to Database Systems Fall 2026

This repository presents the work done for the Car Tracking System term project. The project's purpose is tracking vehicles, and their location pings, fuel type, status, type, assignment, and driver, as well as parking areas, road segments, and trips.

# Project Structure

Database-Management-Project/\
├── ETL/\
│   ├── phase1_official_dataset/\
│   │   ├── (.parquet files)\
│   ├── extract.py\
│   ├── transform.py\
│   └── load.py\

# Database Environment Variables
Set these before running the ETL scripts:

- `PGUSER`
- `PGPASSWORD`
- `PGHOST`
- `PGPORT`
- `PGDATABASE`