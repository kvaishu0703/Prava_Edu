"""Public website contact inquiry model."""

from app.extensions import db
from app.models.base import TimestampMixin


class ContactInquiry(TimestampMixin, db.Model):
    """Message submitted from the public college contact form."""

    __tablename__ = "contact_inquiries"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="New", nullable=False)

    def __repr__(self) -> str:
        return f"<ContactInquiry {self.email}>"
