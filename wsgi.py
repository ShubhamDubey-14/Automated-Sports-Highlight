from app import app, db

# Ensure database tables are created when running under a WSGI server
with app.app_context():
    db.create_all()

# Expose the Flask app as module-level variable for WSGI servers
# Gunicorn entrypoint: "wsgi:app"

