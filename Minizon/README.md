# Minizon
## How to run
On Mac:
Our application assume you have postgresql on your machine and user postgres does not have password by default.
You can modify line 21 of MiniAmazon/\_\_init__.py to specify data base. 
```code
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri_local
```
To create all relationships, execute the following code.
```bash
cd CHTeam/Minizon
python3
from MiniAmazon import db
db.create_all()
exit()
```
Next, run the following commands to start application and it is running on *http://127.0.0.1:5000/*
```bash
pip install requirements.txt
export FLASK_APP = app.py
flask run
```

## Files

- **models.py**: matched classes of tables
- **routes.py**: routings between pages
- **templates**: webpages (*all pages should inherit from base page*)
- **app.py**: starting point 
