from flask import Blueprint, render_template, request, url_for, jsonify, session, current_app, send_from_directory, abort
from sqlalchemy import or_, func
from app.models import (Clothing, ClothingImage, SiteSettings, Visitor,
                        ClothingActivity, ClientShowcase, Achievement)
from app import db, limiter
from email_validator import validate_email, EmailNotValidError

public_bp = Blueprint('public', __name__)


def _settings():
    s = SiteSettings.query.first()
    if s is None:
        s = SiteSettings()
        db.session.add(s)
        db.session.commit()
    return s


def _get_visitor():
    pid = session.get('visitor_public_id')
    if not pid:
        return None
    return Visitor.query.filter_by(public_id=pid).first()


def _record_activity(clothing, activity_type, counter=None):
    if counter:
        column = getattr(Clothing, counter)
        db.session.execute(db.update(Clothing).where(Clothing.id == clothing.id)
                           .values({counter: column + 1}))
    visitor = _get_visitor()
    db.session.add(ClothingActivity(clothing_id=clothing.id,
                                   visitor_id=visitor.id if visitor else None,
                                   activity_type=activity_type))
    db.session.commit()


def _input_data():
    if request.is_json:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, description='Send a JSON object.')
        return data
    return request.form


def _text(data, key, maximum):
    value = data.get(key)
    if value is None:
        return ''
    if not isinstance(value, str) or len(value) > maximum:
        abort(400, description=f'Invalid {key}.')
    return value.strip()


def _email(data, required=False):
    value = _text(data, 'email', 120)
    if not value and not required:
        return None
    try:
        normalized = validate_email(value, check_deliverability=False).normalized
        if len(normalized) > 120:
            raise ValueError('Email is too long.')
        return normalized
    except (EmailNotValidError, ValueError):
        abort(400, description='Enter a valid email address.')


@public_bp.route('/uploads/<filename>')
def upload(filename):
    from app.utils import allowed_file
    if not allowed_file(filename):
        abort(404)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


def _filter_clothes(q='', category=''):
    query = Clothing.query
    if q:
        like = f'%{q}%'
        query = query.filter(or_(Clothing.name.ilike(like),
                                 Clothing.description.ilike(like),
                                 Clothing.category.ilike(like),
                                 Clothing.material.ilike(like)))
    if category and category.lower() not in ('all', ''):
        query = query.filter(func.lower(Clothing.category) == category.lower())
    return query


@public_bp.route('/visitor/identify', methods=['POST'])
@limiter.limit('30 per minute')
def visitor_identify():
    data = _input_data()
    name = _text(data, 'name', 120) or None
    email = _email(data)
    pid = session.get('visitor_public_id')
    visitor = None
    if pid:
        visitor = Visitor.query.filter_by(public_id=pid).first()
    if visitor is None:
        import uuid
        visitor = Visitor(public_id=uuid.uuid4().hex, name=name, email=email)
        db.session.add(visitor)
        db.session.commit()
    else:
        if name:
            visitor.name = name
        if email:
            visitor.email = email
        db.session.commit()
    session['visitor_public_id'] = visitor.public_id
    session['visitor_prompted'] = True
    return jsonify({'ok': True})


@public_bp.route('/track/<int:clothing_id>/<activity_type>', methods=['POST'])
@limiter.limit('60 per minute')
def track(clothing_id, activity_type):
    clothing = db.get_or_404(Clothing, clothing_id)
    allowed = {'WHATSAPP_CLICK', 'PHONE_CLICK'}
    if activity_type not in allowed:
        return jsonify({'error': 'invalid'}), 400
    _record_activity(clothing, activity_type)
    return jsonify({'ok': True})
@public_bp.route('/')
def index():
    settings = _settings()
    all_newest = Clothing.query.order_by(Clothing.created_at.desc(), Clothing.id.desc()).limit(6).all()
    just_dropped = all_newest[0] if all_newest else None
    latest = all_newest[1:6] if len(all_newest) > 1 else []
    featured = Clothing.query.filter_by(featured=True).order_by(Clothing.created_at.desc()).limit(4).all()
    best_loved = Clothing.query.order_by((Clothing.likes + Clothing.interested_count).desc()).limit(4).all()
    new_in = Clothing.query.order_by(Clothing.created_at.desc()).limit(4).all()
    mens = Clothing.query.filter(func.lower(Clothing.category).in_(['men', 'mens', "men's"])).order_by(Clothing.created_at.desc()).limit(4).all()
    womens = Clothing.query.filter(func.lower(Clothing.category).in_(['women', 'womens', "women's"])).order_by(Clothing.created_at.desc()).limit(4).all()
    wedding = Clothing.query.filter(Clothing.category.ilike('%wedding%')).order_by(Clothing.created_at.desc()).limit(4).all()
    categories = [c[0] for c in db.session.query(Clothing.category).distinct().all() if c[0]]
    newest_by_category = db.session.query(
        Clothing.id.label('id'),
        func.row_number().over(partition_by=Clothing.category,
                               order_by=(Clothing.created_at.desc(), Clothing.id.desc())).label('position'),
    ).subquery()
    category_clothes = Clothing.query.join(newest_by_category, Clothing.id == newest_by_category.c.id).filter(
        newest_by_category.c.position == 1, Clothing.category.is_not(None), Clothing.category != ''
    ).order_by(Clothing.category).all()
    category_cards = [{'name': item.category, 'clothing': item} for item in category_clothes]
    gallery_images = ClothingImage.query.join(Clothing).order_by(Clothing.created_at.desc()).limit(7).all()
    clients = ClientShowcase.query.filter_by(permission_confirmed=True).order_by(ClientShowcase.created_at.desc()).limit(6).all()
    from datetime import datetime
    return render_template('public/home.html', settings=settings,
                           just_dropped=just_dropped, latest=latest, featured=featured,
                           best_loved=best_loved, new_in=new_in, mens=mens, womens=womens,
                           wedding=wedding, now=datetime.now(), categories=categories, category_cards=category_cards,
                           gallery_images=gallery_images, clients=clients)


