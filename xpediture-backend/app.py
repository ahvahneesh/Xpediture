import os
from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'xpediture-super-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xpediture.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# Models
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    home_currency = db.Column(db.String(3), default='USD')

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class Trip(db.Model):
    __tablename__ = 'trips'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100))
    currency_code = db.Column(db.String(3), nullable=False)
    status = db.Column(db.String(20))
    start_date = db.Column(db.String(10))
    end_date = db.Column(db.String(10))
    budget = db.Column(db.Numeric(10, 2), default=0.00)
    cover_url = db.Column(db.Text)

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id', ondelete='SET NULL'))
    date = db.Column(db.String(10), nullable=False)

class ChecklistItem(db.Model):
    __tablename__ = 'checklist_items'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False)
    item_text = db.Column(db.String(255), nullable=False)
    is_done = db.Column(db.Boolean, default=False)

# Auth API
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_pw, home_currency=data.get('home_currency', 'USD'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created"}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        session['user_id'] = user.id
        return jsonify({"u": user.username, "base": user.home_currency})
    return jsonify({"error": "Invalid credentials"}), 401

# Trips API
@app.route('/api/trips', methods=['GET', 'POST'])
def manage_trips():
    uid = session.get('user_id')
    if not uid: return jsonify({"error": "Unauthorized"}), 401
    
    if request.method == 'POST':
        data = request.json
        new_trip = Trip(user_id=uid, name=data['name'], currency_code=data['currency_code'], 
                        status=data['status'], start_date=data.get('start_date'), 
                        end_date=data.get('end_date'), budget=data.get('budget', 0),
                        cover_url=data.get('cover_url'))
        db.session.add(new_trip)
        db.session.commit()
        return jsonify({"message": "Trip created", "id": new_trip.id}), 201
    
    trips = Trip.query.filter_by(user_id=uid).all()
    return jsonify([{ "id": t.id, "name": t.name, "currency": t.currency_code, "status": t.status, "budget": float(t.budget), "cover": t.cover_url } for t in trips])

# Expenses API
@app.route('/api/expenses/<int:trip_id>', methods=['GET', 'POST'])
def manage_expenses(trip_id):
    if request.method == 'POST':
        data = request.json
        new_exp = Expense(trip_id=trip_id, title=data['title'], amount=data['amount'], 
                          category_id=data.get('category_id'), date=data['date'])
        db.session.add(new_exp)
        db.session.commit()
        return jsonify({"message": "Expense added"}), 201
    
    exps = db.session.query(Expense, Category.name).outerjoin(Category).filter(Expense.trip_id == trip_id).all()
    return jsonify([{ "id": e[0].id, "title": e[0].title, "amount": float(e[0].amount), "category": e[1], "date": e[0].date } for e in exps])

# Checklist API
@app.route('/api/checklist/<int:trip_id>', methods=['GET', 'POST'])
def manage_checklist(trip_id):
    if request.method == 'POST':
        data = request.json
        new_item = ChecklistItem(trip_id=trip_id, item_text=data['item_text'], is_done=data.get('is_done', False))
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"message": "Item added"}), 201
    
    items = ChecklistItem.query.filter_by(trip_id=trip_id).all()
    return jsonify([{ "id": i.id, "item_text": i.item_text, "is_done": i.is_done } for i in items])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
