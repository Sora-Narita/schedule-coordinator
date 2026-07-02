from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, date, timedelta
import os
from database import db, init_db
from models import Event, ScheduleDate, TimeSlot, Vote

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///schedule.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app)
init_db(app)

# ===== Event Routes =====
@app.route('/api/events', methods=['GET'])
def get_events():
    """Get all events"""
    events = Event.query.all()
    return jsonify([e.to_dict() for e in events])

@app.route('/api/events', methods=['POST'])
def create_event():
    """Create a new event"""
    data = request.get_json()
    
    event = Event(
        title=data.get('title'),
        description=data.get('description', '')
    )
    db.session.add(event)
    db.session.commit()
    
    return jsonify(event.to_dict()), 201

@app.route('/api/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event details"""
    event = Event.query.get_or_404(event_id)
    return jsonify(event.to_dict())

# ===== Schedule Date Routes =====
@app.route('/api/events/<int:event_id>/dates', methods=['POST'])
def add_schedule_date(event_id):
    """Add a date to event schedule"""
    event = Event.query.get_or_404(event_id)
    data = request.get_json()
    
    schedule_date = ScheduleDate(
        event_id=event_id,
        date=datetime.fromisoformat(data.get('date')).date()
    )
    db.session.add(schedule_date)
    db.session.commit()
    
    return jsonify(schedule_date.to_dict()), 201

# ===== Time Slot Routes =====
@app.route('/api/schedule-dates/<int:schedule_date_id>/time-slots', methods=['POST'])
def add_time_slot(schedule_date_id):
    """Add time slots to a date"""
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

# ===== Vote Routes =====
@app.route('/api/time-slots/<int:time_slot_id>/vote', methods=['POST'])
def vote_time_slot(time_slot_id):
    """Vote for a time slot"""
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

@app.route('/api/time-slots/<int:time_slot_id>/unvote', methods=['POST'])
def unvote_time_slot(time_slot_id):
    """Remove vote from a time slot"""
    data = request.get_json()
    voter_name = data.get('voter_name')
    
    vote = Vote.query.filter_by(
        time_slot_id=time_slot_id,
        voter_name=voter_name
    ).first_or_404()
    
    db.session.delete(vote)
    db.session.commit()
    
    return jsonify({'success': True}), 200

# ===== Stats Routes =====
@app.route('/api/events/<int:event_id>/best-slot', methods=['GET'])
def get_best_slot(event_id):
    """Get the best time slot(s) based on votes"""
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
