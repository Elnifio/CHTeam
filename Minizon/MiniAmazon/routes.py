from MiniAmazon import app, db, ALLOWED_EXTENSIONS, bcrypt
from flask import render_template, redirect, url_for, flash, request
from MiniAmazon.models import Item, User, Category, ItemImage, Inventory, ItemRating, ItemUpvote, Conversation, \
    SellerRating, SellerUpvote, Order, Order_item, Cart, Order, Order_item, Favorites, Balance_change
from MiniAmazon.forms import RegisterForm, LoginForm, ItemForm, MarketForm, SellForm, AddToCartForm, EditCartForm, ItemEditForm, \
    SellForm, EditUserForm, InventoryForm, InventoryEditForm, SellHistoryForm, BuyHistoryForm, BalanceHistoryForm
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from sqlalchemy import func, case, desc, asc
import json
import uuid as uuid
import os
from decimal import *


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
    return f"{t.month}/{t.day}/{t.year} {t.hour}:{t.minute}"

# ----------------
# ABSTRACTION FUNCTIONS OVER INTERFACE Rating & Upvote
# ----------------
def make_rating_query(rating, upvote, rated_oi, rater_oi):
    q = rating.query.filter(rating.rated_id == rated_oi). \
        join(User, User.id == rating.rater_id). \
        outerjoin(upvote, rating.id == upvote.rating_id). \
        group_by(
            rating.id, User.name, rating.rated_id,
            rating.comment, rating.rate, rating.ts). \
        with_entities(
            rating.id.label("rating_id"),
            User.name.label("name"),
            rating.rated_id.label("rated_id"),
            rating.comment.label("comment"),
            rating.rate.label("rate"),
            rating.ts.label("ts"),
            func.count(upvote.voter_id).label("num_upvotes"),
            func.max(
                case([(upvote.voter_id == rater_oi, 1)], else_=0)
            ).label("is_voted")
        )

    return q


def make_rating_average_distribution(rating, rated_oi):
    return rating.query.\
                with_entities(func.avg(rating.rate).label("average")).\
                filter(rating.rated_id == rated_oi).all()[0][0]


def make_rating_distribution(rating, rated_oi):
    result = rating.query.filter(rating.rated_id == rated_oi).\
                with_entities(rating.rate, func.count(rating.rater_id).label("cnt")).\
                group_by(rating.rate).all()

    actuals = {x: 0 for x in range(6)}
    for dist in result:
        actuals[dist[0]] = dist[1]

    return actuals


def execute_delete(rating, rated_oi, rater_oi):
    q = rating.query.\
        filter(rating.rated_id == rated_oi, rating.rater_id == rater_oi).\
        delete()
    return q


def get_current_review(rating, rated_oi, rater_oi):
    return rating.query.filter(rating.rated_id == rated_oi, rating.rater_id == rater_oi).all()


def find_is_voted(upvote, rating, voter):
    return upvote.query.filter(upvote.rating_id == rating, upvote.voter_id == voter)


def query_upvotes(upvote, rating, voter):
    return upvote.query.filter(upvote.rating_id == rating).\
            group_by(upvote.rating_id).\
            with_entities(
                func.count(upvote.voter_id).label("num_upvotes"),
                func.max(
                    case([(upvote.voter_id == voter, 1)], else_=0)
                ).label("is_voted")
            ).all()


def abstract_info(rating, upvote, rated, rater):
    average = make_rating_average_distribution(rating, rated)

    ratings = make_rating_query(rating, upvote, rated, rater).all()

    actuals = make_rating_distribution(rating, rated)

    current_review = get_current_review(rating, rated, rater)

    return average, ratings, actuals, current_review


def abstract_upvote(req, user, table):
    assert req.method == "POST"

    argument = json.loads(req.data.decode("utf-8"))
    assert "user" in argument and "rating" in argument, "Illegal Data provided"

    voter_id = argument['user']
    assert voter_id == user, "Illegal user detected"

    rating_id = argument['rating']
    query = find_is_voted(table, rating_id, voter_id)
    is_voted = len(query.all())

    if is_voted != 0:
        result = query.delete()
        assert result != 0, "Number of Item Upvotes in database is inconsistent with is_voted"
        db.session.commit()
    else:
        upvote = table(rating_id=rating_id, voter_id=voter_id)
        db.session.add(upvote)
        db.session.commit()

    q = query_upvotes(table, rating_id, current_user.id)

    if len(q) == 0:
        return {'upvotes': 0, 'voted': False}

    assert len(q) == 1, f"Item Upvote aggregation did not match operation: {str(q)}"
    return {'upvotes': q[0].num_upvotes, 'voted': q[0].is_voted == 1}


