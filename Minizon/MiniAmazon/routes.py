from MiniAmazon import app, db, ALLOWED_EXTENSIONS
from flask import render_template, redirect, url_for, flash, request
from MiniAmazon.models import Item, User, Category, ItemImage, Inventory, ItemRating, ItemUpvote, Conversation
from MiniAmazon.forms import RegisterForm, LoginForm, ItemForm, MarketForm, SellForm
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, case
import json
import uuid as uuid
import os


# ----------------
# HELPER METHODS
# ----------------
# returns a boolean mask of length 5
# that represents the ratings
def to_boolean_mask(rate):
    if rate is None:
        return [False] * 5
    nstar = rate.rate
    nstar = min(nstar, 5)
    nstar = max(nstar, 0)
    return [True] * nstar + [False] * (5 - nstar)


def format_time(t):
    return f"{t.month}/{t.day}/{t.year} {t.hour}:{t.minute}:{t.second}"


@app.route('/')
@app.route('/home')
@login_required
def home_page():
    return render_template('home.html')


order_swicthes = {
    'Price': Item.price,
    'Name': Item.name,
    'Rating': Item.rating
}


@app.route('/market', methods=['GET', 'POST'])
@login_required
def market_page():
    items = None
    query = None
    form = MarketForm()
    categories = Category.query.order_by('name').all()
    choices = ['All']
    for c in categories:
        choices.append(c.name)
    form.category.choices = choices
    if request.method == 'POST':
        if form.validate_on_submit():
            # process search
            search = form.search.data
            if form.category.data == 'All':
                # search for item with keyword in name and description
                query = Item.query
            else:
                query = Category.query.filter_by(name=form.category.data).first().items

            query = query.filter(db.or_(
                Item.name.ilike(f'%{search}%'),
                Item.description.ilike(f'%{search}%')
            ))

            # process sort and order
            if form.order_by.data == 'Desc':
                items = query.order_by(order_swicthes.get(form.sort_by.data).desc()).all()
            else:
                items = query.order_by(order_swicthes.get(form.sort_by.data)).all()
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')

    return render_template('market.html', items=items, form=form)


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
@login_required
def item_upvote():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')

    assert request.method == "POST"

    argument = json.loads(request.data.decode("utf-8"))
    if not ("user" in argument and "rating" in argument):
        flash(f'Error: Invalid request data format', category='danger')
    assert "user" in argument and "rating" in argument, "Illegal Data provided"

    voter_id = argument['user']
    if not voter_id == current_user.id:
        flash(f"Error: Invalid voter", category="danger")
    assert voter_id == current_user.id, "Illegal user detected"

    rating_id = argument['rating']
    query = ItemUpvote.query.filter(ItemUpvote.rating_id == rating_id, ItemUpvote.voter_id == voter_id)
    is_voted = len(query.all())

    if is_voted != 0:
        result = query.delete()
        if result != 0:
            flash("Error: Number of Item Upvotes in database is inconsistent with is_voted")
        assert result != 0, "Number of Item Upvotes in database is inconsistent with is_voted"
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

    if not len(q) == 1:
        flash("Error: Item Upvote aggregation returned multiple instances")
    assert len(q) == 1, "Item Upvote aggregation returned multiple instances"
    return {'upvotes': q[0].num_upvotes, 'voted': q[0].is_voted == 1}


@app.route("/item_review", methods=['POST'])
@login_required
def receive_item_review():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')
    assert request.method == "POST"

    argument = json.loads(request.data.decode("utf-8"))
    for item in ['user', "item", 'rate', 'comment']:
        if item not in argument:
            flash('Error: Invalid request data format', category='danger')
        assert item in argument, item + " not in argument: " + str(argument)

    if not argument['user'] == current_user.id:
        flash(f"Error: Invalid rater", category="danger")
    assert argument['user'] == current_user.id, "Provided user is not current user"

    q = ItemRating.query.filter(ItemRating.item_id == argument['item'], ItemRating.rater_id == argument['user']).all()

    if len(q) == 0:
        new_rate = ItemRating(item_id=argument['item'], rater_id=argument['user'],
                              comment=argument['comment'], rate=argument['rate'])
        db.session.add(new_rate)
        db.session.commit()
        return {"comment": new_rate.comment}
    else:
        roi = q[0]
        roi.comment = argument['comment']
        roi.rate = argument['rate']
        db.session.commit()
        return {'comment': roi.comment}


