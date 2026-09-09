import sqlite3
import logging

logger = logging.getLogger(__name__)


class Storage:
    """
    Hangi duyuruların daha önce gönderildiğini tutar (tekrar mesaj atmamak için).
    DATABASE_URL doluysa Postgres (Railway'in ücretsiz eklentisi dahil), boşsa yerel SQLite dosyası kullanılır.

    ÖNEMLİ: Railway'in dosya sistemi kalıcı olmayabilir (redeploy'da sıfırlanabilir).
    Bu yüzden production'da DATABASE_URL (Postgres) kullanılması şiddetle önerilir.
    """

    def __init__(self, database_url: str = "", sqlite_path: str = "bot_data.db"):
        self.database_url = database_url
        self.sqlite_path = sqlite_path
        self.backend = "postgres" if database_url else "sqlite"
        self._init_db()

    def _get_conn(self):
        if self.backend == "postgres":
            import psycopg2
            return psycopg2.connect(self.database_url)
        return sqlite3.connect(self.sqlite_path)

    def _init_db(self):
        conn = self._get_conn()
        cur = conn.cursor()
        if self.backend == "postgres":
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_announcements (
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    first_seen_at TIMESTAMP DEFAULT NOW(),
                    PRIMARY KEY (source, external_id)
                )
                """
            )
        else:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS seen_announcements (
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    title TEXT,
                    url TEXT,
                    first_seen_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source, external_id)
                )
                """
            )
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Veritabanı hazır (backend={self.backend})")

    def is_seen(self, source: str, external_id: str) -> bool:
        conn = self._get_conn()
        cur = conn.cursor()
        ph = "%s" if self.backend == "postgres" else "?"
        cur.execute(
            f"SELECT 1 FROM seen_announcements WHERE source={ph} AND external_id={ph}",
            (source, external_id),
        )
        result = cur.fetchone() is not None
        cur.close()
        conn.close()
        return result

    def mark_seen(self, source: str, external_id: str, title: str, url: str):
        conn = self._get_conn()
        cur = conn.cursor()
        try:
            if self.backend == "postgres":
                cur.execute(
                    """INSERT INTO seen_announcements (source, external_id, title, url)
                       VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (source, external_id, title, url),
                )
            else:
                cur.execute(
                    """INSERT OR IGNORE INTO seen_announcements (source, external_id, title, url)
                       VALUES (?, ?, ?, ?)""",
                    (source, external_id, title, url),
                )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def has_any(self, source: str) -> bool:
        """Bu kaynak için hiç kayıt var mı? (ilk çalıştırma / baseline kontrolü için)"""
        conn = self._get_conn()
        cur = conn.cursor()
        ph = "%s" if self.backend == "postgres" else "?"
        cur.execute(f"SELECT 1 FROM seen_announcements WHERE source={ph} LIMIT 1", (source,))
        result = cur.fetchone() is not None
        cur.close()
        conn.close()
        return result
