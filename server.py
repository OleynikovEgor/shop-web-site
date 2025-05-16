import os
from data.api import api as api_blueprint
from data.cart_items import CartItem
from data.products import Product, ProductVariant
from data.favorites import Favorite
from data.reviews import Review
import json
import re
import random
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import or_
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash
from data.orders import Order, OrderItem
from data import db_session
from data.users import User
from data.addresses import Address
from data.payments import Payment
from data.phone_all import VALID_PREFIXES

app = Flask(__name__)
app.config['SECRET_KEY'] = 'b5d42101e497ef1025d34d1044df5183817ed67f41a48eb653e5dc7c36a88041'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=2)
ALLOWED_IMG = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_VIDEO = {'mp4', 'webm', 'ogg'}

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads', 'reviews')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename, exts):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in exts


app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_TLS=False,
    MAIL_USE_SSL=True,
    MAIL_USERNAME='olegorandr@gmail.com',
    MAIL_PASSWORD='zemb ytvd tdme qycp',
    MAIL_DEFAULT_SENDER='olegorandr@gmail.com'
)
mail = Mail(app)

serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


def is_strong_password(pw: str) -> bool:
    return bool(re.match(r'^(?=.*[A-Z])(?=.*[\d\W])[A-Za-z\d\W_]+$', pw))



@app.route('/verify-registration', methods=['GET', 'POST'])
def verify_registration():
    if 'reg_data' not in session or 'reg_code' not in session:
        return redirect(url_for('reg'))


    if request.method == 'GET' and not session.get('reg_email_sent', False):
        code = session['reg_code']
        email = session['reg_data']['email']
        msg = Message(
            subject='Код подтверждения регистрации',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email],
            body=f'Ваш код подтверждения: {code}'
        )
        mail.send(msg)
        session['reg_email_sent'] = True

    if request.method == 'POST':
        entered = request.form.get('code', '').strip()
        if entered == session['reg_code']:
            data = session.pop('reg_data')
            session.pop('reg_code')
            session.pop('reg_email_sent', None)

            db_sess = db_session.create_session()
            user = User(
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone_num=data['phone_num'],
                email=data['email'],
                gender=data['gender']
            )
            user.set_password(data['password'])
            db_sess.add(user)
            db_sess.commit()


            session['user_id'] = user.id
            session['login_time'] = datetime.now().strftime("%Y-%m-%d")

            return redirect(url_for('main_page'))
        else:
            flash('Неверный код подтверждения', 'warning')

    return render_template('verify_registration.html')



@app.before_request
def check_daily_logout():
    if "login_time" in session:
        if session["login_time"] != datetime.now().strftime("%Y-%m-%d"):
            session.clear()



def is_valid_phone(phone):
    return len(phone) == 12 and phone[2:5] in VALID_PREFIXES


def is_valid_email(email):
    db_sess = db_session.create_session()
    return bool(db_sess.query(User).filter(User.email == email).first())



@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email).first()
        if not user:
            flash('Пользователь с таким email не найден.', 'warning')
            return redirect(url_for('forgot_password'))


        token = serializer.dumps(email, salt='password-reset-salt')
        reset_link = url_for('reset_password', token=token, _external=True)
        msg = Message(
            subject="Восстановление пароля",
            recipients=[email],
            html=render_template('email_reset.html', reset_link=reset_link)
        )
        mail.send(msg)


        flash('Письмо со ссылкой для восстановления отправлено на вашу почту.', 'success')
        return redirect(url_for('forgot_password'))

    return render_template('forgot_password.html')


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token,
                                 salt='password-reset-salt',
                                 max_age=3600)
    except (SignatureExpired, BadSignature):
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_pw = request.form['new_password']
        conf_pw = request.form['confirm_password']
        if new_pw != conf_pw:
            flash('Пароли не совпадают.', 'warning')
            return redirect(url_for('reset_password', token=token))
        if not is_strong_password(new_pw):
            flash(
                'Пароль должен содержать минимум одну заглавную, '
                'одну строчную букву и хотя бы одну цифру или спец. символ.',
                'warning'
            )
            return redirect(url_for('reset_password', token=token))

        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == email).first()
        user.set_password(new_pw)
        db_sess.commit()
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)