def abstract_edit_review(req, user, rating):
    assert req.method == "POST"

    argument = json.loads(req.data.decode("utf-8"))
    for item in ['user', "item", 'rate', 'comment']:
        assert item in argument, item + " not in argument: " + str(argument)

    assert argument['user'] == user, "Provided user is not current user"

    q = get_current_review(rating, argument['item'], argument['user'])

    if len(q) == 0:
        new_rate = rating(rated_id=argument['item'], rater_id=argument['user'],
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


def abstract_delete_review(req, user, rating):
    assert req.method == "POST"

    argument = json.loads(req.data.decode("utf-8"))
    for item in ['user', "item"]:
        assert item in argument, item + " not in argument: " + str(argument)

    assert argument['user'] == user, "Provided user is not current user"

    q = execute_delete(rating, argument['item'], argument['user'])
    assert q != 0, "0 rating deleted"

    db.session.commit()
    return {"success": True}


control_message = {
    "initiated": "INITIATED",
    "image_header": "image://"
}


@app.route('/')
@app.route('/home')
@login_required
def home_page():
    return render_template('home.html')


order_swicthes = {
    'Price': Item.price,
    'Name': Item.name,
    'Rating': Item.rating,
    'Quantity': Item.quantity
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
                items = query.order_by(order_swicthes.get(form.sort_by.data).asc()).all()
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
                                password_plain=form.password1.data,
                                balance=form.balance.data
                                )
        if User.query.filter_by(email=form.email.data).first():
            flash(f'Login Failed: email already exists.', category='danger')
            return redirect(url_for('register_page'))
        db.session.add(user_to_register)
        db.session.commit()

        login_user(user_to_register)
        flash(f'Login Success! Welcome, {user_to_register.name}!', category='success')
        return redirect(url_for('home_page'))
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
            return redirect(url_for('home_page'))
        else:
            if User.query.filter_by(email=form.email.data).first() is None:
                flash('Email not exists, please register first.', category='danger')
            else:
                flash('Email and password not match. Please try again.', category='danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout_page():
    logout_user()
    flash(f'Logout Success!', category='success')
    return render_template('home.html')


# --------------------------------
#
# CONVERSATION MODULE
#
# --------------------------------
@app.route("/start_message/<int:id>")
@login_required
def start_message(id):
    sender = current_user.id
    receiver = id
    print(f"Sender id: {sender}, Receiver ID: {receiver}")

    q = Conversation.query.filter(
        ((Conversation.sender_id == sender) & (Conversation.receiver_id == receiver)) |
        ((Conversation.sender_id == receiver) & (Conversation.receiver_id == sender))
    ).order_by(Conversation.ts).all()

    if len(q) == 0:
        msg = Conversation(sender_id=sender, receiver_id=receiver, content=control_message['initiated'], priority=1)
        db.session.add(msg)
        db.session.commit()
    else:
        msg = q[-1]
        print(q)
        msg.priority = 1
        db.session.commit()
    return redirect(url_for("conversation_page"))


@app.route("/receive_message", methods=['POST'])
@login_required
def receive_message():
    assert request.method == "POST", "Request Method invalid"
    argument = json.loads(request.data.decode("utf-8"))
    if not ("other" in argument and "content" in argument):
        return {"status": False}
    other = argument['other']
    content = argument['content']
    message = Conversation(sender_id=current_user.id,
                           receiver_id=other,
                           content=content)
    db.session.add(message)
    db.session.commit()
    return {"status": True, "timestamp": format_time(message.ts)}


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
        (((Conversation.sender_id == current_user.id) & (Conversation.receiver_id == other)) |
        ((Conversation.receiver_id == current_user.id) & (Conversation.sender_id == other))))
    q = q.order_by(Conversation.ts)

    to_be_updated = q.filter(Conversation.priority == 1)
    mapping = []
    for updated in to_be_updated.all():
        mapping.append({"id": updated.id, "priority": 0})
    print(mapping)
    db.session.bulk_update_mappings(Conversation, mapping)
    db.session.commit()

    q = q.filter((Conversation.content != control_message['initiated']))

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
            User.id.label("other_id"),
            Conversation.priority.label("priority")
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
            User.id.label("other_id"),
            Conversation.priority.label("priority")
        )

    return {
        "contacts": list(map(
            lambda x: {
                "other_id": x.other_id,
                "other": x.other,
                "content": "" if x.content == control_message['initiated'] else x.content,
                "timestamp": format_time(x.timestamp),
                "priority": x.priority
            },
            senders.union(receivers).order_by(desc(Conversation.priority), desc(Conversation.ts)).all()
        )),
    }


