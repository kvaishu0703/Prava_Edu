"""Transaction revision used to refresh connected portal views."""
from datetime import datetime, timezone
from app.extensions import db


class PortalRevision(db.Model):
    __tablename__ = 'portal_revision'
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=0)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False,
                           default=lambda: datetime.now(timezone.utc))
