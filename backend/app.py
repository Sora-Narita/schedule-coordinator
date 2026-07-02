from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import os

# ===== Database Setup =====
db = SQLAlchemy()

def init_db(app):
    """Initialize database"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

# ===== Models =====
class Event(db.Model):
    """Schedule event"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    dates = db.relationship('ScheduleDate', back_populates='event', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'dates': [d.to_dict() for d in self.dates]
        }

class ScheduleDate(db.Model):
    """Schedule date for an event"""
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # Relationships
    event = db.relationship('Event', back_populates='dates')
    time_slots = db.relationship('TimeSlot', back_populates='schedule_date', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'date': self.date.isoformat(),
            'time_slots': [t.to_dict() for t in self.time_slots]
        }

class TimeSlot(db.Model):
    """1-hour time slot"""
    id = db.Column(db.Integer, primary_key=True)
    schedule_date_id = db.Column(db.Integer, db.ForeignKey('schedule_date.id'), nullable=False)
    hour = db.Column(db.Integer, nullable=False)  # 0-23
    
    # Relationships
    schedule_date = db.relationship('ScheduleDate', back_populates='time_slots')
    votes = db.relationship('Vote', back_populates='time_slot', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'schedule_date_id': self.schedule_date_id,
            'hour': self.hour,
            'votes_count': len(self.votes),
            'voters': [v.voter_name for v in self.votes]
        }

class Vote(db.Model):
    """User vote for a time slot"""
    id = db.Column(db.Integer, primary_key=True)
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slot.id'), nullable=False)
    voter_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    time_slot = db.relationship('TimeSlot', back_populates='votes')
    
    def to_dict(self):
        return {
            'id': self.id,
            'time_slot_id': self.time_slot_id,
            'voter_name': self.voter_name,
            'created_at': self.created_at.isoformat()
        }

# ===== Flask App =====
app = Flask(__name__)

# Database configuration
if os.environ.get('DATABASE_URL'):
    # Render environment
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace('postgres://', 'postgresql://')
else:
    # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
init_db(app)

# ===== Event Routes =====
@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events"""
    try:
        events = Event.query.all()
        return jsonify([e.to_dict() for e in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
def create_event():
    """Create a new event"""
    try:
        data = request.get_json()
        
        event = Event(
            title=data.get('title'),
            description=data.get('description', '')
        )
        db.session.add(event)
        db.session.commit()
        
        return jsonify(event.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event details"""
    try:
        event = Event.query.get_or_404(event_id)
        return jsonify(event.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== Schedule Date Routes =====
@app.route('/api/events/<int:event_id>/dates', methods=['POST'])
def add_schedule_date(event_id):
    """Add a date to event schedule"""
    try:
        event = Event.query.get_or_404(event_id)
        data = request.get_json()
        
        schedule_date = ScheduleDate(
            event_id=event_id,
            date=datetime.fromisoformat(data.get('date')).date()
        )
        db.session.add(schedule_date)
        db.session.commit()
        
        return jsonify(schedule_date.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Time Slot Routes =====
@app.route('/api/schedule-dates/<int:schedule_date_id>/time-slots', methods=['POST'])
def add_time_slot(schedule_date_id):
    """Add time slots to a date"""
    try:
        schedule_date = ScheduleDate.query.get_or_404(schedule_date_id)
        data = request.get_json()
        
        hours = data.get('hours', [])  # List of hours [9, 10, 11, ...]
        created_slots = []
        
        for hour in hours:
            # Check if slot already exists
            existing = TimeSlot.query.filter_by(
                schedule_date_id=schedule_date_id,
                hour=hour
            ).first()
            
            if not existing:
                time_slot = TimeSlot(
                    schedule_date_id=schedule_date_id,
                    hour=hour
                )
                db.session.add(time_slot)
                created_slots.append(time_slot)
        
        db.session.commit()
        return jsonify([s.to_dict() for s in created_slots]), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Vote Routes =====
@app.route('/api/time-slots/<int:time_slot_id>/vote', methods=['POST'])
def vote_time_slot(time_slot_id):
    """Vote for a time slot"""
    try:
        time_slot = TimeSlot.query.get_or_404(time_slot_id)
        data = request.get_json()
        
        voter_name = data.get('voter_name')
        if not voter_name:
            return jsonify({'error': 'voter_name is required'}), 400
        
        # Check if user already voted for this slot
        existing_vote = Vote.query.filter_by(
            time_slot_id=time_slot_id,
            voter_name=voter_name
        ).first()
        
        if existing_vote:
            return jsonify({'error': 'User already voted for this slot'}), 400
        
        vote = Vote(
            time_slot_id=time_slot_id,
            voter_name=voter_name
        )
        db.session.add(vote)
        db.session.commit()
        
        return jsonify(vote.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/time-slots/<int:time_slot_id>/unvote', methods=['POST'])
def unvote_time_slot(time_slot_id):
    """Remove vote from a time slot"""
    try:
        data = request.get_json()
        voter_name = data.get('voter_name')
        
        vote = Vote.query.filter_by(
            time_slot_id=time_slot_id,
            voter_name=voter_name
        ).first_or_404()
        
        db.session.delete(vote)
        db.session.commit()
        
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ===== Stats Routes =====
@app.route('/api/events/<int:event_id>/best-slot', methods=['GET'])
def get_best_slot(event_id):
    """Get the best time slot(s) based on votes"""
    try:
        event = Event.query.get_or_404(event_id)
        
        best_slots = []
        max_votes = 0
        
        for schedule_date in event.dates:
            for time_slot in schedule_date.time_slots:
                vote_count = len(time_slot.votes)
                if vote_count > max_votes:
                    max_votes = vote_count
                    best_slots = [time_slot]
                elif vote_count == max_votes and vote_count > 0:
                    best_slots.append(time_slot)
        
        return jsonify({
            'max_votes': max_votes,
            'best_slots': [s.to_dict() for s in best_slots]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== Health Check =====
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
