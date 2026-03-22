from app import create_app, db
import os

application = create_app()
app = application

with application.app_context():
    db.create_all()

if _name_ == '_main_':
    application.run(debug=False)