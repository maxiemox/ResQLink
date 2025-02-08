from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_cors import CORS

from database import db
app = Flask(__name__)
CORS(app)  # Allow all origins


# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'resqlink.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class HelpRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    people_affected = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact': self.contact,
            'location': self.location,
            'category': self.category,
            'description': self.description,
            'people_affected': self.people_affected,
            'status': self.status,
            'timestamp': self.timestamp.isoformat()
        }

# Create database tables
with app.app_context():
    db.create_all()

# Route Handlers
@app.route('/')
def index():
    return render_template('helpline.html')

@app.route('/dashboard')
def dashboard():
    return render_template('authority_dashboard.html')

@app.route('/helpline/<int:request_id>')
def helpline(request_id=None):
    if request_id:
        help_request = HelpRequest.query.get_or_404(request_id)
        return render_template('helpline.html', request=help_request)
    return render_template('helpline.html')

@app.route('/api/submit', methods=['POST'])
def submit_request():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'contact', 'location', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400

        # Create new help request
        new_request = HelpRequest(
            name=data['name'],
            contact=data['contact'],
            location=data['location'],
            category=data['category'],
            description=data['description'],
            people_affected=int(data.get('people_affected', 1)),
            status='pending'
        )

        # Save to database
        db.session.add(new_request)
        db.session.commit()

        return jsonify({
            'message': 'Request submitted successfully',
            'request_id': new_request.id
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error submitting request: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@app.route('/api/get_requests', methods=['GET'])
def get_requests():
    try:
        # Get optional filter parameters
        category = request.args.get('category')
        status = request.args.get('status')

        # Build query
        query = HelpRequest.query
        if category:
            query = query.filter_by(category=category)
        if status:
            query = query.filter_by(status=status)

        # Order by timestamp (most recent first)
        requests = query.order_by(HelpRequest.timestamp.desc()).all()
        
        return jsonify({
            'requests': [request.to_dict() for request in requests]
        }), 200

    except Exception as e:
        print(f"Error fetching requests: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@app.route('/api/resolve_request/<int:request_id>', methods=['POST'])
def resolve_request(request_id):
    try:
        help_request = HelpRequest.query.get_or_404(request_id)
        help_request.status = 'resolved'
        db.session.commit()

        return jsonify({
            'message': 'Request marked as resolved',
            'request_id': request_id
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error resolving request: {str(e)}")
        return jsonify({
            'error': 'Internal server error'
        }), 500

@app.route('/api/regions/affected')
def get_affected_regions():
    try:
        regions = db.get_affected_regions()
        return jsonify({'regions': regions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts/<district>/<state>')
def get_regional_contacts(district, state):
    try:
        contacts = db.get_contacts_by_region(district, state)
        return jsonify({'contacts': contacts}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    try:
        alert_data = request.get_json()
        alert_id = db.add_region_alert(alert_data)
        return jsonify({'message': 'Alert created', 'id': alert_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'error': 'Resource not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(debug=True)
