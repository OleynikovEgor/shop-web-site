from flask import Flask, render_template, request, redirect, url_for, session, flash
from data import db_session
from data.users import User
from data.addresses import Address
from data.payments import Payment
from data.phone_all import VALID_PREFIXES
from datetime import timedelta, datetime
import os
import re
from werkzeug.security import generate_password_hash, generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=2)


@app.before_request
def check_daily_logout():
    if "login_time" in session:
        last_login_date = session["login_time"]
        current_date = datetime.now().strftime("%Y-%m-%d")
        if last_login_date != current_date:
            session.clear()


def is_valid_phone(phone):
    # Ожидаем формат: +7XXXXXXXXXX (всего 12 символов)
    if len(phone) != 12:
        return False
    # Проверка по префиксу (символы с 3 по 5 индекс)
    return phone[2:5] in VALID_PREFIXES


def is_valid_email(email):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.email == email).first()
    return bool(user)


# ====== Профиль, адреса и платежи ======
@app.route("/profile", methods=["GET", "POST"])
def profile():
    check_daily_logout()
    if "user_id" not in session:
        return redirect(url_for("login"))
    db_sess = db_session.create_session()
    user = db_sess.get(User, session.get("user_id"))

    # Загружаем список адресов и платежных методов для отображения в профиле
    addresses = db_sess.query(Address).filter(Address.user_id == session["user_id"]).all()
    payments = db_sess.query(Payment).filter(Payment.user_id == session["user_id"]).all()

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone_num = request.form.get("phone_num")

        # Если поля не заполнены, оставляем предыдущие значения
        if not first_name:
            first_name = user.first_name
        if not last_name:
            last_name = user.last_name
        if not email:
            email = user.email
        if not phone_num:
            phone_num = user.phone_num

        # Приводим номер к нужному формату, если начинается с "8"
        if phone_num.startswith("8"):
            phone_num = "+7" + phone_num[1:]

        errors = {}
        if not is_valid_phone(phone_num):
            errors["phone_error"] = "Некорректный номер телефона."

        # Проверка формата email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors["email_error"] = "Некорректный формат email."
        else:
            if email != user.email:
                existing_user = db_sess.query(User).filter(User.email == email).first()
                if existing_user:
                    errors["email_error"] = "Пользователь с таким email уже существует."

        if errors:
            for e in errors.values():
                flash(e, "warning")
            return redirect(url_for("profile", edit="true"))

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone_num = phone_num
        db_sess.commit()
        flash("Профиль успешно обновлён", "success")
        return redirect(url_for("profile"))

    edit_mode = request.args.get("edit") == "true"
    return render_template("profile.html", user=user, edit=edit_mode, addresses=addresses, payments=payments)


