# SHAI Core developer shortcuts
PSQL_URL ?= postgresql://shai:shai@localhost:5432/shai

.PHONY: help db-up db-init db-reset api web test fmt

help:
	@echo "db-up     bring up Postgres + pgvector (docker compose)"
	@echo "db-init   apply db/schema.sql then db/seed.sql"
	@echo "db-reset  drop + recreate schema, then seed"
	@echo "api       run the FastAPI dev server"
	@echo "web       run the Next.js dev server"
	@echo "test      run the API test suite"

db-up:
	docker compose up -d db

db-init:
	psql "$(PSQL_URL)" -f db/schema.sql
	psql "$(PSQL_URL)" -f db/seed.sql

db-reset:
	psql "$(PSQL_URL)" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	$(MAKE) db-init

api:
	cd api && uvicorn app.main:app --reload

web:
	cd web && npm run dev

test:
	cd api && pytest