@app.route("/conversation")
@login_required
def conversation_page():
    return render_template("conversation.html", current=current_user.id)


# --------------------------------
#
# ITEM MODULE
#
# --------------------------------
@app.route('/item_info/<int:id>')
@login_required
def item_info_page(id):
    item = Item.query.get_or_404(id)

    user_inventory = item.user_inventory.all()


    # TODO: Find if an item is reviewable
    # commentable = Order.query.filter(Order.buyer_id == current_user.id).\
    #     join(Order_item, Order_item.order_id == Order.id).\
    #     filter(Order_item.item_id == id).all()
    # commentable = len(commentable) > 0
    commentable = True

    average, ratings, actuals, current_review = abstract_info(ItemRating, ItemUpvote, id, current_user.id)


    return render_template('item_info.html', item=item,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user,
                           user_review=current_review[0] if len(current_review) > 0 else None,
                           has_user_review=len(current_review) > 0,
                           reviewable=commentable,
                           user_inventory=user_inventory)


@app.route("/item_upvote", methods=['POST'])
@login_required
def item_upvote():
    return abstract_upvote(request, current_user.id, ItemUpvote)


@app.route("/item_review", methods=['POST'])
@login_required
def receive_item_review():
    return abstract_edit_review(request, current_user.id, ItemRating)


@app.route("/delete_item_review", methods=["POST"])
@login_required
def delete_item_review():
    return abstract_delete_review(request, current_user.id, ItemRating)


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


@app.route('/item_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def item_edit_page(id):
    item = Item.query.get_or_404(id)
    form = ItemEditForm()
    categories = Category.query.order_by('name').all()
    choices = []
    # set catgory choices and select current category by default

    for c in categories:
        choices.append((c.id, c.name))
    form.category.choices = choices
    if item.creator_id != current_user.id:
        flash(f'Sorry, you cannot edit this product since you are not the creator of {item.name}.', category='danger')
        return redirect(url_for('item_info_page', id=id))
    if request.method == 'POST':
        print(form.item_name.data)
        item.name = form.item_name.data
        item.description = form.description.data
        item.category_id = form.category.data
        uploaded_files = request.files.getlist("images")

        if uploaded_files[0].filename:
            for file in uploaded_files:
                if allowed_file(file.filename):
                    picname = str(uuid.uuid1()) + "_" + secure_filename(file.filename)
                    item.images.append(ItemImage(name=picname))
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], picname))
                else:
                    flash(f'Item Edit failed. {file.filename} is not allowed, please try again.',
                          category='danger')
                    return redirect(url_for('item_edit_page', id=id))
        db.session.add(item)
        db.session.commit()
        flash(f'Item edit succeed.', category='success')
    form.category.default = item.category_id
    form.item_name.default = item.name
    form.description.default = item.description
    form.process()
    return render_template('item_edit.html', item=item, form=form)


@app.route('/remove_image/<int:image_id>')
@login_required
def remove_image(image_id):
    image = ItemImage.query.get_or_404(image_id)
    item_images = Item.query.get_or_404(image.item_id).images
    item_id = image.item_id
    if image is None:
        flash(f'Image not exists.')
    elif len(item_images) <= 1:
        flash(f'Item must have at least one image.', category='danger')
    else:
        db.session.delete(image)
        db.session.commit()
        flash(f'Image remove succeed.', category='success')
    return redirect(url_for('item_edit_page', id=item_id))