# ========= Адреса =========
@app.route("/addresses/add", methods=["POST"])
def add_address():
    if "user_id" not in session:
        return redirect(url_for("login"))
    new_address = request.form.get("new_address")
    if not new_address:
        return redirect(url_for("profile", edit="true") + "#tab-addresses")
    db_sess = db_session.create_session()

    # Проверка на наличие дубликата
    existing_address = db_sess.query(Address).filter(
        Address.user_id == session["user_id"],
        Address.address == new_address
    ).first()
    if existing_address:
        flash("Такой адрес уже существует", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-addresses")

    addr = Address(user_id=session["user_id"], address=new_address)
    # Если это первый адрес, то он становится адресом по умолчанию
    existing_addresses = db_sess.query(Address).filter(Address.user_id == session["user_id"]).all()
    if not existing_addresses:
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
    db_sess.query(Address).filter(Address.user_id == session["user_id"]).update({"is_default": False})
    addr = db_sess.get(Address, address_id)
    if addr and addr.user_id == session["user_id"]:
        addr.is_default = True
        db_sess.commit()
    return redirect(url_for("profile", edit="true") + "#tab-addresses")


# ========= Платежи =========

def luhn_checksum(card_number: str) -> bool:
    card_number = re.sub(r'[\s-]', '', card_number)

    def digits_of(n):
        return [int(d) for d in n]

    try:
        digits = digits_of(card_number)
    except ValueError:
        return False
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(digits_of(str(d * 2)))
    return checksum % 10 == 0


def validate_expiry_date(expiry: str) -> bool:
    if not re.match(r'^\d{2}/\d{2}$', expiry):
        return False
    try:
        exp_month, exp_year = expiry.split('/')
        exp_month = int(exp_month)
        exp_year = int(exp_year) + 2000
        if exp_month < 1 or exp_month > 12:
            return False
        if exp_month == 12:
            next_month = datetime(exp_year + 1, 1, 1)
        else:
            next_month = datetime(exp_year, exp_month + 1, 1)
        return datetime.now() < next_month
    except Exception:
        return False


def validate_cvv(cvv: str) -> bool:
    return bool(re.fullmatch(r'\d{3,4}', cvv))


@app.route("/add_payment", methods=["POST"])
def add_payment():
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Получаем данные из формы (например, из модального окна во вкладке "Платежи")
    card_number = request.form.get("card_number")
    card_holder = request.form.get("card_holder")
    expiry_date = request.form.get("expiry_date")
    cvv = request.form.get("cvv")

    if not all([card_number, card_holder, expiry_date, cvv]):
        flash("Все поля должны быть заполнены", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-payments")

    # Чистим номер карты (удаляем пробелы и тире)
    cleaned_number = re.sub(r'[\s-]', '', card_number)

    if not luhn_checksum(cleaned_number):
        flash("Номер карты не проходит проверку по алгоритму Луна", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-payments")

    if not validate_expiry_date(expiry_date):
        flash("Срок действия карты указан неверно или карта истекла", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-payments")

    if not validate_cvv(cvv):
        flash("CVV должен содержать 3 или 4 цифры", "warning")
        return redirect(url_for("profile", edit="true") + "#tab-payments")

    # Проверяем, нет ли уже сохранённой карты с таким номером
    db_sess = db_session.create_session()
    existing_payments = db_sess.query(Payment).filter(Payment.user_id == session["user_id"]).all()
    for payment in existing_payments:
        # Используем check_password_hash для сравнения
        if check_password_hash(payment.card_number, cleaned_number):
            flash("Эта карта уже добавлена", "warning")
            return redirect(url_for("profile", edit="true") + "#tab-payments")

    # Извлекаем последние 4 цифры номера карты для отображения
    card_last4 = cleaned_number[-4:]

    # Хэширование данных карты через werkzeug.security
    hashed_card_number = generate_password_hash(cleaned_number)
    hashed_card_holder = generate_password_hash(card_holder)
    hashed_expiry_date = generate_password_hash(expiry_date)
    hashed_cvv = generate_password_hash(cvv)

    payment = Payment(
        user_id=session["user_id"],
        card_number=hashed_card_number,
        card_last4=card_last4,
        card_holder=hashed_card_holder,
        expiry_date=hashed_expiry_date,
        cvv=hashed_cvv
    )
    db_sess.add(payment)
    db_sess.commit()
    flash("Новый метод оплаты успешно добавлен", "success")
    return redirect(url_for("profile", edit="true") + "#tab-payments")



@app.route("/delete_payment/<int:payment_id>", methods=["POST"])
def delete_payment(payment_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db_sess = db_session.create_session()
    payment = db_sess.get(Payment, payment_id)
    if payment and payment.user_id == session["user_id"]:
        db_sess.delete(payment)
        db_sess.commit()
        flash("Метод оплаты удалён", "success")
    else:
        flash("Ошибка при удалении метода оплаты", "warning")
    return redirect(url_for("profile", edit="true") + "#tab-payments")


# ========= Регистрация =========
@app.route("/reg", methods=["GET", "POST"])
def reg():
    if request.method == "POST":
        phone_error = email_error = password_error = None

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone_num = request.form.get("phone")
        email = request.form.get("email").lower()
        password = request.form.get("password")
        repassword = request.form.get("repassword")
        gender = request.form.get("gender")  # новое поле

        if phone_num.startswith("8"):
            phone_num = "+7" + phone_num[1:]

        if not is_valid_phone(phone_num):
            phone_error = "Некорректный номер"

        db_sess = db_session.create_session()

        if db_sess.query(User).filter(User.phone_num == phone_num).first():
            phone_error = "Пользователь с таким номером уже зарегистрирован"

        if is_valid_email(email):
            email_error = "Пользователь с таким email уже зарегистрирован"

        if password != repassword:
            password_error = "Пароли не совпадают"

        if phone_error or email_error or password_error:
            return render_template("registration.html",
                                   first_name=first_name,
                                   last_name=last_name,
                                   phone=phone_num,
                                   email=email,
                                   gender=gender,
                                   phone_error=phone_error,
                                   email_error=email_error,
                                   password_error=password_error)

        user = User(first_name=first_name, last_name=last_name, phone_num=phone_num, email=email, gender=gender)
        user.set_password(password)
        db_sess.add(user)
        db_sess.commit()

        return redirect(url_for("main_page"))

    return render_template("registration.html")


# ========= Авторизация =========
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        session.clear()
    if request.method == "POST":
        email_error = password_error = None
        db_sess = db_session.create_session()
        inp_email = request.form.get("exampleInputEmail1").lower()
        inp_pass = request.form.get("exampleInputPassword1")
        user = db_sess.query(User).filter(User.email == inp_email).first()
        db_sess.commit()

        if not user:
            email_error = "Пользователь с таким email не найден"
        elif not user.check_password(inp_pass):
            password_error = "Неверный пароль"

        if email_error or password_error:
            return render_template("login.html",
                                   email=inp_email if not email_error else '',
                                   email_error=email_error,
                                   password_error=password_error)

        session["user_id"] = user.id
        session["login_time"] = datetime.now().strftime("%Y-%m-%d")
        return redirect(url_for("main_page"))

    return render_template("login.html")


@app.route("/")
def main_page():
    return render_template("main_page.html", logged_in="user_id" in session)


def main():
    db_session.global_init("db/Buyers.db")
    app.run(debug=True)


if __name__ == '__main__':
    main()
