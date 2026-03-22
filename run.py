from app import create_app, db
import os

application = create_app()
app = application

with application.app_context():
    db.create_all()

if __name__ == '__main__':
    application.run(debug=False)