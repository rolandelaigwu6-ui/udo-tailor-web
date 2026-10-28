from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms.fields.choices import SelectChoice
from wtforms import (StringField, TextAreaField, DecimalField, SelectField,
                     SubmitField, BooleanField, IntegerField)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Email, URL, ValidationError
from flask_wtf.file import FileField, MultipleFileField, FileAllowed


def http_link(form, field):
    from urllib.parse import urlsplit
    URL(require_tld=False)(form, field)
    if urlsplit(field.data).scheme.lower() not in {'http', 'https'}:
        raise ValidationError('Use an HTTP or HTTPS URL.')


def valid_image(form, field):
    from app.utils import validate_image
    files = field.data if isinstance(field.data, list) else [field.data]
    for upload in files:
        if upload and getattr(upload, 'filename', ''):
            try:
                validate_image(upload)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc


class FiniteDecimalField(DecimalField):
    def process_formdata(self, valuelist):
        super().process_formdata(valuelist)
        if self.data is not None and not self.data.is_finite():
            self.data = None
            raise ValueError('Enter a finite price.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=80)])
    password = StringField('Password', validators=[DataRequired(), Length(max=1024)])
    submit = SubmitField('Login')


class ClothingForm(FlaskForm):
    name = StringField('Clothing Name', validators=[DataRequired(), Length(max=200)])
    price = FiniteDecimalField('Price', validators=[Optional(), NumberRange(min=0, max=Decimal('9999999999.99'))], places=2)
    category = StringField('Category', validators=[Optional(), Length(max=80)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=10000)])
    material = StringField('Material', validators=[Optional(), Length(max=120)])
    sizes = StringField('Sizes', validators=[Optional(), Length(max=200)])
    colors = StringField('Colors', validators=[Optional(), Length(max=200)])
    availability = SelectField('Availability', choices=[
        SelectChoice('Available'),
        SelectChoice('Made to Order'),
        SelectChoice('Sold'),
        SelectChoice('Unavailable'),
    ], default='Available')
    featured = BooleanField('Featured on homepage')
    images = MultipleFileField('Images', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'), valid_image])
    submit = SubmitField('Publish Design')


class SettingsForm(FlaskForm):
    brand_name = StringField('Brand Name', validators=[Optional(), Length(max=120)])
    hero_heading = StringField('Hero Heading', validators=[Optional(), Length(max=200)])
    hero_description = TextAreaField('Hero Description', validators=[Optional(), Length(max=10000)])
    logo = FileField('Logo', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'), valid_image])
    phone = StringField('Phone', validators=[Optional(), Length(max=40)])
    whatsapp = StringField('WhatsApp', validators=[Optional(), Length(max=40)])
    email = StringField('Email', validators=[Optional(), Length(max=120), Email(check_deliverability=False)])
    address = StringField('Address', validators=[Optional(), Length(max=300)])
    opening_hours = StringField('Opening Hours', validators=[Optional(), Length(max=200)])
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=120)])
    account_name = StringField('Account Name', validators=[Optional(), Length(max=120)])
    account_number = StringField('Account Number', validators=[Optional(), Length(max=40)])
    about = TextAreaField('About', validators=[Optional(), Length(max=10000)])
    instagram = StringField('Instagram URL', validators=[Optional(), Length(max=200), http_link])
    facebook = StringField('Facebook URL', validators=[Optional(), Length(max=200), http_link])
    tiktok = StringField('TikTok URL', validators=[Optional(), Length(max=200), http_link])
    social_links = TextAreaField('Social Links', validators=[Optional(), Length(max=10000)])
    submit = SubmitField('Save Settings')
class AboutProfileForm(FlaskForm):
    designer_name = StringField('Designer Name', validators=[Optional(), Length(max=120)])
    designer_title = StringField('Designer Title', validators=[Optional(), Length(max=120)])
    designer_bio = TextAreaField('Biography', validators=[Optional(), Length(max=10000)])
    designer_image = FileField('Profile Photograph', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'), valid_image])
    years_experience = StringField('Years of Experience', validators=[Optional(), Length(max=40)])
    specialties = TextAreaField('Specialties', validators=[Optional(), Length(max=10000)])
    signature_style = TextAreaField('Signature Style', validators=[Optional(), Length(max=10000)])
    submit = SubmitField('Save Profile')


class AchievementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=10000)])
    year = StringField('Year', validators=[Optional(), Length(max=20)])
    image = FileField('Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'), valid_image])
    display_order = IntegerField('Display Order', validators=[Optional(), NumberRange(min=0, max=2147483647)], default=0)
    submit = SubmitField('Save Achievement')


class ClientShowcaseForm(FlaskForm):
    client_name = StringField('Client Name (optional)', validators=[Optional(), Length(max=120)])
    design_name = StringField('Design / Style Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=10000)])
    price = FiniteDecimalField('Price', validators=[Optional(), NumberRange(min=0, max=Decimal('9999999999.99'))], places=2)
    category = StringField('Category', validators=[Optional(), Length(max=80)])
    testimonial = TextAreaField('Testimonial', validators=[Optional(), Length(max=10000)])
    image = FileField('Client Image', validators=[FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!'), valid_image])
    permission_confirmed = BooleanField('Permission to publish client image')
    featured = BooleanField('Featured')
    submit = SubmitField('Save Showcase')