@app.route("/delete_item_review", methods=["POST"])
@login_required
def delete_review():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')
    assert request.method == "POST"

    argument = json.loads(request.data.decode("utf-8"))
    for item in ['user', "item"]:
        if item not in argument:
            flash('Error: Invalid request data format', category='danger')
        assert item in argument, item + " not in argument: " + str(argument)

    if not argument['user'] == current_user.id:
        flash(f"Error: Invalid rater", category="danger")
    assert argument['user'] == current_user.id, "Provided user is not current user"

    q = ItemRating.query.\
        filter(ItemRating.item_id == argument['item'], ItemRating.rater_id == argument['user']).\
        delete()
    if q == 0:
        flash(f"Error: 0 Rating deleted")
    assert q != 0, "0 rating deleted"

    db.session.commit()
    return {"success": True}


@app.route("/get_conversations", methods=['POST'])
@login_required
def conversations():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')
        return

    argument = json.loads(request.data.decode("utf-8"))
    if "other" not in argument:
        flash(f"Error: Invalid request data format", category='danger')
        return

    other = argument['other']
    q = Conversation.query.filter(
        ((Conversation.sender_id == current_user.id) & (Conversation.receiver_id == other)) |
        ((Conversation.receiver_id == current_user.id) & (Conversation.sender_id == other)))
    q = q.order_by(Conversation.ts)

    flash("Conversation load successful", category="primary")

    return {
        "conversation": list(map(
            lambda x: {
                "type": "send" if x.sender_id == current_user.id else "receive",
                "content": x.content,
                "timestamp": format_time(x.ts)
            }, q.all()
        ))
    }


@app.route("/get_contacts", methods=['POST'])
@login_required
def contacts():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')
        return

    roi = Conversation.query.\
        filter(
            (Conversation.sender_id == current_user.id) |
            (Conversation.receiver_id == current_user.id))

    roi = roi.with_entities(
            case(
                [(Conversation.sender_id == current_user.id, Conversation.receiver_id), ],
                else_=Conversation.sender_id
            ).label("other_id"),
            func.max(Conversation.ts).label("ts"),
        ).group_by(
            case(
                [(Conversation.sender_id == current_user.id, Conversation.receiver_id), ],
                else_=Conversation.sender_id)
        ).subquery()

    senders = Conversation.query.\
        join(roi,
             (roi.c.other_id == Conversation.sender_id) &
             (roi.c.ts == Conversation.ts)).\
        filter(Conversation.receiver_id == current_user.id).\
        join(User, User.id == roi.c.other_id).\
        with_entities(
            Conversation.ts.label("timestamp"),
            Conversation.content.label("content"),
            User.name.label("other"),
            User.id.label("other_id")
        )

    receivers = Conversation.query.\
        join(roi,
             (roi.c.other_id == Conversation.receiver_id) &
             (roi.c.ts == Conversation.ts)).\
        filter(Conversation.sender_id == current_user.id).\
        join(User, User.id == roi.c.other_id).\
        with_entities(
            Conversation.ts.label("timestamp"),
            Conversation.content.label("content"),
            User.name.label("other"),
            User.id.label("other_id")
        )

    return {
        "contacts": list(map(
            lambda x: {
                "other_id": x.other_id,
                "other": x.other,
                "content": x.content,
                "timestamp": format_time(x.timestamp)
            },
            senders.union(receivers).order_by(Conversation.ts).all()
        )),
    }


