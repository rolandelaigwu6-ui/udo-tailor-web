from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db, limiter
from app.models import Admin, Clothing, ClothingImage, SiteSettings, ClothingActivity, Achievement, ClientShowcase
from app.forms import LoginForm, ClothingForm, SettingsForm, AboutProfileForm, AchievementForm, ClientShowcaseForm
from app.utils import save_upload, commit_changes, remove_after_commit

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in.', 'warning')
            return redirect(url_for('admin.login'))
        admin = db.session.get(Admin, session['admin_id'])
        if admin is None:
            session.pop('admin_id', None)
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute')
def login():
    if session.get('admin_id'):
        return redirect(url_for('admin.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and admin.check_password(form.password.data):
            session.clear()
            session['admin_id'] = admin.id
            session.permanent = True
            flash('Welcome back.', 'success')
            return redirect(url_for('admin.dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('admin/login.html', form=form)


@admin_bp.route('/logout', methods=['POST'])
@admin_required
def logout():
    session.pop('admin_id', None)
    flash('Logged out.', 'info')
    return redirect(url_for('public.index'))


@admin_bp.route('/')
@admin_required
def dashboard():
    total_designs = Clothing.query.count()
    total_likes = db.session.query(db.func.sum(Clothing.likes)).scalar() or 0
    total_interested = db.session.query(db.func.sum(Clothing.interested_count)).scalar() or 0
    total_views = db.session.query(db.func.sum(Clothing.view_count)).scalar() or 0
    most_liked = Clothing.query.order_by(Clothing.likes.desc()).limit(5).all()
    most_viewed = Clothing.query.order_by(Clothing.view_count.desc()).limit(5).all()
    recent = Clothing.query.order_by(Clothing.created_at.desc()).limit(5).all()
    total_whatsapp = ClothingActivity.query.filter_by(activity_type='WHATSAPP_CLICK').count()
    most_interested = Clothing.query.order_by(Clothing.interested_count.desc()).limit(5).all()
    most_whatsapp = db.session.query(Clothing, db.func.count(ClothingActivity.id).label('cnt')).join(ClothingActivity).filter(ClothingActivity.activity_type=='WHATSAPP_CLICK').group_by(Clothing.id).order_by(db.desc('cnt')).limit(5).all()
    recent_activity = ClothingActivity.query.order_by(ClothingActivity.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html',
                           total_designs=total_designs, total_likes=total_likes,
                           total_interested=total_interested, total_views=total_views,
                           total_whatsapp=total_whatsapp,
                           most_liked=most_liked, most_viewed=most_viewed,
                           most_interested=most_interested, most_whatsapp=most_whatsapp,
                           recent=recent, recent_activity=recent_activity)


@admin_bp.route('/clothes')
@admin_required
def clothes_list():
    pagination = Clothing.query.order_by(Clothing.created_at.desc(), Clothing.id.desc()).paginate(per_page=24, max_per_page=24)
    return render_template('admin/clothes_list.html', clothes=pagination.items, pagination=pagination)
@admin_bp.route('/clothes/new', methods=['GET', 'POST'])
@admin_required
def clothing_new():
    form = ClothingForm()
    if form.validate_on_submit():
        clothing = Clothing(
            name=form.name.data,
            price=form.price.data,
            category=form.category.data,
            description=form.description.data,
            material=form.material.data,
            sizes=form.sizes.data,
            colors=form.colors.data,
            availability=form.availability.data,
            featured=bool(form.featured.data),
        )
        clothing.slug = clothing.unique_slug(clothing.name)
        db.session.add(clothing)
        db.session.flush()
        files = request.files.getlist('images')
        primary_set = False
        for idx, f in enumerate(files):
            url = save_upload(f)
            if url:
                img = ClothingImage(clothing_id=clothing.id, image_url=url,
                                    is_primary=(not primary_set), sort_order=idx)
                db.session.add(img)
                if not primary_set:
                    primary_set = True
        commit_changes()
        flash('Design published.', 'success')
        return redirect(url_for('admin.clothes_list'))
    return render_template('admin/clothing_form.html', form=form, clothing=None)


@admin_bp.route('/clothes/<int:clothing_id>/edit', methods=['GET', 'POST'])
@admin_required
def clothing_edit(clothing_id):
    clothing = db.get_or_404(Clothing, clothing_id)
    form = ClothingForm(obj=clothing)
    if form.validate_on_submit():
        clothing.name = form.name.data
        clothing.price = form.price.data
        clothing.category = form.category.data
        clothing.description = form.description.data
        clothing.material = form.material.data
        clothing.sizes = form.sizes.data
        clothing.colors = form.colors.data
        clothing.availability = form.availability.data
        clothing.featured = bool(form.featured.data)
        clothing.slug = clothing.unique_slug(clothing.name)
        files = request.files.getlist('images')
        primary_exists = any(img.is_primary for img in clothing.images)
        idx_start = len(clothing.images)
        for idx, f in enumerate(files):
            url = save_upload(f)
            if url:
                img = ClothingImage(clothing_id=clothing.id, image_url=url,
                                    is_primary=(not primary_exists and idx == 0),
                                    sort_order=idx_start + idx)
                db.session.add(img)
                if not primary_exists and idx == 0:
                    primary_exists = True
        commit_changes()
        flash('Design updated.', 'success')
        return redirect(url_for('admin.clothes_list'))
    return render_template('admin/clothing_form.html', form=form, clothing=clothing)


@admin_bp.route('/clothes/<int:clothing_id>/delete', methods=['POST'])
@admin_required
def clothing_delete(clothing_id):
    clothing = db.get_or_404(Clothing, clothing_id)
    for img in clothing.images:
        remove_after_commit(img.image_url)
    db.session.delete(clothing)
    commit_changes()
    flash('Design deleted.', 'info')
    return redirect(url_for('admin.clothes_list'))


@admin_bp.route('/clothes/<int:clothing_id>/image/<int:image_id>/delete', methods=['POST'])
@admin_required
def image_delete(clothing_id, image_id):
    img = ClothingImage.query.filter_by(id=image_id, clothing_id=clothing_id).first_or_404()
    remove_after_commit(img.image_url)
    was_primary = img.is_primary
    db.session.delete(img)
    db.session.flush()
    if was_primary:
        first = ClothingImage.query.filter_by(clothing_id=clothing_id).order_by(ClothingImage.sort_order, ClothingImage.id).first()
        if first:
            first.is_primary = True
    commit_changes()
    flash('Image removed.', 'info')
    return redirect(url_for('admin.clothing_edit', clothing_id=clothing_id))


@admin_bp.route('/clothes/<int:clothing_id>/image/<int:image_id>/primary', methods=['POST'])
@admin_required
def image_primary(clothing_id, image_id):
    img = ClothingImage.query.filter_by(id=image_id, clothing_id=clothing_id).first_or_404()
    ClothingImage.query.filter_by(clothing_id=clothing_id).update({'is_primary': False})
    img.is_primary = True
    commit_changes()
    flash('Primary image updated.', 'success')
    return redirect(url_for('admin.clothing_edit', clothing_id=clothing_id))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    s = SiteSettings.query.first()
    if s is None:
        s = SiteSettings(brand_name='Udo Tailor')
        db.session.add(s)
        commit_changes()
    form = SettingsForm(obj=s)
    if form.validate_on_submit():
        s.brand_name = form.brand_name.data
        s.hero_heading = form.hero_heading.data
        s.hero_description = form.hero_description.data
        s.phone = form.phone.data
        s.whatsapp = form.whatsapp.data
        s.email = form.email.data
        s.address = form.address.data
        s.opening_hours = form.opening_hours.data
        s.bank_name = form.bank_name.data
        s.account_name = form.account_name.data
        s.account_number = form.account_number.data
        s.about = form.about.data
        s.instagram = form.instagram.data
        s.facebook = form.facebook.data
        s.tiktok = form.tiktok.data
        s.social_links = form.social_links.data
        if form.logo.data:
            url = save_upload(form.logo.data)
            if url:
                remove_after_commit(s.logo)
                s.logo = url
        commit_changes()
        flash('Settings saved.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', form=form, settings=s)

@admin_bp.route('/activity')
@admin_required
def activity():
    acts = ClothingActivity.query.order_by(ClothingActivity.created_at.desc()).limit(100).all()
    total_views = ClothingActivity.query.filter_by(activity_type='VIEW').count()
    total_likes = ClothingActivity.query.filter_by(activity_type='LIKE').count()
    total_interested = ClothingActivity.query.filter_by(activity_type='INTERESTED').count()
    total_wa = ClothingActivity.query.filter_by(activity_type='WHATSAPP_CLICK').count()
    return render_template('admin/activity.html', acts=acts, total_views=total_views,
                           total_likes=total_likes, total_interested=total_interested,
                           total_wa=total_wa)


@admin_bp.route('/clothes/<int:clothing_id>/activity')
@admin_required
def clothing_activity(clothing_id):
    clothing = db.get_or_404(Clothing, clothing_id)
    acts = ClothingActivity.query.filter_by(clothing_id=clothing_id).order_by(ClothingActivity.created_at.desc()).limit(100).all()
    stats = {
        'views': ClothingActivity.query.filter_by(clothing_id=clothing_id, activity_type='VIEW').count(),
        'likes': ClothingActivity.query.filter_by(clothing_id=clothing_id, activity_type='LIKE').count(),
        'interested': ClothingActivity.query.filter_by(clothing_id=clothing_id, activity_type='INTERESTED').count(),
        'whatsapp': ClothingActivity.query.filter_by(clothing_id=clothing_id, activity_type='WHATSAPP_CLICK').count(),
        'phone': ClothingActivity.query.filter_by(clothing_id=clothing_id, activity_type='PHONE_CLICK').count(),
    }
    return render_template('admin/clothing_activity.html', clothing=clothing, acts=acts, stats=stats)


@admin_bp.route('/about', methods=['GET', 'POST'])
@admin_required
def about_profile():
    s = _settings()
    form = AboutProfileForm(obj=s)
    if form.validate_on_submit():
        s.designer_name = form.designer_name.data
        s.designer_title = form.designer_title.data
        s.designer_bio = form.designer_bio.data
        s.years_experience = form.years_experience.data
        s.specialties = form.specialties.data
        s.signature_style = form.signature_style.data
        if form.designer_image.data:
            url = save_upload(form.designer_image.data)
            if url:
                remove_after_commit(s.designer_image)
                s.designer_image = url
        commit_changes()
        flash('Profile updated.', 'success')
        return redirect(url_for('admin.about_profile'))
    achievements = Achievement.query.order_by(Achievement.display_order, Achievement.created_at).all()
    showcase = ClientShowcase.query.order_by(ClientShowcase.created_at.desc()).all()
    return render_template('admin/about_profile.html', form=form, settings=s,
                           achievements=achievements, showcase=showcase)


def _settings():
    from app.models import SiteSettings
    s = SiteSettings.query.first()
    if s is None:
        s = SiteSettings()
        db.session.add(s)
        commit_changes()
    return s

@admin_bp.route('/achievements/new', methods=['GET', 'POST'])
@admin_required
def achievement_new():
    form = AchievementForm()
    if form.validate_on_submit():
        a = Achievement(title=form.title.data, description=form.description.data,
                        year=form.year.data, display_order=form.display_order.data or 0)
        if form.image.data:
            url = save_upload(form.image.data)
            if url:
                a.image_url = url
        db.session.add(a)
        commit_changes()
        flash('Achievement added.', 'success')
        return redirect(url_for('admin.about_profile'))
    return render_template('admin/achievement_form.html', form=form)


@admin_bp.route('/achievements/<int:aid>/delete', methods=['POST'])
@admin_required
def achievement_delete(aid):
    a = db.get_or_404(Achievement, aid)
    remove_after_commit(a.image_url)
    db.session.delete(a)
    commit_changes()
    flash('Achievement removed.', 'info')
    return redirect(url_for('admin.about_profile'))

@admin_bp.route('/showcase')
@admin_required
def showcase_list():
    pagination = ClientShowcase.query.order_by(ClientShowcase.created_at.desc(), ClientShowcase.id.desc()).paginate(per_page=24, max_per_page=24)
    return render_template('admin/showcase_list.html', items=pagination.items, pagination=pagination)


@admin_bp.route('/showcase/new', methods=['GET', 'POST'])
@admin_required
def showcase_new():
    form = ClientShowcaseForm()
    if form.validate_on_submit():
        item = ClientShowcase(client_name=form.client_name.data, design_name=form.design_name.data,
                              description=form.description.data, price=form.price.data,
                              category=form.category.data, testimonial=form.testimonial.data,
                              permission_confirmed=bool(form.permission_confirmed.data),
                              featured=bool(form.featured.data))
        if form.image.data:
            url = save_upload(form.image.data)
            if url:
                remove_after_commit(item.image_url)
                item.image_url = url
        db.session.add(item)
        commit_changes()
        flash('Showcase item added.', 'success')
        return redirect(url_for('admin.showcase_list'))
    return render_template('admin/showcase_form.html', form=form)


@admin_bp.route('/showcase/<int:iid>/edit', methods=['GET', 'POST'])
@admin_required
def showcase_edit(iid):
    item = db.get_or_404(ClientShowcase, iid)
    form = ClientShowcaseForm(obj=item)
    if form.validate_on_submit():
        item.client_name = form.client_name.data
        item.design_name = form.design_name.data
        item.description = form.description.data
        item.price = form.price.data
        item.category = form.category.data
        item.testimonial = form.testimonial.data
        item.permission_confirmed = bool(form.permission_confirmed.data)
        item.featured = bool(form.featured.data)
        if form.image.data:
            url = save_upload(form.image.data)
            if url:
                remove_after_commit(item.image_url)
                item.image_url = url
        commit_changes()
        flash('Showcase item updated.', 'success')
        return redirect(url_for('admin.showcase_list'))
    return render_template('admin/showcase_form.html', form=form, item=item)


@admin_bp.route('/showcase/<int:iid>/delete', methods=['POST'])
@admin_required
def showcase_delete(iid):
    item = db.get_or_404(ClientShowcase, iid)
    remove_after_commit(item.image_url)
    db.session.delete(item)
    commit_changes()
    flash('Showcase item removed.', 'info')
    return redirect(url_for('admin.showcase_list'))
