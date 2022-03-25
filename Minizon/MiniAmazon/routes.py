from MiniAmazon import app, db
from flask import render_template, redirect, url_for, flash, request
from MiniAmazon.models import Item, User, ItemRating, ItemUpvote
from MiniAmazon.forms import RegisterForm, LoginForm
from flask_login import login_user, login_required, logout_user, current_user
from sqlalchemy import func, case
import json

# ----------------
# HELPER METHODS
# ----------------
# returns a boolean mask of length 5
# that represents the ratings
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


@app.route("/item_upvote", methods=['POST'])
def item_upvote():
    assert request.method == "POST"

    argument = json.loads(request.data.decode("utf-8"))
    assert "user" in argument and "rating" in argument, "Illegal Data provided"

    voter_id = argument['user']
    rating_id = argument['rating']
    query = ItemUpvote.query.filter(ItemUpvote.rating_id == rating_id, ItemUpvote.voter_id == voter_id)
    is_voted = len(query.all())

    if is_voted != 0:
        print(query.all())
        assert query.delete() != 0, "Number of Item Upvotes in database is inconsistent with is_voted"
        db.session.commit()
    else:
        upvote = ItemUpvote(rating_id=rating_id, voter_id=voter_id)
        db.session.add(upvote)
        db.session.commit()

    q = ItemUpvote.query.filter(ItemUpvote.rating_id == rating_id).\
        group_by(ItemUpvote.rating_id).\
        with_entities(
            func.count(ItemUpvote.voter_id).label("num_upvotes"),
            func.max(
                case([(ItemUpvote.voter_id == current_user.id, 1)], else_=0)
            ).label("is_voted")
        ).all()
    assert len(q) == 1, "Item Upvote aggregation returned multiple instances"
    return {'upvotes': q[0].num_upvotes, 'voted': q[0].is_voted == 1}


@app.route('/item_info/<int:id>')
@login_required
def item_info_page(id):
    item = Item.query.get_or_404(id)

    # cursor.execute("select avg(rate) from ItemRating where item_id == ?", (id))
    average = ItemRating.query.\
        with_entities(func.avg(ItemRating.rate).label('average')).\
        filter(ItemRating.item_id == id).all()[0][0]

    # cursor.execute("select * from ItemRating where item_id == ?", (id))
    # ratings = ItemRating.query.filter(ItemRating.item_id == id).all()
    # ----------------
    # Translates the following sql:
    # --------
    # select
    #     withname.id,
    #     withname.name,
    #     withname.item,
    #     withname.comment,
    #     withname.rate,
    #     withname.ts,
    #     count(upvote.voter_id),
    #     exists (
    #         select 1
    #     from upvote
    #         where
    #     withname.id == upvote.rating_id
    #     and
    #     upvote.voter_id == ?)
    # from upvote join (
    #         select
    #         rating.id as id,
    #         user.name as name,
    #         rating.item_id as item,
    #         rating.comment as comment,
    #         rating.rate as rate,
    #         rating.ts as ts
    #     from rating join user on rating.rater_id == user.id
    #     where rating.item_id == ?
    # ) as withname
    # on upvote.rating_id == withname.id
    # group by withname.id
    # --------
    # ?, ? represents (current user, current item)
    # ----------------
    subq = ItemRating.query.filter(ItemRating.item_id == item.id). \
        join(User, User.id == ItemRating.rater_id). \
        with_entities(
            ItemRating.id.label("rating_id"),
            User.name.label("name"),
            ItemRating.item_id.label("item_id"),
            ItemRating.comment.label("comment"),
            ItemRating.rate.label("rate"),
            ItemRating.ts.label("ts")
        ).\
        subquery()

    q = ItemUpvote.query.\
        join(subq, subq.c.rating_id == ItemUpvote.rating_id). \
        group_by(
            subq.c.rating_id,
            subq.c.name,
            subq.c.item_id,
            subq.c.comment,
            subq.c.rate,
            subq.c.ts). \
        with_entities(
            subq.c.rating_id.label("rating_id"),
            subq.c.name.label("commenter"),
            subq.c.item_id.label("item_id"),
            subq.c.comment.label("comment"),
            subq.c.rate.label("rate"),
            subq.c.ts.label("ts"),
            func.count(ItemUpvote.voter_id).label("num_upvotes"),
            func.max(
                case([(ItemUpvote.voter_id == current_user.id, 1)], else_=0)
            ).label("is_voted")
        )
    ratings = q.all()

    # cursor.execute("select rate, count(rater_id) as cnt
    #                   from ItemRating
    #                   where item_id == ?
    #                   group by rate", (id))
    distribution = ItemRating.query.filter(ItemRating.item_id == id).\
        with_entities(ItemRating.rate, func.count(ItemRating.rater_id).label("cnt")).\
        group_by(ItemRating.rate).all()

    actuals = {x: 0 for x in range(6)}
    for item in distribution:
        actuals[item[0]] = item[1]

    # cursor.execute("select
    #                   from ItemRating
    #                       inner join ItemUpvote on ItemRating.id == ItemUpvote.rating_id", ())

    return render_template('item_info.html', item=item,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user)


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404