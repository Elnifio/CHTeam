from MiniAmazon import app, db, ALLOWED_EXTENSIONS
from flask import render_template, redirect, url_for, flash, request
from MiniAmazon.models import Item, User, Category, ItemImage, Inventory
from MiniAmazon.forms import RegisterForm, LoginForm, ItemForm, MarketForm, SellForm
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import uuid as uuid
import os
from sqlalchemy import desc


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


@app.route('/item_info/<int:id>')
@login_required
def item_info_page(id):
    item = Item.query.get_or_404(id)
    return render_template('item_info.html', item=item)


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