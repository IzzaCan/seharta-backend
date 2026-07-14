from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.scrapers.gold_scraper import GoldScraper
from app.core.logger import gold_logger as logger

scheduler = BackgroundScheduler()

def scrape_gold_job():
    """
    Trigger dari scheduler untuk menjalankan scraper.
    Semua logika sukses/gagal sepenuhnya diurus oleh class GoldScraper.
    """
    logger.info("Scheduler triggered: scrape_gold_job")
    try:
        # Panggil scraper   
        GoldScraper().scrape()
    except Exception as e:
        # Handle jika ada error saat memanggil scraper (misal: MongoDB down saat inisiasi)
        logger.error(f"Critical error in scheduler job: {e}")

def start_scheduler():
    """
    Initializes and starts the APScheduler with the gold scraping job.
    """
    if not scheduler.running:
        # Menambahkan job ke scheduler
        scheduler.add_job(
            func=scrape_gold_job,
            trigger=CronTrigger(hour="9,13", minute=30, timezone="Asia/Jakarta"),
            id='gold_scraper_job',
            name="Scrape gold prices twice daily (09:30 & 13:30 WIB)",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("APScheduler started. Gold scraper job scheduled twice daily (09:30 & 14:30 WIB).")

def shutdown_scheduler():
    """
    Shuts down the APScheduler.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shut down.")