@app.route('/cart_add/<int:item_id>/<int:user_id>', methods=['GET', 'POST'])
@login_required
def cart_add_page(item_id, user_id):
    form = AddToCartForm()
    inv = Inventory.query.filter_by(item_id=item_id, seller_id=user_id).first()
    if request.method == 'POST':
        if form.validate_on_submit():
            item = Item.query.get_or_404(item_id)
            # check if this item is in current user's inventory
            current_inventory = current_user.item_inventory.filter_by(item_id=item_id, seller_id=user_id).first()
            if current_inventory:
                flash(f'Add to cart failed. {item.name} is in your inventory.', category='danger')
                return redirect(url_for('cart_add_page', item_id=item_id, user_id=user_id))
            # check if the item from the same seller is in current user's cart and favorites
            current_cart = current_user.item_cart.filter_by(item_id=item_id, seller_id=user_id).first()
            current_favorite = current_user.item_favorites.filter_by(item_id=item_id, seller_id=user_id).first()
            if current_cart or current_favorite:
                flash(f'Add to cart failed. {item.name} already exists in your cart or category.', category='danger')
                return redirect(url_for('cart_add_page', item_id=item_id, user_id=user_id))
            current_user.item_cart.append(Cart(
                    item=item,
                    seller_id=inv.seller_id,
                    quantity=form.quantity.data,
                    price=inv.price
                ))
            db.session.add(current_user)
            db.session.commit()
            flash(f'Add to cart success. {form.quantity.data} X {item.name} added to your cart.', category='success')
            return redirect(url_for('item_info_page', id=item_id))
    return render_template('cart_add.html', form=form, price=inv.price, name=inv.item.name)


@app.route('/inventory',methods=['GET', 'POST'])
@login_required
def inventory_page():
    inventory = None
    query = None
    form = InventoryForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # process search
            search = form.search.data
            query = Inventory.query.filter(Inventory.seller_id==current_user.id)
            if search != '':
                query = query.filter(
                    Inventory.item.name.ilike(f'%{search}%')
                ).first().inventory
            # process sort and order
            inventory = query.all()
            
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')

    return render_template('inventory.html', inventory=inventory, form=form)

@app.route('/inventory_edit/<int:id>', methods=['GET', 'POST'])
@login_required
def inventory_edit_page(id):
    form = InventoryEditForm()
    item = Item.query.get(id)
    if request.method == 'POST':
        if form.validate_on_submit():
            # check user never sell item
            record = Inventory.query.filter(Inventory.seller_id==current_user.id and Inventory.item_id == item.id).first()
            if form.quantity.data == 0:
                db.session.delete(record)
                db.session.commit()
                flash(f'Item Remove Success! Your {item.name} are removed now.',
                  category='success')
            else:
                record.quantity = form.quantity.data
                record.price = form.price.data
                db.session.add(record)
                db.session.commit()
                flash(f'Inventory Edit Success! Your quantity of {item.name} are edit as {form.quantity.data} now.',
                  category='success')

            return redirect(url_for('inventory_page'))
        if form.errors:
            for err_msg in form.errors.values():
                flash(f'Item sell failed. {err_msg}', category='danger')
    return render_template('inventory_edit.html', form=form, item=item)
    
@app.route('/sell_history',methods=['GET', 'POST'])
@login_required
def sell_history_page():
    sell_order = None
    query = None
    form = SellHistoryForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            # process search
            query = Order_item.query.filter(Order_item.seller_id==current_user.id)
            # process sort and order
            if form.order_by.data == 'Desc':
                if form.sort_by.data == 'Date':
                    sell_order = query.join(Order, Order_item.order_id==Order.id).order_by(desc(Order.Date)).all()
                else:
                    sell_order = query.order_by(desc(Order_item.price)).all()
            else:
                if form.sort_by.data == 'Date':
                    sell_order = query.join(Order, Order_item.order_id==Order.id).order_by(asc(Order.Date)).all()
                else:
                    sell_order = query.order_by(asc(Order_item.price)).all()
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')

    return render_template('sell_history.html', sell_order=sell_order, form=form)