@app.route("/conversation")
@login_required
def conversation_page():
    return render_template("conversation.html", current=current_user.id)


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

    q = ItemRating.query.filter(ItemRating.item_id == item.id). \
        join(User, User.id == ItemRating.rater_id). \
        outerjoin(ItemUpvote, ItemRating.id == ItemUpvote.rating_id). \
        group_by(ItemRating.id, User.name, ItemRating.item_id, ItemRating.comment, ItemRating.rate, ItemRating.ts). \
        with_entities(
        ItemRating.id.label("rating_id"),
        User.name.label("name"),
        ItemRating.item_id.label("item_id"),
        ItemRating.comment.label("comment"),
        ItemRating.rate.label("rate"),
        ItemRating.ts.label("ts"),
        func.count(ItemUpvote.voter_id).label("num_upvotes"),
        func.max(
            case([(ItemUpvote.voter_id == current_user.id, 1)], else_=0)
        )
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
    for dist in distribution:
        actuals[dist[0]] = dist[1]

    current_review = ItemRating.query.filter(ItemRating.item_id == id, ItemRating.rater_id == current_user.id).all()
    print(ItemRating.query.filter(ItemRating.item_id == id).all())

    return render_template('item_info.html', item=item,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user,
                           user_review=current_review[0] if len(current_review) > 0 else None,
                           has_user_review=len(current_review) > 0,
                           reviewable=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/item_upload', methods=['GET', 'POST'])
@login_required
def item_upload_page():
    form = ItemForm()
    categories = Category.query.order_by('name').all()
    choices = []
    for c in categories:
        choices.append(c.name)
    form.category.choices = choices
    if request.method == 'POST':
        if form.validate_on_submit():
            # store item
            category_id = Category.query.filter_by(name=form.category.data).first().id
            item_to_create = Item(name=form.item_name.data,
                                  description=form.description.data,
                                  creator_id=current_user.id,
                                  category_id=category_id
                                  )
            # update inventory
            current_user.item_inventory.append(Inventory(item=item_to_create,
                                                         price=form.price.data,
                                                         quantity=form.quantity.data
                                                         ))
            # print(item_to_create.id)
            # db.session.add(item_to_create)
            # store images
            uploaded_files = request.files.getlist("images")
            if uploaded_files:
                for file in uploaded_files:
                    if allowed_file(file.filename):
                        picname = str(uuid.uuid1()) + "_" + secure_filename(file.filename)
                        item_to_create.images.append(ItemImage(name=picname))
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], picname))
                    else:
                        flash(f'Item create failed. {file.filename} is not allowed, please try again.',
                              category='danger')
                        return render_template('item_upload.html', form=form)
            db.session.add(item_to_create)
            db.session.commit()
            flash(f'Item create success! Your {item_to_create.name} is on market now.',
                  category='success')
            return redirect(url_for('market_page'))
        if form.errors:
            for err_msg in form.errors.values():
                flash(f'Item create failed. {err_msg}', category='danger')
    return render_template('item_upload.html', form=form)


@app.route('/item_sell/<int:id>', methods=['GET', 'POST'])
@login_required
def item_sell_page(id):
    form = SellForm()
    item = Item.query.get(id)
    if request.method == 'POST':
        if form.validate_on_submit():
            # check user never sell item
            sold_items = current_user.seller_inventory
            for sold_item in sold_items:
                if id == sold_item.id:
                    flash(f'Item sell failed: you sold {item.name} before, please modify on inventory page.',
                          category='danger')
                    return redirect(url_for('item_sell_page', id=id))

            # add item to suer inventory
            item_inventory = current_user.item_inventory
            current_user.item_inventory.append(Inventory(item=item,
                                                      price=form.price.data,
                                                      quantity=form.quantity.data))
            db.session.add(current_user)
            db.session.commit()
            flash(f'Item Sell Success! Your {form.quantity.data} X {item.name} are on market now.',
                  category='success')
            return redirect(url_for('market_page'))
        if form.errors:
            for err_msg in form.errors.values():
                flash(f'Item sell failed. {err_msg}', category='danger')
    return render_template('item_sell.html', form=form, item=item)


@app.route('/inventory')
@login_required
def inventory_page():
    return render_template('inventory.html')


@app.route('/sell_history')
@login_required
def sell_history_page():
    return render_template('sell_history.html')


@app.route('/buy_history')
@login_required
def buy_history_page():
    return render_template('buy_history.html')


@app.route('/cart')
@login_required
def cart_page():
    return render_template('cart.html')


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404

@app.route('/public_profile/<int:id>')
@login_required
def public_profile__page(id):
    user = User.query.get_or_404(id)
    return render_template('public_profile.html', user=user)