@app.route('/profile', methods=['GET', 'POST'])
def profile():

    check_daily_logout()
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db_sess = db_session.create_session()
    user_id = session['user_id']


    user      = db_sess.get(User, user_id)
    addresses = db_sess.query(Address).filter(Address.user_id == user_id).all()
    payments  = db_sess.query(Payment).filter(Payment.user_id == user_id).all()
    orders    = db_sess.query(Order).filter(Order.user_id == user_id) \
                    .order_by(Order.id.desc()).all()


    if request.method == 'POST':
        first = request.form.get('first_name') or user.first_name
        last  = request.form.get('last_name')  or user.last_name
        email = request.form.get('email')      or user.email
        phone = request.form.get('phone_num')  or user.phone_num

        errors = {}
        if not is_valid_phone(phone):
            errors['phone'] = 'Некорректный номер телефона.'
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            errors['email'] = 'Некорректный формат email.'
        elif email != user.email and db_sess.query(User).filter(User.email == email).first():
            errors['email'] = 'Email уже зарегистрирован.'

        if errors:
            for msg in errors.values():
                flash(msg, 'warning')
            return redirect(url_for('profile', edit='true') + '#tab-profile')

        user.first_name = first
        user.last_name  = last
        user.email      = email
        user.phone_num  = phone
        db_sess.commit()
        flash('Профиль успешно обновлён', 'success')
        return redirect(url_for('profile') + '#tab-profile')


    open_payment_modal = (request.args.get('modal') == 'payments')
    edit_mode          = (request.args.get('edit')  == 'true')


    delivered_variants = []
    for order in orders:
        if order.status == 'Доставлен':
            for oi in order.items:

                if oi.variant not in delivered_variants:
                    delivered_variants.append(oi.variant)


    return render_template(
        'profile.html',
        user=user,
        addresses=addresses,
        payments=payments,
        orders=orders,
        delivered_variants=delivered_variants,
        open_payment_modal=open_payment_modal,
        edit=edit_mode
    )



def luhn_checksum(number: str) -> bool:
    digits = list(map(int, re.sub(r'\D', '', number)))
    checksum = 0
    oddeven = len(digits) & 1
    for idx, d in enumerate(digits):
        if idx & 1 ^ oddeven:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def validate_expiry(exp: str) -> bool:
    if not re.match(r'^\d{2}/\d{2}$', exp):
        return False
    m, y = map(int, exp.split('/'))
    y += 2000
    if not (1 <= m <= 12):
        return False
    return datetime.now() < datetime(y, m, 1)


def validate_cvv(cvv: str) -> bool:
    return bool(re.fullmatch(r'\d{3,4}', cvv))

