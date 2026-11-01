import os

POOL_CONFIG = {
  'minconn': 5,
  'maxconn': 10
}

PG_DB_CONFIG = {
  'dbname': os.environ['PGDATABASE'],
  'host': os.environ.get('PGHOST', 'localhost'),
  'port': os.environ.get('PGPORT', '5432'),
  'user': os.environ['PGUSER'],
  'password': os.environ['PGPASSWORD']
}