@app.route('/fulfill/<int:order_id>/<int:item_id>',methods=['GET', 'POST'])
@login_required
def fulfill(order_id,item_id):
    record = Order_item.query.filter(Order_item.seller_id==current_user.id and Order_item.item_id == item_id and Order_item.order_id == order_id).first()
    if record.fulfill == "Fulfilled":
        flash(f'Order fulfill failed: you order item has already been fulfilled.',category='danger')
    else:
        record.fulfill = "Fulfilled"
        flash(f'Fulfill Successfuly',category='success')
        db.session.add(record)
        db.session.commit()
    order_fulfill = Order.query.filter(Order.id == order_id).first()
    order_fulfill.status = "All fulfilled"
    order_check = Order_item.query.filter(Order_item.order_id == order_id).all()
    for each_order in order_check:
        if each_order.fulfill != "Fulfilled":
            order_fulfill.status = "Not fulfilled yet"
    db.session.add(order_fulfill)
    db.session.commit()
    return redirect(url_for('sell_history_page'))
    
@app.route('/buy_history',methods=['GET', 'POST'])
@login_required
def buy_history_page():
    buy_order = None
    query = None
    form = BuyHistoryForm()

    if request.method == 'POST':
        if form.validate_on_submit():
            # process search
            query = Order.query.filter(Order.buyer_id == current_user.id)
            if form.sort_by.data == 'Desc':
                if form.search_by.data == 'All':
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).order_by(desc(Order.Date)).all()
                elif form.search_by.data == 'Item':
                    search = form.search.data
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).join(Item, Item.id==Order_item.item_id).filter(db.or_(
                    Item.name.ilike(f'%{search}%'),
                    Item.description.ilike(f'%{search}%')
                    )).order_by(desc(Order.Date)).all()
                elif form.search_by.data == 'Seller':
                    search = form.search.data
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).join(User, User.id==Order_item.seller_id).filter(db.or_(
                    User.name.ilike(f'%{search}%'))
                    ).order_by(desc(Order.Date)).all()
            else:
                if form.search_by.data == 'All':
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).order_by(asc(Order.Date)).all()
                elif form.search_by.data == 'Item':
                    search = form.search.data
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).join(Item, Item.id==Order_item.item_id).filter(db.or_(
                    Item.name.ilike(f'%{search}%'),
                    Item.description.ilike(f'%{search}%')
                    )).order_by(asc(Order.Date)).all()
                elif form.search_by.data == 'Seller':
                    search = form.search.data
                    buy_order = query.join(Order_item, Order_item.order_id == Order.id).join(User, User.id==Order_item.seller_id).filter(db.or_(
                    User.name.ilike(f'%{search}%'))
                    ).order_by(asc(Order.Date)).all()
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')

    return render_template('buy_history.html', buy_order = buy_order, form = form)

@app.route('/order_detail/<int:id>')
@login_required
def order_detail_page(id):
    order = Order.query.filter(Order.id ==id).first()
    order_detail = Order_item.query.filter(Order_item.order_id==id).all()
    return render_template('order_detail.html', order = order, order_detail = order_detail)


@app.route('/cart')
@login_required
def cart_page():
    item_cart = current_user.item_cart.order_by(Cart.ts).all()
    total = current_user.item_cart.with_entities(
        db.func.sum(Cart.price * Cart.quantity)
    ).first()[0]
    total = 0.0 if total is None else total
    favorites = current_user.item_favorites.order_by(Favorites.ts).all()
    return render_template('cart.html', item_cart=item_cart, total=total, favorites=favorites)


@app.route('/remove_cart/<int:item_id>/<int:seller_id>')
@login_required
def remove_cart(item_id, seller_id):
    item_cart = Cart.query.filter_by(item_id=item_id, seller_id=seller_id, buyer_id=current_user.id).first()
    # print(item_cart)
    if item_cart:
        db.session.delete(item_cart)
        flash(f'Remove from cart succeed. {item_cart.item.name} is removed from your cart.', category='success')
        db.session.commit()
        # flash(f'Remove from cart Success. {item_cart.item.name} is removed from your cart.', category='success')
    else:
        flash(f'Remove from cart failed. You cannot remove this product from your cart', category='danger')
    return redirect(url_for('cart_page'))