@app.route('/order/<int:order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db_sess = db_session.create_session()
    order = db_sess.get(Order, order_id)
    if not order or order.user_id != session['user_id']:
        abort(404)


    expected_date = order.created_at + timedelta(days=3)

    return render_template(
        'order_detail.html',
        order=order,
        expected_date=expected_date
    )


@app.route("/add_payment", methods=["POST"])
def add_payment():
    if "user_id" not in session:
        return redirect(url_for("login"))

    card_number = request.form.get("card_number")
    expiry = request.form.get("expiry_date")
    cvv = request.form.get("cvv")

    errors = []
    if not all([card_number, expiry, cvv]):
        errors.append("Все поля обязательны")
    else:
        if not luhn_checksum(card_number):
            errors.append("Неверный номер карты")
        if not validate_expiry(expiry):
            errors.append("Неверный срок действия")
        if not validate_cvv(cvv):
            errors.append("Неверный CVV")

    if errors:
        for e in errors:
            flash(e, "warning")
        return redirect(url_for("profile", edit="true", modal="payments") + "#tab-payments")

    db_sess = db_session.create_session()
    clean = re.sub(r'\D', '', card_number)
    last4 = clean[-4:]

    for p in db_sess.query(Payment).filter(Payment.user_id == session["user_id"]):
        if check_password_hash(p.card_number, clean):
            flash("Эта карта уже добавлена", "warning")
            return redirect(url_for("profile", edit="true", modal="payments") + "#tab-payments")

    payment = Payment(
        user_id=session["user_id"],
        card_number=generate_password_hash(clean),
        card_last4=last4,
        expiry_date=generate_password_hash(expiry),
        cvv=generate_password_hash(cvv),
        is_default=False
    )
    db_sess.add(payment)
    db_sess.commit()
    flash("Новый метод оплаты успешно добавлен", "success")
    return redirect(url_for("profile", edit="true") + "#tab-payments")


@app.route("/select_payment/<int:payment_id>", methods=["POST"])
def select_payment(payment_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    db_sess = db_session.create_session()
    db_sess.query(Payment).filter(Payment.user_id == session["user_id"]) \
        .update({Payment.is_default: False}, synchronize_session=False)
    pay = db_sess.get(Payment, payment_id)
    if pay and pay.user_id == session["user_id"]:
        pay.is_default = True
        db_sess.commit()
    return redirect(url_for("profile", edit="true", modal="payments") + "#tab-payments")


@app.route("/delete_payment/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db_sess = db_session.create_session()
    pay = db_sess.get(Payment, payment_id)
    if pay and pay.user_id == session["user_id"]:
        db_sess.delete(pay)
        db_sess.commit()
        flash("Метод оплаты удалён", "success")
    else:
        flash("Ошибка при удалении метода оплаты", "warning")
    return redirect(url_for("profile", edit="true") + "#tab-payments")



@app.route("/addresses/add", methods=["POST"])
def add_address():
    if "user_id" not in session:
        return redirect(url_for("login"))
    new_address = request.form.get("new_address")
    if not new_address:
        return redirect(url_for("profile", edit="true") + "#tab-addresses")

    db_sess = db_session.create_session()
    if db_sess.query(Address).filter(
            Address.user_id == session["user_id"],
            Address.address == new_address
    ).first():
        flash("Такой адрес уже существует", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-addresses")

    addr = Address(user_id=session["user_id"], address=new_address)
    if not db_sess.query(Address).filter(Address.user_id == session["user_id"]).all():
        addr.is_default = True
    db_sess.add(addr)
    db_sess.commit()
    flash("Адрес успешно добавлен", "success")
    return redirect(url_for("profile", edit="true") + "#tab-addresses")


@app.route("/address/delete/<int:address_id>", methods=["POST"])
def delete_address(address_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db_sess = db_session.create_session()
    addr = db_sess.get(Address, address_id)
    if addr and addr.user_id == session["user_id"]:
        db_sess.delete(addr)
        db_sess.commit()
    return redirect(url_for("profile", edit="true") + "#tab-addresses")


@app.route("/address/select/<int:address_id>", methods=["POST"])
def select_address(address_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db_sess = db_session.create_session()
    db_sess.query(Address).filter(Address.user_id == session["user_id"]) \
        .update({Address.is_default: False}, synchronize_session=False)
    addr = db_sess.get(Address, address_id)
    if addr and addr.user_id == session["user_id"]:
        addr.is_default = True
        db_sess.commit()
    return redirect(url_for("profile", edit="true") + "#tab-addresses")


@app.route('/change_password', methods=['POST'])
def change_password():
    old_pw = request.form['old_password']
    new_pw = request.form['new_password']
    conf_pw = request.form['confirm_password']

    db_sess = db_session.create_session()
    user = db_sess.get(User, session['user_id'])

    if not user.check_password(old_pw):
        flash("Неверный старый пароль", "warning")
    elif new_pw != conf_pw:
        flash("Новые пароли не совпадают", "warning")
    elif not is_strong_password(new_pw):
        flash(
            "Пароль должен состоять только из латинских букв, "
            "содержать минимум одну заглавную букву и хотя бы одну цифру или спец. символ.",
            "warning"
        )
    else:
        user.set_password(new_pw)
        db_sess.commit()
        flash("Пароль успешно изменён", "success")

    return redirect(url_for('profile', edit='true') + "#tab-security")



@app.route('/reg', methods=['GET', 'POST'])
def reg():
    if request.method == 'POST':
        # нормализуем телефон
        raw_phone = request.form.get('phone', '').strip()
        digits = re.sub(r'\D', '', raw_phone)
        if digits.startswith('8'):
            phone_num = '+7' + digits[1:]
        elif digits.startswith('7') and len(digits) == 11:
            phone_num = '+7' + digits[1:]
        elif len(digits) == 10:
            phone_num = '+7' + digits
        else:
            phone_num = '+' + digits

        email = request.form.get('email', '').lower().strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        password = request.form.get('password', '')
        repassword = request.form.get('repassword', '')
        gender = request.form.get('gender', '')

        phone_error = email_error = password_error = None
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.phone_num == phone_num).first():
            phone_error = 'Номер уже зарегистрирован'
        if db_sess.query(User).filter(User.email == email).first():
            email_error = 'Email уже зарегистрирован'
        if password != repassword:
            password_error = 'Пароли не совпадают'
        elif not is_strong_password(password):
            password_error = (
                'Пароль должен содержать хотя бы одну заглавную, '
                'одну строчную букву и одну цифру или спец. символ.'
            )

        if phone_error or email_error or password_error:
            return render_template(
                'registration.html',
                first_name=first_name,
                last_name=last_name,
                phone=phone_num,
                email=email,
                gender=gender,
                phone_error=phone_error,
                email_error=email_error,
                password_error=password_error
            )


        session['reg_data'] = {
            'first_name': first_name,
            'last_name': last_name,
            'phone_num': phone_num,
            'email': email,
            'gender': gender,
            'password': password
        }
        session['reg_code'] = f"{random.randint(0, 999999):06}"
        session['reg_email_sent'] = False

        return redirect(url_for('verify_registration'))

    return render_template('registration.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        session.clear()
    if request.method == 'POST':
        email_error = password_error = None
        inp_email = (request.form.get('email') or '').lower().strip()
        inp_pass = request.form.get('password') or ''

        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == inp_email).first()
        if not user:
            email_error = 'Пользователь не найден'
        elif not user.check_password(inp_pass):
            password_error = 'Неверный пароль'
        cart_count = len(session.get("cart_items", []))
        if email_error or password_error:
            return render_template(
                'login.html',
                email=inp_email if not email_error else '',
                email_error=email_error,
                password_error=password_error,
                cart_count=cart_count
            )

        session['user_id'] = user.id
        session['login_time'] = datetime.now().strftime("%Y-%m-%d")
        return redirect(url_for('main_page'))
    return render_template('login.html')


@app.before_request
def ensure_session_lists():
    session.setdefault('cart_items', {})
    session.setdefault('liked_items', [])


@app.route('/favorites/add/<int:variant_id>', methods=['POST'])
def add_to_favorites(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    exists = db_sess.query(Favorite).filter_by(
        user_id=session['user_id'],
        variant_id=variant_id
    ).first()
    if not exists:
        db_sess.add(Favorite(user_id=session['user_id'], variant_id=variant_id))
        db_sess.commit()
    return redirect(request.referrer or url_for('main_page'))


@app.route('/favorites/remove/<int:variant_id>', methods=['POST'])
def remove_from_favorites(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    fav = db_sess.query(Favorite).filter_by(
        user_id=session['user_id'],
        variant_id=variant_id
    ).first()
    if fav:
        db_sess.delete(fav)
        db_sess.commit()
    return redirect(request.referrer or url_for('main_page'))


@app.route('/favorites')
def favorites_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    favs = db_sess.query(Favorite).filter_by(user_id=session['user_id']).all()
    liked_ids = [f.variant_id for f in favs]
    variants = []
    if liked_ids:
        variants = db_sess.query(ProductVariant).filter(ProductVariant.id.in_(liked_ids)).all()
    return render_template('favorites.html', products=variants)


@app.context_processor
def inject_context():
    if 'user_id' in session:
        db_sess = db_session.create_session()

        cis = db_sess.query(CartItem).filter_by(user_id=session['user_id']).all()
        cart_items = {ci.variant_id: ci.quantity for ci in cis}
        cart_count = sum(cart_items.values())

        favs = db_sess.query(Favorite).filter_by(user_id=session['user_id']).all()
        liked_ids = {f.variant_id for f in favs}
        liked_count = len(liked_ids)
    else:
        cart_items, cart_count, liked_ids, liked_count = {}, 0, set(), 0

    return dict(
        cart_items=cart_items,
        cart_count=cart_count,
        liked_items=liked_ids,
        liked_count=liked_count
    )




@app.template_filter('thousands_sep')
def thousands_sep(value):
    try:
        return '{:,.0f}'.format(int(value)).replace(',', ' ')
    except (ValueError, TypeError):
        return value



@app.route('/', methods=['GET'])
def main_page():
    db_sess = db_session.create_session()
    q = request.args.get('q', '').strip()
    if q:
        variants = db_sess.query(ProductVariant).filter(
            or_(
                ProductVariant.name.ilike(f'%{q}%'),
                ProductVariant.type.ilike(f'%{q}%')
            )
        ).all()
    else:
        variants = db_sess.query(ProductVariant).all()
    return render_template('main_page.html', products=variants)



@app.route('/add_to_cart/<int:variant_id>', methods=['POST'])
def add_to_cart(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    item = db_sess.query(CartItem).filter_by(
        user_id=session['user_id'],
        variant_id=variant_id
    ).first()
    if item:
        item.quantity += 1
    else:
        item = CartItem(user_id=session['user_id'], variant_id=variant_id, quantity=1)
        db_sess.add(item)
    db_sess.commit()
    return redirect(request.referrer or url_for('main_page'))


@app.route('/remove_from_cart/<int:variant_id>', methods=['POST'])
def remove_from_cart(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    item = db_sess.query(CartItem).filter_by(
        user_id=session['user_id'],
        variant_id=variant_id
    ).first()
    if item:
        if item.quantity > 1:
            item.quantity -= 1
        else:
            db_sess.delete(item)
        db_sess.commit()
    return redirect(request.referrer or url_for('main_page'))


@app.route('/cart')
def cart_view():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    items = db_sess.query(CartItem).filter_by(user_id=session['user_id']).all()
    total = sum(item.subtotal for item in items)
    return render_template('cart.html', items=items, total=total)


@app.route('/product/<int:variant_id>')
def product_detail(variant_id):
    db_sess = db_session.create_session()
    variant = db_sess.query(ProductVariant).get(variant_id)
    if not variant:
        abort(404)

    slides = variant.images_list
    variants = variant.product.variants

    return render_template(
        'product_detail.html',
        product=variant,
        slides=slides,
        variants=variants,
        current_variant=variant
    )


@app.route('/product/<int:variant_id>/review', methods=['GET','POST'])
def review_form(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db_sess = db_session.create_session()

    delivered = (
        db_sess.query(OrderItem)
        .join(Order)
        .filter(
            Order.user_id == session['user_id'],
            Order.status == 'Доставлен',
            OrderItem.variant_id == variant_id
        )
        .first()
    )
    if not delivered:
        flash('Можно оставить отзыв только на доставленные товары', 'warning')
        return redirect(url_for('profile') + '#tab-reviews')


    variant = db_sess.get(ProductVariant, variant_id)
    if request.method == 'GET':
        return render_template('review_form.html', variant=variant)


    text   = request.form.get('text','').strip()
    rating = float(request.form.get('rating', 5.0))


    images = []
    for f in request.files.getlist('images'):
        if f and allowed_file(f.filename, ALLOWED_IMG):
            fn = secure_filename(f"{variant_id}_{session['user_id']}_{f.filename}")
            path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
            f.save(path)
            images.append(fn)


    video_file = request.files.get('video')
    video_fn = None
    if video_file and allowed_file(video_file.filename, ALLOWED_VIDEO):
        video_fn = secure_filename(f"{variant_id}_{session['user_id']}_{video_file.filename}")
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_fn)
        video_file.save(video_path)


    rev = Review(
        user_id     = session['user_id'],
        variant_id  = variant_id,
        text        = text,
        rating      = rating,
        images      = json.dumps(images),
        video_url   = video_fn
    )
    db_sess.add(rev)


    var = variant
    var.reviews_cnt = (var.reviews_cnt or 0) + 1
    var.rating = ( (var.rating or 0)*(var.reviews_cnt-1) + rating ) / var.reviews_cnt

    db_sess.commit()
    flash('Спасибо за ваш отзыв!', 'success')
    return redirect(url_for('profile'))

@app.route('/product/<int:variant_id>/review', methods=['POST'])
def add_review(variant_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db_sess = db_session.create_session()
    user_id = session['user_id']


    delivered = (
        db_sess.query(OrderItem)
               .join(Order)
               .filter(
                   Order.user_id       == user_id,
                   Order.status        == 'delivered',
                   OrderItem.variant_id == variant_id
               )
               .first()
    )
    if not delivered:
        flash('Нельзя оставить отзыв до получения товара.', 'warning')
        return redirect(url_for('product_detail', variant_id=variant_id) + '#reviews')


    text      = request.form.get('text', '').strip()
    rating    = int(request.form.get('rating', 5))
    video_url = request.form.get('video_url', '').strip()


    images = []
    for f in request.files.getlist('images'):
        filename = f.filename or ''
        ext = filename.rsplit('.', 1)[-1].lower()
        if f and ext in ALLOWED_IMG:
            fn = secure_filename(f"{variant_id}_{user_id}_{filename}")
            dest = os.path.join(app.config['UPLOAD_FOLDER'], fn)
            f.save(dest)
            images.append(fn)


    rev = Review(
        user_id    = user_id,
        variant_id = variant_id,
        text       = text,
        rating     = rating,
        images     = json.dumps(images),
        video_url  = video_url,
        created_at = datetime.utcnow()
    )
    db_sess.add(rev)


    var = db_sess.query(ProductVariant).get(variant_id)
    var.reviews_cnt += 1
    var.rating = (var.rating * (var.reviews_cnt - 1) + rating) / var.reviews_cnt

    db_sess.commit()
    flash('Спасибо! Ваш отзыв опубликован.', 'success')
    return redirect(url_for('product_detail', variant_id=variant_id) + '#reviews')

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db_sess = db_session.create_session()
    user_id = session['user_id']

    cart_items = db_sess.query(CartItem).filter_by(user_id=user_id).all()
    if not cart_items:
        flash('Ваша корзина пуста', 'warning')
        return redirect(url_for('main_page'))

    addresses = db_sess.query(Address).filter_by(user_id=user_id).all()
    payments  = db_sess.query(Payment).filter_by(user_id=user_id).all()

    if request.method == 'POST':
        addr_id = int(request.form['address'])
        pay_id  = int(request.form['payment'])
        total   = sum(ci.subtotal for ci in cart_items)


        order = Order(
            user_id=user_id,
            address_id=addr_id,
            payment_id=pay_id,
            total_amount=total
        )
        db_sess.add(order)
        db_sess.flush()


        for ci in cart_items:
            oi = OrderItem(
                order_id   = order.id,
                product_id = ci.variant.product_id,
                variant_id = ci.variant_id,
                quantity   = ci.quantity,
                unit_price = ci.variant.price
            )
            db_sess.add(oi)


            ci.variant.stock -= ci.quantity


            db_sess.delete(ci)

        db_sess.commit()
        flash(f'Заказ #{order.id} оформлен успешно!', 'success')
        return redirect(url_for('order_confirmation', order_id=order.id))

    return render_template(
        'checkout.html',
        cart_items=cart_items,
        addresses=addresses,
        payments=payments
    )

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db_sess = db_session.create_session()
    order = db_sess.get(Order, order_id)
    if not order or order.user_id != session['user_id']:
        abort(404)


    expected_date = order.created_at + timedelta(days=3)

    return render_template(
        'order_confirmation.html',
        order=order,
        expected_date=expected_date
    )

app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    db_session.global_init("db/Buyers.db")
    app.run(debug=True)

































































# я просто хотел 1000 строк)
