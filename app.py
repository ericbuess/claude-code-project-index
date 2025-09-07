#!/usr/bin/env python3
"""
Simple Flask web application for testing parsing accuracy.
Contains various Python patterns: classes, functions, decorators, etc.
"""

from flask import Flask, request, jsonify, session
from functools import wraps
import hashlib
import jwt
import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass

app = Flask(__name__)
app.secret_key = "test-secret-key"


@dataclass
class User:
    """User data model."""
    id: int
    username: str
    email: str
    password_hash: str
    created_at: datetime.datetime
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash."""
        return verify_password(password, self.password_hash)


class UserManager:
    """Manages user operations and database interactions."""
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.next_id = 1
    
    def create_user(self, username: str, email: str, password: str) -> Optional[User]:
        """Create a new user account."""
        if self.find_by_username(username):
            return None
        
        password_hash = hash_password(password)
        user = User(
            id=self.next_id,
            username=username,
            email=email,
            password_hash=password_hash,
            created_at=datetime.datetime.now()
        )
        
        self.users[self.next_id] = user
        self.next_id += 1
        return user
    
    def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        for user in self.users.values():
            if user.username == username:
                return user
        return None
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """Find user by ID."""
        return self.users.get(user_id)
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        user = self.find_by_username(username)
        if user and user.check_password(password):
            return user
        return None


# Global user manager instance
user_manager = UserManager()


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hash_value: str) -> bool:
    """Verify password against hash."""
    return hash_password(password) == hash_value


def generate_jwt_token(user: User) -> str:
    """Generate JWT token for user."""
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')


def decode_jwt_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if token.startswith('Bearer '):
            token = token[7:]
        
        payload = decode_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        
        user = user_manager.find_by_id(payload['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        request.current_user = user
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['username', 'email', 'password']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    user = user_manager.create_user(
        data['username'],
        data['email'],
        data['password']
    )
    
    if not user:
        return jsonify({'error': 'Username already exists'}), 409
    
    token = generate_jwt_token(user)
    return jsonify({
        'message': 'User created successfully',
        'user': user.to_dict(),
        'token': token
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and return token."""
    data = request.get_json()
    
    if not data or not all(k in data for k in ['username', 'password']):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = user_manager.authenticate(data['username'], data['password'])
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = generate_jwt_token(user)
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict(),
        'token': token
    })


@app.route('/api/profile')
@require_auth
def get_profile():
    """Get current user's profile."""
    return jsonify({
        'user': request.current_user.to_dict()
    })


@app.route('/api/users')
@require_auth
def list_users():
    """List all users (admin only for demo)."""
    users = [user.to_dict() for user in user_manager.users.values()]
    return jsonify({'users': users})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({'error': 'Internal server error'}), 500


def create_sample_users():
    """Create sample users for testing."""
    sample_users = [
        ('admin', 'admin@example.com', 'admin123'),
        ('testuser', 'test@example.com', 'password123'),
        ('demo', 'demo@example.com', 'demo123')
    ]
    
    for username, email, password in sample_users:
        user_manager.create_user(username, email, password)


if __name__ == '__main__':
    create_sample_users()
    app.run(debug=True, host='0.0.0.0', port=5000)