@app.route('/cart_edit/<int:item_id>/<int:seller_id>', methods=['GET', 'POST'])
@login_required
def cart_edit_page(item_id, seller_id):
    form = EditCartForm()
    item_cart = Cart.query.filter_by(item_id=item_id, seller_id=seller_id, buyer_id=current_user.id).first()
    if request.method == 'POST':
        if form.validate_on_submit():
            if item_cart is None:
                flash(f'Cart edit failed. You cannot edit this item.', category='danger')
                return redirect(url_for('cart_page'))
            item_cart.quantity = form.quantity.data
            db.session.add(item_cart)
            db.session.commit()
            flash(f'Cart Edit success. You have {item_cart.quantity} X {item_cart.item.name} in your cart now.',
                  category='success')
            return redirect(url_for('cart_page'))
        if form.errors:
            for err_msg in form.errors.values():
                flash(f'Cart edit failed. {err_msg}', category='danger')
    return render_template('cart_edit.html', item_cart=item_cart, form=form)


@app.route('/favorites_add/<int:item_id>/<int:seller_id>', methods=['GET', 'POST'])
@login_required
def favorites_add(item_id, seller_id):
    # check if item from seller is in current_user's cart
    current_cart = current_user.item_cart.filter_by(item_id=item_id, seller_id=seller_id).first()
    if not current_cart:
        flash(f'Add to favorites failed. Item does not exist in your cart.', category='danger')
    else:
        item_name = current_cart.item.name
        quantity = current_cart.quantity
        current_user.item_favorites.append(Favorites(item_id=item_id,
                                                     seller_id=seller_id,
                                                     quantity=quantity,
                                                     price=current_cart.price))
        db.session.delete(current_cart)
        db.session.add(current_user)
        db.session.commit()
        flash(f'Add to favorites succeed! {quantity} X {item_name} added to your favorites.', category='success')
    return redirect(url_for('cart_page'))


@app.route('/favorites_move/<int:item_id>/<int:seller_id>', methods=['GET', 'POST'])
@login_required
def favorites_move(item_id, seller_id):
    current_favorite = current_user.item_favorites.filter_by(item_id=item_id, seller_id=seller_id).first()
    if not current_favorite:
        flash(f'Move to cart failed. Item does not exist in your favorites.', category='danger')
    else:
        item_name = current_favorite.item.name
        quantity = current_favorite.quantity
        current_user.item_cart.append(Cart( item_id=item_id,
                                            seller_id=seller_id,
                                            quantity=quantity,
                                            price=current_favorite.price))
        db.session.delete(current_favorite)
        db.session.add(current_user)
        db.session.commit()
        flash(f'Move to cart succeed! {quantity} X {item_name} added to your cart.', category='success')
    return redirect(url_for('cart_page'))

@app.route('/checkout')
@login_required
def checkout():
    if current_user.item_cart.count() == 0:
        flash(f'Checkout failed. No items found in your cart.', category='danger')
    else:
        total = current_user.item_cart.with_entities(
            db.func.sum(Cart.price * Cart.quantity)
        ).first()[0]
        if current_user.balance < total:
            flash(f'Checkout failed. You don\' have enough balance in your account.', category='danger')
            return redirect(url_for('cart_page'))

        order = Order(address=current_user.address, total_price=total, status="NA", buyer_id=current_user.id)
        db.session.add(order)
        items_cart = current_user.item_cart.all()
        invs = []
        for item_cart in items_cart:
            # check seller has enough stock
            inv = item_cart.seller.\
                item_inventory.filter_by(item_id=item_cart.item_id).first()
            if inv.quantity < item_cart.quantity:
                flash(f'Checkout failed. Seller {item_cart.seller.name} doesn\'t have'
                      f'{item_cart.quantity} X {item_cart.item.name} in inventory.', category='danger')
                return redirect(url_for('cart_page'))
            inv.quantity = inv.quantity - item_cart.quantity
            invs.append(inv)
        for i in range(len(invs)):
            inv = invs[i]
            cart = items_cart[i]
            order.order_items.append(Order_item(item_id=cart.item_id,
                                                seller_id=cart.seller_id,
                                                quantity=cart.quantity,
                                                price=cart.price,
                                                fulfill="NA"))
            db.session.add(inv)
            db.session.delete(cart)
        current_user.balance = current_user.balance - total
        db.session.add(order)
        db.session.add(current_user)
        db.session.commit()
        flash(f'Checkout succeed!', category='success')

    return redirect(url_for('cart_page'))


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


