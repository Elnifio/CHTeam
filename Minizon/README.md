# Minizon
## How to run
On Mac:
```bash
cd CHTeam/Minizon
pip install requirements.txt
export FLASK_APP = app.py
flask run
```
## Project Structure
```bash
Minizon
├── MiniAmazon
│   ├── __init__.py
│   ├── __pycache__
│   ├── models.py
│   ├── routes.py
│   └── templates
├── __pycache__
│   └── app.cpython-37.pyc
├── app.py
├── requirements.txt
├── static
└── venv
    ├── bin
    ├── include
    ├── lib
    └── pyvenv.cfg

```
- **models.py**: matched classes of tables
- **routes.py**: routings between pages
- **templates**: webpages (*all pages should inherit from base page*)
- **app.py**: starting point 
- **requirements.txt**: installed packages
## Git Flow
Branches:
- main: version release
- dev: development use (merge into this after compeleting a feature) 
## Database Connection
use remote connection by default
- server: 34.207.91.24
- user: postgres
- databaase: postgres
- password: password
## Er Diagram
![alt text](er.png)