@public_bp.route('/newsletter/subscribe', methods=['POST'])
@limiter.limit('10 per minute')
def newsletter_subscribe():
    data = _input_data()
    email = _email(data, required=True)
    visitor = None
    pid = session.get('visitor_public_id')
    if pid:
        visitor = Visitor.query.filter_by(public_id=pid).first()
    if visitor is None:
        import uuid
        visitor = Visitor(public_id=uuid.uuid4().hex, email=email, newsletter_subscribed=True)
        db.session.add(visitor)
        db.session.commit()
    else:
        visitor.email = email
        visitor.newsletter_subscribed = True
        db.session.commit()
    session['visitor_public_id'] = visitor.public_id
    session['visitor_prompted'] = True
    return jsonify({'ok': True})

@public_bp.route('/collections')
def collections():
    settings = _settings()
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    if len(q) > 200 or len(category) > 80:
        abort(400, description='Search input is too long.')
    pagination = _filter_clothes(q, category).order_by(Clothing.created_at.desc(), Clothing.id.desc()).paginate(per_page=24, max_per_page=24)
    clothes = pagination.items
    categories = [c[0] for c in db.session.query(Clothing.category).distinct().all() if c[0]]
    return render_template('public/collections.html', settings=settings, clothes=clothes,
                           categories=categories, q=q, category=category, pagination=pagination)


@public_bp.route('/new-designs')
def new_designs():
    settings = _settings()
    clothes = Clothing.query.order_by(Clothing.created_at.desc()).limit(24).all()
    just_dropped = clothes[0] if clothes else None
    rest = clothes[1:] if len(clothes) > 1 else []
    return render_template('public/new_designs.html', settings=settings, clothes=clothes,
                           just_dropped=just_dropped, rest=rest)

@public_bp.route('/about')
def about():
    settings = _settings()
    achievements = Achievement.query.order_by(Achievement.display_order, Achievement.created_at).all()
    clients = ClientShowcase.query.filter_by(permission_confirmed=True).order_by(ClientShowcase.created_at.desc()).all()
    return render_template('public/about.html', settings=settings, achievements=achievements, clients=clients)


@public_bp.route('/contact')
def contact():
    settings = _settings()
    return render_template('public/contact.html', settings=settings)


@public_bp.route('/clothes/<slug>')
def clothing_detail(slug):
    clothing = Clothing.query.filter_by(slug=slug).first_or_404()
    _record_activity(clothing, 'VIEW', 'view_count')
    settings = _settings()
    return render_template('public/clothing_detail.html', clothing=clothing, settings=settings)


@public_bp.route('/like/<int:clothing_id>', methods=['POST'])
@limiter.limit('60 per minute')
def like(clothing_id):
    clothing = db.get_or_404(Clothing, clothing_id)
    liked = session.get('liked_ids', [])
    if clothing_id not in liked:
        _record_activity(clothing, 'LIKE', 'likes')
        liked.append(clothing_id)
        session['liked_ids'] = liked
    return jsonify({'likes': clothing.likes})


@public_bp.route('/interest/<int:clothing_id>', methods=['POST'])
@limiter.limit('60 per minute')
def interest(clothing_id):
    clothing = db.get_or_404(Clothing, clothing_id)
    answer = _text(_input_data(), 'answer', 3).lower()
    if answer not in {'yes', 'no'}:
        return jsonify({'error': 'invalid'}), 400
    answered = session.get('interest_ids', [])
    if clothing_id not in answered:
        _record_activity(clothing, 'INTERESTED' if answer == 'yes' else 'NOT_INTERESTED',
                         'interested_count' if answer == 'yes' else 'not_interested_count')
        session['interest_ids'] = answered + [clothing_id]
    if answer == 'yes':
        return jsonify({'redirect': url_for('public.clothing_detail', slug=clothing.slug)})
    return jsonify({'ok': True})