# --------------------------------
#
# USER MODULE
#
# --------------------------------
@app.route('/public_profile/<int:id>')
@login_required
def public_profile_page(id):
    user = User.query.get_or_404(id)

    # TODO: Find if the user can comment the seller
    # commentable = Order.query.filter(Order.buyer_id == current_user.id).\
    #     join(Order_item, Order_item.order_id == Order.id).\
    #     filter(Order_item.seller_id == id).all()
    # commentable = len(commentable) > 0
    commentable = True

    average, ratings, actuals, current_review = abstract_info(SellerRating, SellerUpvote, id, current_user.id)

    return render_template('public_profile.html', user=user,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user,
                           user_review=current_review[0] if len(current_review) > 0 else None,
                           has_user_review=len(current_review) > 0,
                           reviewable=commentable,
                            )

@app.route('/edit_info', methods=['GET', 'POST'])
@login_required
def edit_user_page():
    user = User.query.get_or_404(current_user.id)
    form = EditUserForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # process 
            if form.email.data != user.email and User.query.filter_by(email=form.email.data).first():
                flash(f'Login Failed: email already exists.', category='danger')
                return redirect(url_for('edit_user_page'))
            user.name = form.username.data
            user.email = form.email.data
            user.address = form.address.data
            # user.password = form.password1.data
            user.password_plain = form.password1.data
            if form.balance_change.data + Decimal(user.balance) < 0:
                user.balance = 0
            else:
                user.balance = form.balance_change.data + Decimal(user.balance)
            db.session.commit()
            flash(f'User edit succeed.', category='success')
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')
    form.username.default = user.name
    form.email.default = user.email
    form.address.default = user.address
    form.balance_change.default = 0.0
    form.process()
    return render_template('edit_info.html', user=user, form = form)

    # TODO: Find if the user can comment the seller
    # commentable = Order.query.filter(Order.buyer_id == current_user.id).\
    #     join(Order_item, Order_item.order_id == Order.id).\
    #     filter(Order_item.seller_id == id).all()
    # commentable = len(commentable) > 0
    commentable = True

    average, ratings, actuals, current_review = abstract_info(SellerRating, SellerUpvote, id, current_user.id)

    return render_template('public_profile.html', user=user,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user,
                           user_review=current_review[0] if len(current_review) > 0 else None,
                           has_user_review=len(current_review) > 0,
                           reviewable=commentable)


@app.route("/seller_upvote", methods=['POST'])
@login_required
def seller_upvote():
    return abstract_upvote(request, current_user.id, SellerUpvote)


@app.route("/seller_review", methods=['POST'])
@login_required
def receive_seller_review():
    return abstract_edit_review(request, current_user.id, SellerRating)


@app.route("/delete_seller_review", methods=["POST"])
@login_required
def delete_seller_review():
    return abstract_delete_review(request, current_user.id, SellerRating)

@app.route('/balance_history',methods=['GET', 'POST'])
@login_required
def balance_history_page():
    balance_history = None
    query = None
    form = BalanceHistoryForm()
    balance_history = Balance_change.query.filter(Balance_change.user_id == current_user.id).all()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.order_by.data == 'Desc':
                balance_history = Balance_change.query.filter(Balance_change.user_id == current_user.id).order_by(desc(Balance_change.ts)).all()
            else:
                balance_history = Balance_change.query.filter(Balance_change.user_id == current_user.id).order_by(asc(Balance_change.ts)).all()
        if form.errors != {}:
            for err_msg in form.errors.values():
                flash(f'Error: {err_msg}', category='danger')

    return render_template('balance_history.html', balance_history = balance_history, form = form)