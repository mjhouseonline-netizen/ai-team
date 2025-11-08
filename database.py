"""
Database models and configuration for AI Team authentication
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

# Initialize SQLAlchemy
db = SQLAlchemy()


class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    integrations = db.relationship('Integration', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set the user's password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify the user's password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active
        }
    
    def __repr__(self):
        return f'<User {self.email}>'


class Integration(db.Model):
    """Third-party integration model"""
    __tablename__ = 'integrations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False, index=True)  # 'google', 'slack', etc.
    access_token = db.Column(db.Text, nullable=False)  # Hashed token
    token_expires_at = db.Column(db.DateTime)
    metadata = db.Column(db.JSON)  # Additional provider-specific data
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    refresh_tokens = db.relationship('RefreshToken', backref='integration', lazy=True, cascade='all, delete-orphan')
    
    # Composite unique constraint: one integration per provider per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'provider', name='unique_user_provider'),
    )
    
    def is_token_expired(self):
        """Check if access token is expired"""
        if not self.token_expires_at:
            return False
        return datetime.utcnow() >= self.token_expires_at
    
    def to_dict(self):
        """Convert integration to dictionary"""
        return {
            'id': self.id,
            'provider': self.provider,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata,
            'token_expired': self.is_token_expired()
        }
    
    def __repr__(self):
        return f'<Integration {self.provider} for User {self.user_id}>'


class RefreshToken(db.Model):
    """Refresh token storage for OAuth integrations"""
    __tablename__ = 'refresh_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    integration_id = db.Column(db.Integer, db.ForeignKey('integrations.id'), nullable=False, unique=True)
    token = db.Column(db.Text, nullable=False)  # Hashed refresh token
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RefreshToken for Integration {self.integration_id}>'


# Database initialization functions

def init_db(app):
    """Initialize the database with the Flask app"""
    db.init_app(app)
    return db


def create_tables():
    """Create all database tables"""
    db.create_all()
    print("Database tables created successfully")


def drop_tables():
    """Drop all database tables (use with caution!)"""
    db.drop_all()
    print("Database tables dropped")


def reset_db():
    """Reset the database (drop and recreate all tables)"""
    drop_tables()
    create_tables()
    print("Database reset complete")


# Helper functions for database operations

def get_or_create(session, model, **kwargs):
    """Get an existing record or create a new one"""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance, True


def create_test_user(email='test@example.com', password='testpassword', name='Test User'):
    """Create a test user for development"""
    user = User(email=email, name=name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    print(f"Test user created: {email}")
    return user
