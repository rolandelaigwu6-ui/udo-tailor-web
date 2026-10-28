
from app import db


def seed_admin(app):
    from app.models import Admin
    from werkzeug.security import generate_password_hash
    username = app.config['ADMIN_USERNAME']
    password = app.config['ADMIN_PASSWORD']
    if Admin.query.count() == 0:
        admin = Admin(username=username, password_hash=generate_password_hash(password))
        db.session.add(admin)
        db.session.commit()


def seed_settings():
    from app.models import SiteSettings
    if SiteSettings.query.count() == 0:
        s = SiteSettings(
            brand_name='Udo Tailor',
            hero_heading='Crafted With Precision. Designed For You.',
            hero_description='Premium Nigerian and African fashion for every occasion.',
            phone='+234 800 000 0000',
            whatsapp='2348000000000',
            email='hello@udotailor.com',
            address='Lagos, Nigeria',
            opening_hours='Mon - Sat, 9am - 6pm',
            about='Udo Tailor creates premium clothing and custom designs with careful craftsmanship and modern African style.',
            designer_image='img/WhatsApp Image 2026-10-28 at 11.24.34 AM.jpeg',
            designer_name='Udo Tailor',
            designer_title='Founder & Creative Director',
            designer_bio='Udo Tailor creates premium clothing and custom designs with careful craftsmanship and modern African style.',
            years_experience='10+',
            specialties='Agbada, Senator, Kaftan, Ankara, Aso Oke, Adire, Buba and Iro, Lace, Baggy Jean native, Bridal and ceremonial wear',
            signature_style='Precision tailoring with a modern interpretation of Nigerian traditional wear, detailed embroidery and premium fabric selection.',
            instagram='https://instagram.com/udotailor',
            facebook='https://facebook.com/udotailor',
            tiktok='https://tiktok.com/@udotailor',
        )
        db.session.add(s)
        db.session.commit()
def seed_demo_data():
    from app.models import Clothing, ClothingImage
    if Clothing.query.count() > 0:
        return
    images = [
        'https://images.unsplash.com/photo-1493357335960-4583bfa6f8d9?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1535530705774-695729778c55?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1557321247-f3b7ac08a75a?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1586470208462-01ac006ae264?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1587425206783-d51b608ea87e?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1599950755142-d471f509a534?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1600713257155-b061ef5fb0f3?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1603530066858-c589c83d99bd?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1619292843545-96ba1f41c4f4?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1620138996011-943081eb5a10?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1623460445314-2d4959a8bcca?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1626596662792-12cdc7ecce71?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1630168657978-979878c05a42?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1646178070829-e0070110e61a?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1660827915351-56b260b17a09?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1663593185972-4c3d2c1b9535?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1669197795882-0769e6908096?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1670855822901-5786604e9c40?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1677442992191-33e64435ad7e?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1678274342617-09c13eefab9f?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1687276154818-d555a7b337ba?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1687276154823-66f9cba2e484?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1693930446116-3434cbc30e57?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1693987661225-4f4716d3caa8?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1693988511054-4159e875966c?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1693988513572-9c7ca45ba5e4?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1693989651221-c7af9e752ab0?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1697677791983-b489f1b19700?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1697677791984-5bb30a8a6a25?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1697677913862-ba6af4f2f024?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1704775989090-452868cbeb75?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1708946702646-933a24be239e?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1714030282710-4f003762bfb1?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1715624133436-d3d449d126ea?auto=format&fit=crop&w=900&q=80',
        'https://images.unsplash.com/photo-1716470435412-731a739f9bf8?auto=format&fit=crop&w=900&q=80',
    ]
    for i, img in enumerate(images):
        color = ["Black","Beige","Navy","White","Olive","Brown","Grey","Cream","Charcoal","Khaki","Burgundy","Stone","Blue","Tan","Slate"][i % 15]
        c = Clothing(
            name=f"Oversize Palazzo Trousers {i+1}",
            price=55000 + (i * 1500),
            category="Oversize Palazzo",
            description="Wide-leg oversize palazzo trousers with relaxed tailored fit.",
            material="Premium cotton blend",
            sizes="M, L, XL",
            colors=color,
            availability="Available",
            featured=(i % 5 == 0),
        )
        c.slug = c.unique_slug(c.name)
        db.session.add(c)
        db.session.flush()
        imgrow = ClothingImage(clothing_id=c.id, image_url=img, is_primary=True, sort_order=0)
        db.session.add(imgrow)
    db.session.commit()
