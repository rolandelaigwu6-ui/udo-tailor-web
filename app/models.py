import re
from datetime import datetime, timezone

from app import db


def slugify(text):
    text = (text or '').lower().strip()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-+', '-', text).strip('-')
    return text or 'design'


class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)


class Clothing(db.Model):
    __tablename__ = 'clothing'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(220), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    material = db.Column(db.String(120), nullable=True)
    sizes = db.Column(db.String(200), nullable=True)
    colors = db.Column(db.String(200), nullable=True)
    availability = db.Column(db.String(40), nullable=False, default='Available')
    featured = db.Column(db.Boolean, nullable=False, default=False)
    likes = db.Column(db.Integer, nullable=False, default=0)
    interested_count = db.Column(db.Integer, nullable=False, default=0)
    not_interested_count = db.Column(db.Integer, nullable=False, default=0)
    view_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    images = db.relationship('ClothingImage', backref='clothing', lazy='selectin',
                             cascade='all, delete-orphan', order_by='ClothingImage.sort_order')

    @property
    def primary_image(self):
        return next((img for img in self.images if img.is_primary),
                    self.images[0] if self.images else None)

    def unique_slug(self, name):
        base = slugify(name)
        slug = base
        i = 1
        while Clothing.query.filter(Clothing.slug == slug, Clothing.id != self.id).first():
            slug = f'{base}-{i}'
            i += 1
        return slug


class ClothingImage(db.Model):
    __tablename__ = 'clothing_images'
    id = db.Column(db.Integer, primary_key=True)
    clothing_id = db.Column(db.Integer, db.ForeignKey('clothing.id'), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)

    @property
    def url(self):
        if self.image_url.startswith('http://') or self.image_url.startswith('https://'):
            return self.image_url
        from app.utils import image_url
        return image_url(self.image_url)


class SiteSettings(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    brand_name = db.Column(db.String(120), default='Udo Tailor')
    logo = db.Column(db.String(500), nullable=True)
    hero_heading = db.Column(db.String(200), default='Crafted With Precision. Designed For You.')
    hero_description = db.Column(db.Text, default='Premium tailoring and contemporary African fashion.')
    phone = db.Column(db.String(40), nullable=True)
    whatsapp = db.Column(db.String(40), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    opening_hours = db.Column(db.String(200), nullable=True)
    bank_name = db.Column(db.String(120), nullable=True)
    account_name = db.Column(db.String(120), nullable=True)
    account_number = db.Column(db.String(40), nullable=True)
    about = db.Column(db.Text, nullable=True)
    instagram = db.Column(db.String(200), nullable=True)
    facebook = db.Column(db.String(200), nullable=True)
    tiktok = db.Column(db.String(200), nullable=True)
    social_links = db.Column(db.Text, nullable=True)
    designer_name = db.Column(db.String(120), nullable=True)
    designer_title = db.Column(db.String(120), nullable=True)
    designer_bio = db.Column(db.Text, nullable=True)
    designer_image = db.Column(db.String(500), nullable=True)
    years_experience = db.Column(db.String(40), nullable=True)
    specialties = db.Column(db.Text, nullable=True)
    signature_style = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

class Visitor(db.Model):
    __tablename__ = 'visitors'
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                             onupdate=lambda: datetime.now(timezone.utc))
    newsletter_subscribed = db.Column(db.Boolean, default=False)


class ClothingActivity(db.Model):
    __tablename__ = 'clothing_activities'
    id = db.Column(db.Integer, primary_key=True)
    clothing_id = db.Column(db.Integer, db.ForeignKey('clothing.id'), nullable=False)
    visitor_id = db.Column(db.Integer, db.ForeignKey('visitors.id'), nullable=True)
    activity_type = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    clothing = db.relationship('Clothing', backref=db.backref('activities', cascade='all, delete-orphan'))
    visitor = db.relationship('Visitor', backref='activities')


class Achievement(db.Model):
    __tablename__ = 'achievements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    year = db.Column(db.String(20), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class ClientShowcase(db.Model):
    __tablename__ = 'client_showcase'
    id = db.Column(db.Integer, primary_key=True)
    client_name = db.Column(db.String(120), nullable=True)
    design_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(12, 2), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(80), nullable=True)
    testimonial = db.Column(db.Text, nullable=True)
    permission_confirmed = db.Column(db.Boolean, default=False)
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
