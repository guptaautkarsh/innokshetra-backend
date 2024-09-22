from datetime import datetime
from hack import db, app

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(30), nullable=False)
    past_pdfs = db.relationship('Pdf', backref='parent', lazy=True)

    def __repr__(self):
        return '{} {}'.format(self.username, self.email)


class Pdf(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pdf_name = db.Column(db.String(120), nullable=False)
    actual_pdf_name = db.Column(db.String(120), nullable=False)
    date_posted = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # user table is used

    def __repr__(self):
        return 'Pdf({}, {}, {})'.format(self.pdf_name, self.actual_pdf_name, self.date_posted)


with app.app_context(): #tables created if not present
    db.create_all()