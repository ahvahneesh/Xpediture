import os
from flask import Flask, request, jsonify, session, redirect, url_for
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
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Username already exists"}), 400
        
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
        return jsonify({
            "id": user.id, 
            "username": user.username, 
            "home_currency": user.home_currency
        })
    return jsonify({"error": "Invalid credentials"}), 401

# Trips API
@app.route('/api/trips', methods=['GET', 'POST'])
def manage_trips():
    # Check URL first, then JSON body, then session
    uid = request.args.get('user_id') or session.get('user_id')
    if request.is_json and not uid:
        uid = request.json.get('user_id')
        
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
    result = []
    for t in trips:
        expenses = Expense.query.filter_by(trip_id=t.id).all()
        total_spent = sum([float(e.amount) for e in expenses])
        result.append({ 
            "id": t.id, 
            "name": t.name, 
            "currency_code": t.currency_code, 
            "status": t.status, 
            "start_date": t.start_date,
            "end_date": t.end_date,
            "budget": float(t.budget) if t.budget else 0, 
            "cover_url": t.cover_url,
            "total_spent": total_spent
        })
    return jsonify(result)

# THE MISSING DELETE ROUTE
@app.route('/api/trips/<int:trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    trip = Trip.query.get(trip_id)
    if trip:
        db.session.delete(trip)
        db.session.commit()
        return jsonify({"message": "Deleted"}), 200
    return jsonify({"error": "Not found"}), 404

# Expenses API
@app.route('/api/expenses/<int:trip_id>', methods=['GET', 'POST'])
def manage_expenses(trip_id):
    if request.method == 'POST':
        data = request.json
        cat_name = data.get('category_name')
        cat_id = None
        
        # If a category is sent, find its ID or create it dynamically in the DB!
        if cat_name:
            category = Category.query.filter_by(name=cat_name).first()
            if not category:
                category = Category(name=cat_name)
                db.session.add(category)
                db.session.commit() # Save to generate the ID
            cat_id = category.id

        new_exp = Expense(trip_id=trip_id, title=data['title'], amount=data['amount'], 
                          category_id=cat_id, date=data['date'])
        db.session.add(new_exp)
        db.session.commit()
        return jsonify({"message": "Expense added"}), 201
    
    exps = db.session.query(Expense, Category.name).outerjoin(Category).filter(Expense.trip_id == trip_id).all()
    return jsonify([{ "id": e[0].id, "title": e[0].title, "amount": float(e[0].amount), "category": e[1], "date": e[0].date } for e in exps])

@app.route('/api/expenses/delete/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    exp = Expense.query.get(expense_id)
    if exp:
        db.session.delete(exp)
        db.session.commit()
        return jsonify({"message": "Expense deleted"}), 200
    return jsonify({"error": "Expense not found"}), 404

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

@app.route('/api/checklist/item/<int:item_id>', methods=['PUT', 'DELETE'])
def modify_checklist_item(item_id):
    item = ChecklistItem.query.get(item_id)
    if not item: return jsonify({"error": "Item not found"}), 404
    
    if request.method == 'PUT':
        data = request.json
        if 'is_done' in data:
            item.is_done = data['is_done']
        db.session.commit()
        return jsonify({"message": "Item updated"}), 200
        
    if request.method == 'DELETE':
        db.session.delete(item)
        db.session.commit()
        return jsonify({"message": "Item deleted"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)