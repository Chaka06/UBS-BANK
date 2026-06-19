import logging
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ubsbank.settings')

logger = logging.getLogger(__name__)

application = get_wsgi_application()

# Apply any pending migrations at cold start (needed on Vercel serverless
# where build-time migrate may target a different DB or be skipped).
try:
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        logger.info("Applying %d pending migration(s) at startup...", len(plan))
        from django.core.management import call_command
        call_command('migrate', verbosity=0)
        logger.info("Migrations applied successfully.")
except Exception:
    logger.exception("Migration check/apply failed at startup")
