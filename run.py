from app import create_app, db
import os

application = create_app()
app = application

with application.app_context():
    db.create_all()
    print("Database tables created!")

if __name__ == '__main__':
    application.run(debug=False)