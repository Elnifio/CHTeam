from MiniAmazon import app, db, ALLOWED_EXTENSIONS
from flask import render_template, redirect, url_for, flash, request
from MiniAmazon.models import Item, User, Category, ItemImage, Inventory, ItemRating, ItemUpvote, Cart, Order, \
    Order_item
from MiniAmazon.forms import RegisterForm, LoginForm, ItemForm, MarketForm, SellForm, AddToCartForm, EditCartForm, \
    ItemEditForm
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


@app.route("/item_upvote", methods=['POST'])
@login_required
def item_upvote():
    if not request.method == "POST":
        flash(f'Error: Invalid Request Method {request.method}', category='danger')

    assert request.method == "POST"

    argument = json.loads(request.data.decode("utf-8"))
    if not "user" in argument and "rating" in argument:
        flash(f'Error: Invalid request data format', category='danger')
    assert "user" in argument and "rating" in argument, "Illegal Data provided"

    voter_id = argument['user']
    if not voter_id ==  current_user.id:
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

    q = ItemRating.query.filter(ItemRating.item_id == argument['item'], ItemRating.rater_id == argument['user']).delete()
    if q == 0:
        flash(f"Error: 0 Rating deleted")
    assert q != 0, "0 rating deleted"

    db.session.commit();
    return {"success": True}


@app.route('/item_info/<int:id>')
@login_required
def item_info_page(id):
    item = Item.query.get_or_404(id)
    user_inventory = item.user_inventory.filter(Inventory.quantity>0).all()
    # print(type(user_inventory))
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
    # print(ItemRating.query.filter(ItemRating.item_id == id).all())

    return render_template('item_info.html', item=item,
                           reviews=ratings,
                           average=round(average, 1) if average is not None else average,
                           distribution=actuals, num_reviews=len(ratings),
                           boolean_mask=to_boolean_mask,
                           current=current_user,
                           user_review=current_review[0] if len(current_review) > 0 else None,
                           has_user_review=len(current_review) > 0,
                           reviewable=True,
                           user_inventory=user_inventory)


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
            for i in current_user.item_inventory:
                if i.item_id == item_id and i.seller_id == current_user.id:
                    flash(f'Add to cart failed. {item.name} is already in your inventory.', category='danger')
                    return redirect(url_for('cart_add_page', item_id=item_id, user_id=user_id))
            # check if the item from the same seller is in current user's cart
            items_cart = current_user.item_cart.all()
            for i in items_cart:
                if i.item_id == item_id and i.seller_id == user_id:
                    flash(f'Add to cart failed. {item.name} from {inv.seller.name} is already in your cart',
                          category='danger')
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
    item_cart = current_user.item_cart.order_by(Cart.ts).all()
    total = current_user.item_cart.with_entities(
        db.func.sum(Cart.price * Cart.quantity)
    ).first()[0]
    return render_template('cart.html', item_cart=item_cart, total=total)


@app.route('/remove_cart/<int:item_id>/<int:seller_id>')
@login_required
def remove_cart(item_id, seller_id):
    item_cart = Cart.query.filter_by(item_id=item_id, seller_id=seller_id, buyer_id=current_user.id).first()
    # print(item_cart)
    if item_cart:
        db.session.delete(item_cart)
        flash(f'Remove from cart Success. {item_cart.item.name} is removed from your cart.', category='success')
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
        if form.errors:
            for err_msg in form.errors.values():
                flash(f'Cart edit failed. {err_msg}', category='danger')
    return render_template('cart_edit.html', item_cart=item_cart, form=form)


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
        flash(f'Chekout success!', category='success')

    return redirect(url_for('cart_page'))


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html'), 404


@app.route('/public_profile/<int:id>')
@login_required
def public_profile_page(id):
    user = User.query.get_or_404(id)
    return render_template('public_profile.html', user=user)

