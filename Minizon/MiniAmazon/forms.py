from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, MultipleFileField
from wtforms import SelectField, TextAreaField, IntegerField, DecimalField
from wtforms.validators import Length, Email, EqualTo, DataRequired, NumberRange, Regexp
from MiniAmazon.models import Category

letter_constraint = ' must contain only letters, numbers, underscore'
regex = '^[a-zA-Z0-9_]*$'
# including space
regex2 = '^[a-zA-Z0-9_\s]*$'


class RegisterForm(FlaskForm):
    username = StringField(label='User Name:', validators=
    [Length(min=2, max=50), DataRequired(), Regexp(regex=regex, message="Username"+letter_constraint)])
    email = StringField(label='Email Address:', validators=[Email(), DataRequired()])
    address = StringField(label='Delivery Address:', validators=[Length(max=100), DataRequired(),
                                                    Regexp(regex, message="Address"+letter_constraint)])
    password1 = PasswordField(label='Password:', validators=[Length(min=6, max=60), DataRequired(),
                                                    Regexp(regex, message="Password"+letter_constraint)])
    password2 = PasswordField(label='Confirm Password:', validators=[EqualTo('password1'), DataRequired()])
    submit = SubmitField(label='Create Account')


class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', validators=[DataRequired(),
                                                           Regexp(regex, message="Password"+letter_constraint)])
    submit = SubmitField(label='Login')


class ItemForm(FlaskForm):
    item_name = StringField(label='Name', validators=[DataRequired(),
                                                      Regexp(regex2, message="Item name"+letter_constraint+", space")])
    images = MultipleFileField(label='Images', validators=[DataRequired()])
    category = SelectField(label='Category')
    description = TextAreaField(label="Description",validators=[DataRequired(), Regexp(regex2, message="Description"+letter_constraint+", space")])
    price = DecimalField(places=2, label="Price", validators=[NumberRange(min=0.0)])
    quantity = IntegerField(label="Quantity", validators=[NumberRange(min=1)])
    submit = SubmitField(label='Create Item')


class MarketForm(FlaskForm):
    category = SelectField(label='Category')
    sort_by = SelectField(label='Sort By', choices=['Price', 'Name', 'Rating'])
    search = StringField(label='Keyword', validators=[DataRequired(),
                                                      Regexp(regex, message="Keyword"+letter_constraint)])
    order_by = SelectField(label='Order By', choices=['Asc', 'Desc'])
    submit = SubmitField(label='Submit')


class SellForm(FlaskForm):
    price = DecimalField(places=2, label='Price', validators=[NumberRange(min=0.0)])
    quantity = IntegerField(label='Quantity', validators=[NumberRange(min=1)])
    submit = SubmitField(label='Sell')
    