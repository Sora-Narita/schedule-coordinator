from database import db
from datetime import datetime

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
