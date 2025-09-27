"""
Scheduled backup functionality for embeddings folder
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from .gcs_sync_manager import backup_embeddings_folder, get_sync_manager

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def setup_daily_backup():
    """Setup daily backup scheduler"""
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already initialized")
        return scheduler

    scheduler = AsyncIOScheduler()
    # Schedule daily backup at 12:00 AM
    scheduler.add_job(
        func=daily_backup_job,
        trigger=CronTrigger(hour=0, minute=0),  # 12:00 AM daily
        id="daily_embeddings_backup",
        name="Daily Embeddings Backup",
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )

    logger.info("Daily backup scheduler configured for 12:00 AM")
    return scheduler


async def daily_backup_job():
    """Daily backup job function"""
    logger.info("🔄 Starting scheduled daily backup...")

    try:
        # Check if sync manager is available
        sync_manager = get_sync_manager()
        if not sync_manager:
            logger.warning("Sync manager not available for scheduled backup")
            return

        if not sync_manager.gcs_available:
            logger.warning("GCS not available for scheduled backup")
            return

        # Perform backup
        success = backup_embeddings_folder()

        if success:
            logger.info("✅ Scheduled daily backup completed successfully")
        else:
            logger.warning("⚠️ Scheduled daily backup failed")

    except Exception as e:
        logger.error(f"❌ Error during scheduled backup: {str(e)}")


def start_scheduler():
    """Start the scheduler"""
    global scheduler

    if scheduler is None:
        scheduler = setup_daily_backup()

    if not scheduler.running:
        scheduler.start()
        logger.info("📅 Backup scheduler started")
    else:
        logger.warning("Scheduler already running")
