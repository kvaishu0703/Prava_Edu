"""Short-lived, account-owned previews for office roster imports."""
from datetime import datetime, timezone
from uuid import uuid4
from app.extensions import db


class RecordImport(db.Model):
    __tablename__ = 'record_imports'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
