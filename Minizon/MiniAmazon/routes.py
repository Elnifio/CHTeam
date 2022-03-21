from MiniAmazon import app, db
from flask import render_template, redirect, url_for, flash
from MiniAmazon.models import Item, User, ItemRating
from MiniAmazon.forms import RegisterForm, LoginForm
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import func

# ----------------
# HELPER METHODS
# ----------------
def to_boolean_mask(nstar):
    nstar = min(nstar, 5)
    nstar = max(nstar, 0)
    return [True] * nstar + [False] * (5 - nstar)

@app.route('/')
@app.route('/home')
@login_required
def home_page():
    return render_template('home.html')


@app.route('/market')
@login_required
def market_page():
    items = Item.query.all()
    return render_template('market.html', items=items)


@app.route('/register', methods=['GET', 'POST'])
def register_page():
    form = RegisterForm()
    if form.validate_on_submit():
        user_to_register = User(name=form.username.data,
                                email=form.email.data,
                                address=form.address.data,
                                password_plain=form.password1.data
                                )
        db.session.add(user_to_register)
        db.session.commit()

        login_user(user_to_register)
        flash(f'Login Success! Welcome, {user_to_register.name}!', category='success')
        return redirect(url_for('home_page'))
    # TODO: catch error from sqlaclchemy
    # TODO: balance
    if form.errors != {}:
        for err_msg in form.errors.values():
            flash(f'Error: {err_msg}', category='danger')
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    form = LoginForm()
    if form.validate_on_submit():
        attempted_user = User.query.filter_by(email=form.email.data).first()
        if attempted_user and attempted_user.check_password_correct(
            plaintext=form.password.data
        ):
            login_user(attempted_user)
            flash(f'Login Success! Welcome, {attempted_user.name}!', category='success')
            # TODO: page after login
            return redirect(url_for('home_page'))
        else:
            flash('Email and password not match! Please try again.', category='danger')
    # TODO: add on: email not found, go to register
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    flash(f'Logout Success!', category='success')
    return render_template('home.html')


@app.route('/item_info/<int:id>')
@login_required
def item_info_page(id):
    item = Item.query.get_or_404(id)
    average = ItemRating.query.\
        with_entities(func.avg(ItemRating.rate).label('average')).\
        filter(ItemRating.item_id == id).all()[0][0]

    ratings = ItemRating.query.filter(ItemRating.item_id == id).all()

    distribution = ItemRating.query.filter(ItemRating.item_id == id).\
        with_entities(ItemRating.rate, func.count(ItemRating.rater_id).label("cnt")).\
        group_by(ItemRating.rate).all()

    actuals = {x: 0 for x in range(6)}
    for item in distribution:
        actuals[item[0]] = item[1]

    return render_template('item_info.html', item=item,
                           reviews=ratings, average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask)


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404