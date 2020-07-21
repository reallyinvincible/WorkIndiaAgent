from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash
from flask_marshmallow import Marshmallow
import time
import os

# create flask app
app = Flask(__name__)

# find database
app.config[
    'SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# init db
db = SQLAlchemy(app)

# init Marshmallow
ma = Marshmallow(app)


# Models
class Agent(db.Model):
    __tablename__ = "agents"
    agent_id = db.Column(db.String(100), primary_key=True)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, agent_id, password):
        self.agent_id = agent_id
        self.password = password


class Task(db.Model):
    __tablename__ = "tasks"
    task_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    category = db.Column(db.String(100), default="general")
    time_created = db.Column(db.BigInteger, default=(time.time() * 1000))
    created_by = db.Column(db.String(1000), nullable=False, default="0")
    due_by = db.Column(db.BigInteger, default=((time.time() * 1000) + (24 * 60 * 60 * 1000)))

    def __init__(self, title, description, category, created_by, due_by):
        self.title = title
        self.description = description
        self.category = category
        self.created_by = created_by
        self.due_by = due_by


class TaskSchema(ma.Schema):
    class Meta:
        fields = ('task_id', 'title', 'description', 'category', 'time_created', 'created_by', 'due_by')


class Response:
    status = 'request successful'
    status_code = 200
    error = False
    message = 'call completed'
    payload = {}

    def __init__(self, status, error, message, payload):
        self.status = status
        self.error = error
        self.message = message
        self.payload = payload


@app.before_request
def setup_db():
    db.create_all()


# Home Route
@app.route('/', methods=['GET'])
def home():
    print('hello')
    return "<h1>Welcome to Home Agent X</h1>"


# Route to create an agent
@app.route('/app/agent/', methods=['POST'])
def create_agent():
    agent_id = request.json['agent_id']
    agent_password = request.json['agent_password']
    agent_query = Agent.query.filter_by(agent_id=agent_id).first()
    if agent_query:
        response = Response('account already exists', True, 'account already exists', None)
        response.status_code = 402
        return jsonify(response.__dict__)
    agent = Agent(agent_id, generate_password_hash(agent_password, method='sha256'))
    agent_dict = dict(agent.__dict__)
    agent_dict.pop('_sa_instance_state')
    agent_dict.pop('password')
    response = Response('account created', False, 'data added successfully', agent_dict)
    try:
        db.session.add(agent)
        db.session.commit()
    except SQLAlchemyError as e:
        error = str(e.__dict__['orig'])
        response = Response('failure', True, error, None)
    return jsonify(response.__dict__)


# Route to authenticate an agent
@app.route('/app/agent/auth/', methods=['POST'])
def verify_agent():
    agent_id = request.json['agent_id']
    agent_password = request.json['agent_password']
    agent_query = Agent.query.filter_by(agent_id=agent_id).first()
    if not agent_query or not check_password_hash(agent_query.password, agent_password):
        response = Response('failed', True, 'wrong password', None)
        response.status_code = 401
        return jsonify(response.__dict__)
    agent_dict = dict(agent_query.__dict__)
    agent_dict.pop('_sa_instance_state')
    agent_dict.pop('password')
    response = Response('success', False, 'data authenticated', agent_dict)
    return jsonify(response.__dict__)


# Route to create a task
@app.route('/app/sites/', methods=['POST'])
def create_task():
    agent_id = request.args.get('agent')
    title = request.json['title']
    description = request.json['description']
    category = request.json['category']
    due_by = request.json['due_by']
    task = Task(title, description, category, agent_id, due_by)
    task_dict = dict(task.__dict__)
    task_dict.pop('_sa_instance_state')
    response = Response('success', False, 'data added successfully', task_dict)
    try:
        db.session.add(task)
        db.session.commit()
    except SQLAlchemyError as e:
        error = str(e.__dict__['orig'])
        response = Response('failure', True, error, None)
    return jsonify(response.__dict__)


# Route to get tasks
@app.route('/app/sites/list/', methods=['GET'])
def get_all():
    agent_id = request.args.get('agent')
    all_tasks = Task.query.filter_by(created_by=agent_id).order_by(Task.due_by).all()
    tasks_list = []
    for task in all_tasks:
        tasks_dict = task.__dict__
        tasks_dict.pop('_sa_instance_state')
        tasks_list.append(tasks_dict)
    response = Response('success', False, 'data fetched successfully', tasks_list)
    return jsonify(response.__dict__)


# Route to update a task
@app.route('/app/sites/<task_id>/', methods=['PUT'])
def update_task(task_id):
    try:
        task = Task.query.get(task_id)
        task.name = request.json['title']
        task.description = request.json['description']
        task.category = request.json['category']
        task.due_by = request.json['due_by']
        task_dict = dict(task.__dict__)
        task_dict.pop('_sa_instance_state')
        response = Response('success', False, 'data updated successfully', task_dict)
        db.session.commit()
        return jsonify(response.__dict__)
    except SQLAlchemyError as e:
        error = str(e.__dict__['orig'])
        response = Response('failure', True, error, None)
        return jsonify(response.__dict__)


# Route to delete a task
@app.route('/app/sites/<task_id>/', methods=['DELETE'])
def delete_task(task_id):
    try:
        task = Task.query.get(task_id)
        task_dict = dict(task.__dict__)
        task_dict.pop('_sa_instance_state')
        db.session.delete(task)
        db.session.commit()
    except SQLAlchemyError as e:
        error = str(e.__dict__['orig'])
        response = Response('failure', True, error, None)
        return jsonify(response.__dict__)
    response = Response('success', False, 'data deleted successfully', task_dict)
    return jsonify(response.__dict__)


if __name__ == '__main__':
    app.run()
