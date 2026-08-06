#!/usr/bin/env bash
# Start Celery worker for document processing (Phase 2)
exec celery -A app.celery_app worker --loglevel=info -Q documents --concurrency=2
