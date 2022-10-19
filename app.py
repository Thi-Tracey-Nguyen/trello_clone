from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import date, timedelta
from flask_marshmallow import Marshmallow, fields
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://trello_dev:password123@127.0.0.1:5432/trello'
app.config['JWT_SECRET_KEY'] = 'hello there'

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

class Card(db.Model):
    __tablename__ = 'cards'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    date = db.Column(db.Date)
    status = db.Column(db.String)
    priority = db.Column(db.String)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)


class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'name', 'email', 'password', 'is_admin')
        

class CardSchema(ma.Schema):
    class Meta:
        fields = ("id", "title", "description", "date", "status", "priority")
        ordered = True

def authorize():
    user_id = get_jwt_identity() #extract the user identity from the token
    stmt = db.select(User).filter_by(id = user_id)
    user = db.session.scalar(stmt)
    return user.is_admin
    

@app.cli.command('create')
def create_db():
    db.create_all()
    print('Table created')

@app.cli.command('seed')
def seed_db():
    cards = [
        Card(
            title = 'Start the project',
            description = 'Stage 1 - Create the database',
            status = 'To Do',
            priority = 'High',
            date = date.today()
        ),
        Card(
            title = "SQLAlchemy",
            description = "Stage 2 - Integrate ORM",
            status = "Ongoing",
            priority = "High",
            date = date.today()
        ),
        Card(
            title = "ORM Queries",
            description = "Stage 3 - Implement several queries",
            status = "Ongoing",
            priority = "Medium",
            date = date.today()
        ),
        Card(
            title = "Marshmallow",
            description = "Stage 4 - Implement Marshmallow to jsonify models",
            status = "Ongoing",
            priority = "Medium",
            date = date.today()
        )
    ]
    users = [
        User(
            email = 'admin@spam.com',
            password = bcrypt.generate_password_hash('eggs').decode('utf-8'),
            is_admin = True,
        ),
        User(
            name = 'Tracey', 
            email = 'tracey@spam.com',
            password = bcrypt.generate_password_hash('12345').decode('utf-8'),
        ),
    ]

    db.session.add_all(cards)
    db.session.add_all(users)
    db.session.commit()
    print('Tables seeded!')

@app.cli.command('drop')
def drop_tables():
    db.drop_all()
    print('Tables dropped')


@app.route('/auth/register/', methods=['POST'])
def auth_register():
    try:
        user = User(
            email = request.json['email'],
            password = bcrypt.generate_password_hash(request.json['password']).decode('utf-8'),
            name = request.json['name']
        )
        db.session.add(user)
        db.session.commit()
        #Respond to the user
        return UserSchema(exclude=['password']).dump(user), 201
    except IntegrityError:
        return {'error': 'Email address already in use'}, 409


@app.route('/cards/')
@jwt_required()
def all_cards():
    if not authorize():
        return {"error": "You must be an admin"}, 401
    # cards = Card.query.all()
    # return CardSchema(many=True).dump(cards)
    stmt = db.select(Card).order_by(Card.priority, Card.title)
    cards = db.session.scalars(stmt)
    return CardSchema(many=True).dump(cards)
  

@app.route('/auth/login/', methods=['POST'])
def auth_login():
    stmt = db.select(User).filter_by(email = request.json["email"])
    user = db.session.scalar(stmt)
    if user and bcrypt.check_password_hash(user.password, request.json["password"]):
        # return UserSchema(exclude=["password"]).dump(user), 200
        # generate token
        token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=1))
        return {'email': user.email, 'token': token, 'is_admin': user.is_admin}
    else:
        return {"error": "Invalid email or password"}, 401 #401 Unauthorized


@app.cli.command('first_card')
def first_card():
    # card = Card.query.first()
    # print(card.__dict__)
    stmt = db.select(Card).limit(1)
    card = db.session.scalar(stmt)
    print(card.__dict__)


@app.cli.command('count_ongoing')
def count():
    stmt = db.select(db.func.count()).select_from(Card).filter_by(status = 'Ongoing')
    cards = db.session.scalar(stmt)
    print(cards)


@app.route('/')
def index():
    return 'Welcome to my Flask - ORM class!'

