import os

from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated, require_admin


def _get_db_file_path(application) -> str:
    """
    :return: Absolute filesystem path to the SQLite database file.
    :rtype: str
    """
    db_path: str = application.digi_settings.settings.get("db_path").get_value()
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")
    return db_path


def _list_backups(db_path: str) -> list[dict]:
    """
    :param db_path: Filesystem path to the main database file.
    :type db_path: str
    :return: List of backup file dicts, sorted newest first.
    :rtype: list[dict]
    """
    db_dir = os.path.dirname(db_path) or "."
    db_basename = os.path.basename(db_path)
    prefix = db_basename + "."

    backups = []
    if os.path.isdir(db_dir):
        for fname in os.listdir(db_dir):
            if not fname.startswith(prefix):
                continue
            suffix = fname[len(prefix) :]
            if not suffix.isdigit():
                continue
            full_path = os.path.join(db_dir, fname)
            stat = os.stat(full_path)
            backups.append(
                {
                    "filename": fname,
                    "size_bytes": stat.st_size,
                    "created_at": int(suffix),
                }
            )

    backups.sort(key=lambda x: x["created_at"], reverse=True)
    return backups


@ApiRoute("admin/db-backups", ApiVersion.V1)
class BackupsController(BaseAPIController):
    @api_authenticated
    @require_admin
    async def get(self):
        db_path = _get_db_file_path(self.application)
        backups = _list_backups(db_path)
        total_size = sum(b["size_bytes"] for b in backups)
        self.set_status(200)
        await self.finish(
            {
                "backups": backups,
                "count": len(backups),
                "total_size_bytes": total_size,
            }
        )

    @api_authenticated
    @require_admin
    async def delete(self):
        timestamp = self.get_argument("timestamp", None)
        if not timestamp:
            self.set_status(400)
            await self.finish({"message": "timestamp query argument is required"})
            return
        if not timestamp.isdigit():
            self.set_status(400)
            await self.finish({"message": "timestamp must be a positive integer"})
            return

        db_path = _get_db_file_path(self.application)
        backup_path = f"{db_path}.{timestamp}"

        if not os.path.isfile(backup_path):
            self.set_status(404)
            await self.finish({"message": "Backup file not found"})
            return

        os.remove(backup_path)
        self.set_status(200)
        await self.finish({"message": "Backup deleted"})
