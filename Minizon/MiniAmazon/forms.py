from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import Length, Email, EqualTo, DataRequired


class RegisterForm(FlaskForm):
    username = StringField(label='User Name:', validators=[Length(min=2, max=50), DataRequired()])
    email = StringField(label='Email Address:', validators=[Email(), DataRequired()])
    address = StringField(label='Delivery Address:', validators=[Length(max=100)])
    password1 = PasswordField(label='Password:', validators=[Length(min=6, max=60), DataRequired()])
    password2 = PasswordField(label='Confirm Password:', validators=[EqualTo('password1'), DataRequired()])
    submit = SubmitField(label='Create Account')


class LoginForm(FlaskForm):
    email = StringField(label='Email Address', validators=[DataRequired()])
    password = PasswordField(label='Password', validators=[DataRequired()])
    submit = SubmitField(label='Login')
