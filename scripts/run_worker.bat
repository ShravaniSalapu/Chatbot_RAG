@echo off
REM Start Celery worker for document processing (Phase 2)
celery -A app.celery_app worker --loglevel=info -Q documents --pool=solo
