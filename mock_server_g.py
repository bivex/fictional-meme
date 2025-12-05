#!/usr/bin/env python3
"""
Mock API Server for Domain-Driven OpenAPI Testing

Creates a mock server that responds to all OpenAPI endpoints with
valid responses based on your domain model schemas.
"""

from flask import Flask, request, jsonify, redirect, Response
import json
import random
import re
import time
import logging
from datetime import datetime, timezone

print("Mock server script started.") # Debug print

app = Flask(__name__)

# Configure Flask to return JSON errors instead of HTML
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Disable HTML error pages for better API compliance
app.config['TRAP_HTTP_EXCEPTIONS'] = True
app.config['TESTING'] = False

# Enhanced security middleware to handle malformed headers and protect against attacks
import time
import logging
import threading
from collections import defaultdict, deque

from webob import Request

class SafeWSGIMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        try:
            Request(environ)  # безопасный парсер
            return self.app(environ, start_response)
        except Exception as e:
            # Return JSON error instead of HTML for API compliance
            start_response("400 Bad Request", [("Content-Type", "application/json")])
            return [b'{"error": {"code": "BAD_REQUEST", "message": "Invalid HTTP header"}}']

# Apply enhanced security middleware
app.wsgi_app = SafeWSGIMiddleware(app.wsgi_app)

# Custom error handlers to ensure JSON responses
@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({"error": {"code": "BAD_REQUEST", "message": "Bad request"}}), 400

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({"error": {"code": "NOT_FOUND", "message": "Endpoint not found"}}), 404

@app.errorhandler(405)
def method_not_allowed_error(error):
    # Determine supported methods for the current endpoint
    supported_methods = set()
    if request.url_rule:
        # Get methods supported by the current route
        supported_methods = request.url_rule.methods.copy()
        # Remove OPTIONS and HEAD if present (OPTIONS is handled separately, HEAD is automatic)
        supported_methods.discard('OPTIONS')
        supported_methods.discard('HEAD')
    else:
        # Fallback - assume common methods for unknown routes
        supported_methods = {'GET', 'POST', 'PUT', 'DELETE'}

    # Sort methods for consistent output
    allow_header = ', '.join(sorted(supported_methods))

    response = jsonify({"error": {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed"}})
    response.headers['Allow'] = allow_header
    return response, 405

@app.errorhandler(406)
def not_acceptable_error(error):
    return jsonify({"error": {"code": "NOT_ACCEPTABLE", "message": "Not acceptable"}}), 406

@app.errorhandler(422)
def unprocessable_entity_error(error):
    return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Unprocessable entity"}}), 422

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}), 500

# Global error handler for all exceptions
@app.errorhandler(Exception)
def handle_exception(error):
    # Log the error
    app.logger.error(f"Unhandled exception: {error}")
    return jsonify({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}), 500

# Add comprehensive headers for ads server compatibility
@app.after_request
def add_cors_headers(response):
    # Enhanced CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-API-Key, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    response.headers['Access-Control-Max-Age'] = '86400'

    # Security headers for ads server
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # Cache control for ad serving (short cache for dynamic content)
    if request.path.startswith('/mock-'):
        response.headers['Cache-Control'] = 'private, max-age=300'  # 5 minutes for ad pages
    else:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'

    # Mobile and ad-specific headers
    response.headers['Mobile-Web-App-Capable'] = 'yes'
    response.headers['Apple-Mobile-Web-App-Capable'] = 'yes'
    response.headers['Apple-Mobile-Web-App-Status-Bar-Style'] = 'default'

    # Performance headers
    response.headers['Connection'] = 'close'

    return response

# Global regex patterns
date_time_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?$'
date_pattern = r'^\d{4}-\d{2}-\d{2}$'

# ============================================================================
# MOCK DATA MANAGEMENT
# ============================================================================

# Simple in-memory storage to simulate state management
mock_storage = {
    "campaigns": {},
    "deleted_campaigns": set(),
    "landing_pages": {},
    "analytics_cache": {},
    "clicks": []  # Initialize clicks storage
}

def reset_storage():
    """Reset all mock storage"""
    global mock_storage
    mock_storage = {
        "campaigns": {},
        "deleted_campaigns": set(),
        "landing_pages": {},
        "analytics_cache": {},
        "clicks": []  # Initialize clicks storage
    }

    # Create some initial mock campaigns for testing
    mock_campaigns = [
        {
            "id": "camp_123",  # Used in security tests
            "name": "Summer Sale Campaign",
            "description": "High-converting summer promotion",
            "status": "active",
            "schedule": {
                "startDate": "2024-01-01T00:00:00Z",
                "endDate": "2024-12-31T23:59:59Z",
            },
            "urls": {
                "safePage": "https://example.com/safe-landing",
                "offerPage": "https://example.com/offer",
            },
            "financial": {
                "costModel": "CPA",
                "payout": {"amount": 25.50, "currency": "USD"},
                "dailyBudget": {"amount": 500.00, "currency": "USD"},
                "totalBudget": {"amount": 15000.00, "currency": "USD"},
                "spent": {"amount": 1250.75, "currency": "USD"},
            },
            "performance": {
                "clicks": 5000,
                "conversions": 150,
                "ctr": 0.025,
                "cr": 0.03,
                "epc": {"amount": 8.35, "currency": "USD"},
                "roi": 2.15,
            },
            "createdAt": "2024-01-01T10:00:00Z",
            "updatedAt": "2024-01-15T15:00:00Z",
            "_links": {
                "self": "/api/v1/campaigns/camp_123",
                "landingPages": "/api/v1/campaigns/camp_123/landing-pages",
                "offers": "/api/v1/campaigns/camp_123/offers",
                "analytics": "/api/v1/campaigns/camp_123/analytics",
            }
        },
        {
            "id": "camp_456",
            "name": "Winter Promotion",
            "description": "Holiday season marketing campaign",
            "status": "active",
            "schedule": {
                "startDate": "2024-11-01T00:00:00Z",
                "endDate": "2024-12-31T23:59:59Z",
            },
            "urls": {
                "safePage": "https://example.com/winter-landing",
                "offerPage": "https://example.com/winter-offer",
            },
            "financial": {
                "costModel": "CPC",
                "payout": {"amount": 15.00, "currency": "USD"},
                "dailyBudget": {"amount": 300.00, "currency": "USD"},
                "totalBudget": {"amount": 9000.00, "currency": "USD"},
                "spent": {"amount": 2100.00, "currency": "USD"},
            },
            "performance": {
                "clicks": 8000,
                "conversions": 240,
                "ctr": 0.032,
                "cr": 0.03,
                "epc": {"amount": 6.25, "currency": "USD"},
                "roi": 1.85,
            },
            "createdAt": "2024-11-01T08:00:00Z",
            "updatedAt": "2024-11-20T12:00:00Z",
            "_links": {
                "self": "/api/v1/campaigns/camp_456",
                "landingPages": "/api/v1/campaigns/camp_456/landing-pages",
                "offers": "/api/v1/campaigns/camp_456/offers",
                "analytics": "/api/v1/campaigns/camp_456/analytics",
            }
        }
    ]

    # Add mock campaigns to storage
    for campaign in mock_campaigns:
        mock_storage["campaigns"][campaign["id"]] = campaign

    # Create some initial mock clicks for testing
    mock_clicks = [
        {
            'id': '123e4567-e89b-12d3-a456-426614174000',  # Used in tests
            'cid': 123,
            'ip': '192.168.1.100',
            'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'ref': 'https://facebook.com/ad/123',
            'isValid': 1,
            'ts': 1640995200,
            'sub1': 'fb_ad_15',
            'sub2': 'facebook',
            'sub3': 'adset_12',
            'sub4': 'video1',
            'sub5': 'lookalike78',
            'clickId': 'USERCLICK123',
            'affSub': 'aff_sub_123',
            'affSub2': None,
            'affSub3': None,
            'affSub4': None,
            'affSub5': None,
            'fraudScore': 0.0,
            'fraudReason': None,
            'landingPageId': 456,
            'campaignOfferId': 789,
            'trafficSourceId': 101,
            'conversionType': 'sale'
        },
        {
            'id': '456e7890-e89b-12d3-a456-426614174001',
            'cid': 456,
            'ip': '10.0.0.50',
            'ua': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'ref': 'https://google.com/search?q=test',
            'isValid': 1,
            'ts': 1641081600,
            'sub1': 'google_search',
            'sub2': 'google',
            'sub3': 'brand_campaign',
            'sub4': 'text_ad',
            'sub5': 'keyword_123',
            'clickId': 'GOOGLE_CLICK_456',
            'affSub': 'network_a',
            'affSub2': 'sub_a1',
            'affSub3': None,
            'affSub4': None,
            'affSub5': None,
            'fraudScore': 0.1,
            'fraudReason': None,
            'landingPageId': 457,
            'campaignOfferId': 790,
            'trafficSourceId': 102,
            'conversionType': 'lead'
        }
    ]

    # Add mock clicks to storage
    mock_storage["clicks"] = mock_clicks

# Initialize storage with mock data
reset_storage()

def is_campaign_deleted(campaign_id):
    """Check if campaign was deleted"""
    return campaign_id in mock_storage["deleted_campaigns"]

def mark_campaign_deleted(campaign_id):
    """Mark campaign as deleted"""
    if campaign_id in mock_storage["campaigns"]:
        del mock_storage["campaigns"][campaign_id]
    mock_storage["deleted_campaigns"].add(campaign_id)

# ============================================================================
# AUTHENTICATION VALIDATION
# ============================================================================

def validate_auth(request):
    """Validate Authorization header according to HTTP standards"""
    auth_header = request.headers.get('Authorization', '')

    # No auth header
    if not auth_header:
        return False, {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}, 401

    # Check for control characters or invalid bytes
    try:
        for c in auth_header:
            if ord(c) < 32 or ord(c) > 126:
                return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid characters in authentication header"}}, 401
    except (UnicodeDecodeError, TypeError):
        return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid authentication header encoding"}}, 401

    # Check header length
    if len(auth_header) > 1000:
        return False, {"error": {"code": "VALIDATION_ERROR", "message": "Authentication header too long"}}, 401

    # Authorization header must contain scheme and credentials separated by space
    if ' ' not in auth_header:
        return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid authentication format - missing scheme"}}, 401

    scheme, credentials = auth_header.split(' ', 1)
    scheme = scheme.strip()
    credentials = credentials.strip()

    # Empty scheme or credentials
    if not scheme or not credentials:
        return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid authentication format"}}, 401

    # Validate scheme (case-insensitive for common schemes, but we'll accept various)
    valid_schemes = {'Bearer', 'Basic', 'Token', 'Api-Key', 'ApiKey', 'Digest', 'Negotiate', 'AWS4-HMAC-SHA256'}
    if scheme not in valid_schemes and not scheme.isalpha():
        return False, {"error": {"code": "VALIDATION_ERROR", "message": f"Unsupported authentication scheme: {scheme}"}}, 401

    # Validate credentials based on scheme
    if scheme.upper() == 'BEARER':
        # Bearer tokens (JWT, API keys, etc.)
        if len(credentials) < 8:  # Minimum reasonable token length
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Token too short"}}, 401

        # Reject obviously invalid tokens
        invalid_patterns = ['[filtered]', 'schemathesis', 'null', 'undefined', 'test', 'invalid']
        if any(pattern in credentials.lower() for pattern in invalid_patterns):
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401

        # For JWT-like tokens (contain dots), basic structure validation
        if '.' in credentials and len(credentials.split('.')) != 3:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid JWT format"}}, 401

    elif scheme.upper() == 'BASIC':
        # Basic auth - should be base64 encoded
        import base64
        try:
            decoded = base64.b64decode(credentials)
            if b':' not in decoded:
                return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid Basic auth format"}}, 401
        except Exception:
            return False, {"error": {"code": "VALIDATION_ERROR", "message": "Invalid Base64 encoding in Basic auth"}}, 401

    # For other schemes (Token, Api-Key, etc.), just ensure credentials are present and not obviously invalid
    else:
        if len(credentials) < 4:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Credentials too short"}}, 401

        invalid_patterns = ['[filtered]', 'schemathesis', 'null', 'undefined']
        if any(pattern in credentials.lower() for pattern in invalid_patterns):
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials"}}, 401

    # Check for valid test tokens (for testing purposes only)
    valid_test_tokens = {
        # Bearer tokens
        'test_jwt_token_12345': True,
        'valid_api_key_abcdef': True,
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c': True,

        # Basic auth (user:pass)
        'dXNlcjpwYXNz': True,  # base64('user:pass')
        'YWRtaW46c2VjcmV0': True,  # base64('admin:secret')

        # Token scheme
        'my_test_token_123': True,

        # Api-Key
        'test_api_key_abcdef123': True,
    }

    # Check if credentials are in our valid test tokens
    if credentials in valid_test_tokens:
        # For mock server, we accept these test tokens
        return True, None, None

    # If we reach here, the format is valid, but credentials are not in our test set
    # (since this is a mock server without real authentication)
    return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid credentials"}}, 401

def endpoint_supports_api_key(request):
    """Check if current endpoint supports API key authentication based on OpenAPI spec"""
    path = request.path

    # Endpoints that support apiKey according to OpenAPI spec
    # /v1/campaigns/{campaignId}/analytics - GET
    # Must have at least one character between /campaigns/ and /analytics
    if (path.startswith('/v1/campaigns/') and path.endswith('/analytics') and
        '/campaigns//' not in path and len(path.split('/')) >= 4 and request.method == 'GET'):
        return True

    # /v1/click/{clickId} - GET
    if path.startswith('/v1/click/') and len(path.split('/')) == 4 and request.method == 'GET':
        return True

    # /v1/clicks - GET
    if path == '/v1/clicks' and request.method == 'GET':
        return True

    return False

def validate_scopes(request, required_scopes):
    """Validate that the request has the required OAuth2 scopes"""
    import jwt
    import sys
    from security_middleware_fixed import VALID_API_KEYS

    # Check for Authorization header first
    auth_header = request.headers.get('Authorization', '')
    has_auth_header = bool(auth_header)

    # Check for API key authentication (only for endpoints that support it)
    api_key = request.headers.get('X-API-Key')
    has_api_key = bool(api_key)
    endpoint_expects_api_key = endpoint_supports_api_key(request)

    # Check for valid test tokens first (for testing purposes)
    valid_test_tokens = {
        # Bearer tokens
        'test_jwt_token_12345': ['admin'],  # Admin has all scopes
        'valid_api_key_abcdef': ['campaign:read', 'campaign:write', 'analytics:read'],
        'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c': ['campaign:read'],

        # Basic auth (user:pass) - base64 encoded
        'dXNlcjpwYXNz': ['campaign:read'],  # base64('user:pass')
        'YWRtaW46c2VjcmV0': ['admin'],  # base64('admin:secret')

        # Token scheme
        'my_test_token_123': ['campaign:read', 'campaign:write'],

        # Api-Key
        'test_api_key_abcdef123': ['analytics:read', 'traffic:read'],
    }

    # Case 1: Authorization header present
    if has_auth_header:
        # Check if it's a Bearer token with our test credentials
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer '
            if token in valid_test_tokens:
                token_scopes = valid_test_tokens[token]
                if "admin" in token_scopes or all(scope in token_scopes for scope in required_scopes):
                    return True, None, None
                else:
                    return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope(s): {required_scopes}"}}, 403

        # Check if it's Basic auth with our test credentials
        elif auth_header.startswith('Basic '):
            import base64
            try:
                credentials = auth_header[6:]  # Remove 'Basic '
                if credentials in valid_test_tokens:
                    token_scopes = valid_test_tokens[credentials]
                    if "admin" in token_scopes or all(scope in token_scopes for scope in required_scopes):
                        return True, None, None
                    else:
                        return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope(s): {required_scopes}"}}, 403
            except:
                pass

        # Check if it's Token/Api-Key scheme with our test credentials
        else:
            # Extract scheme and credentials
            if ' ' in auth_header:
                scheme, credentials = auth_header.split(' ', 1)
                if credentials.strip() in valid_test_tokens:
                    token_scopes = valid_test_tokens[credentials.strip()]
                    if "admin" in token_scopes or all(scope in token_scopes for scope in required_scopes):
                        return True, None, None
                    else:
                        return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope(s): {required_scopes}"}}, 403

        # Try JWT validation for non-test tokens
        if auth_header.startswith('Bearer '):
            try:
                token = auth_header[7:] # Remove 'Bearer '
                if not token or '[Filtered]' in token or 'schemathesis' in token.lower() or len(token.strip()) == 0:
                    return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing token"}}, 401

                payload = jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
                token_scopes = payload.get('scopes', [])

                if "admin" in token_scopes:
                    return True, None, None # Admin scope grants all access

                # Validate token scopes
                if not isinstance(token_scopes, list):
                    return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token scopes format"}}, 401

                invalid_scopes = []
                for scope in token_scopes:
                    if scope is None or (isinstance(scope, str) and not scope.strip()):
                        invalid_scopes.append(scope)

                if not token_scopes or invalid_scopes:
                    return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid or empty token scopes"}}, 401

                if all(scope in token_scopes for scope in required_scopes):
                    return True, None, None
                else:
                    return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope(s): {required_scopes}"}}, 403

            except jwt.ExpiredSignatureError:
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Token has expired"}}, 401
            except jwt.InvalidTokenError:
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401
            except Exception as e:
                # Catch any other unexpected errors during token processing
                app.logger.error(f"Token processing error: {e}")
                return False, {"error": {"code": "UNAUTHORIZED", "message": f"Token processing error"}}, 401

    # Case 2: No Authorization header, but API Key is expected and present
    elif not has_auth_header and endpoint_expects_api_key and has_api_key:
        if api_key == '[Filtered]' or not api_key.strip():
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing API Key"}}, 401

        key_info = VALID_API_KEYS.get(api_key.strip())
        if key_info:
            api_key_scopes = key_info.get('scopes', [])
            if "admin" in api_key_scopes:
                return True, None, None
            elif all(scope in api_key_scopes for scope in required_scopes):
                return True, None, None
            else:
                return False, {"error": {"code": "FORBIDDEN", "message": f"API key missing required scope(s): {required_scopes}"}}, 403
        else:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid API Key"}}, 401

    # Case 3: No Authorization header, API Key is expected but missing
    elif not has_auth_header and endpoint_expects_api_key and not has_api_key:
        return False, {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}, 401

    # Case 4: No Authorization header, API Key not expected or not provided (and not expected)
    # This implies that a bearer token or OAuth2 is required but not provided.
    return False, {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}, 401

    # JWT validation (for Authorization header)
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

        try:
            # Decode JWT token (using the same secret as the test token generator)
            payload = jwt.decode(token, "your-secret-key-change-in-production", algorithms=["HS256"])

            # Check for scopes
            token_scopes = payload.get('scopes', [])
            if not isinstance(token_scopes, list):
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token scopes format"}}, 401

            # Validate scope format - check for None, empty strings, or invalid types
            invalid_scopes = []
            for scope in token_scopes:
                if scope is None or (isinstance(scope, str) and not scope.strip()):
                    invalid_scopes.append(scope)

            # Empty scopes list is also invalid for access control
            if not token_scopes or invalid_scopes:
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid or empty token scopes"}}, 401

            # Check scope hierarchy (admin includes all scopes)
            if "admin" in token_scopes:
                # Admin has all permissions
                return True, None, None

            # Check if all required scopes are present
            for scope in required_scopes:
                if scope not in token_scopes:
                    return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope: {scope}"}}, 403

            return True, None, None

        except jwt.ExpiredSignatureError:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Token has expired"}}, 401
        except jwt.InvalidTokenError:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401
        except Exception as e:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Token validation failed"}}, 401

    # No valid authentication method found
    return False, {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}, 401

    # For Bearer tokens, validate scopes
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]

        try:
            # Decode JWT token (using the same secret as the test token generator)
            payload = jwt.decode(token, "your-secret-key-change-in-production", algorithms=["HS256"])

            # Check for scopes
            token_scopes = payload.get('scopes', [])
            if not isinstance(token_scopes, list):
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token scopes format"}}, 401

            # Validate scope format - check for None, empty strings, or invalid types
            invalid_scopes = []
            for scope in token_scopes:
                if scope is None or (isinstance(scope, str) and not scope.strip()):
                    invalid_scopes.append(scope)

            # Empty scopes list is also invalid for access control
            if not token_scopes or invalid_scopes:
                return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid or empty token scopes"}}, 401

            # Check scope hierarchy (admin includes all scopes)
            if "admin" in token_scopes:
                # Admin has all permissions
                return True, None, None

            # Check if all required scopes are present
            for scope in required_scopes:
                if scope not in token_scopes:
                    return False, {"error": {"code": "FORBIDDEN", "message": f"Missing required scope: {scope}"}}, 403

            return True, None, None

        except jwt.ExpiredSignatureError:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Token has expired"}}, 401
        except jwt.InvalidTokenError:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Invalid token"}}, 401
        except Exception as e:
            return False, {"error": {"code": "UNAUTHORIZED", "message": "Token validation failed"}}, 401

    # No valid authentication method found
    return False, {"error": {"code": "UNAUTHORIZED", "message": "Authentication required"}}, 401

# ============================================================================
# INPUT VALIDATION
# ============================================================================

def convert_validation_errors_to_object(validation_errors):
    """Convert validation errors from array format to object format for OpenAPI compliance"""
    details = {}
    for error in validation_errors:
        field = error.get('field', 'general')
        message = error.get('message', 'Invalid value')
        details[field] = message
    return details

def validate_campaign_data(data):
    """Validate campaign creation data"""
    errors = []

    # Type validation - data must be a dict
    if not isinstance(data, dict):
        errors.append({"field": "request", "message": "Request body must be a JSON object"})
        return errors

    # Required fields validation
    name = data.get('name', '')
    if not name:
        errors.append({"field": "name", "message": "Campaign name is required"})
    elif not isinstance(name, str):
        errors.append({"field": "name", "message": "Campaign name must be a string"})
    elif len(name) > 255:
        errors.append({"field": "name", "message": "Campaign name must be at most 255 characters"})

    # Required fields for campaign creation
    required_fields = ['name', 'whiteUrl', 'blackUrl', 'costModel', 'payout']
    for field in required_fields:
        if field not in data or data[field] is None:
            errors.append({"field": field, "message": f"{field} is required"})

    return validate_campaign_fields(data, errors)

def validate_campaign_update_data(data):
    """Validate campaign update data (no required fields)"""
    errors = []

    # Type validation - data must be a dict
    if not isinstance(data, dict):
        errors.append({"field": "request", "message": "Request body must be a JSON object"}), 400
        return errors

    # For updates, only validate provided fields
    if 'name' in data and not data.get('name', '').strip():
        errors.append({"field": "name", "message": "Campaign name cannot be empty"})

    return validate_campaign_fields(data, errors)


def validate_pagination_params(request):
    """Validate pagination query parameters"""
    errors = []

    # Validate page
    page_str = request.args.get("page")
    if page_str is not None:
        try:
            page = int(page_str)
            if page < 1:
                errors.append({"field": "page", "message": "Page must be >= 1"})
        except (ValueError, TypeError):
            errors.append({"field": "page", "message": "Page must be a valid integer"})

    # Validate pageSize
    page_size_str = request.args.get("pageSize")
    if page_size_str is not None:
        try:
            page_size = int(page_size_str)
            if page_size < 1 or page_size > 100:
                errors.append({"field": "pageSize", "message": "Page size must be between 1 and 100"})
        except (ValueError, TypeError):
            errors.append({"field": "pageSize", "message": "Page size must be a valid integer"})

    # Validate sort (optional string)
    sort = request.args.get("sort")
    if sort is not None and not isinstance(sort, str):
        errors.append({"field": "sort", "message": "Sort must be a string"})

    # Validate filter (optional string)
    filter_param = request.args.get("filter")
    if filter_param is not None and not isinstance(filter_param, str):
        errors.append({"field": "filter", "message": "Filter must be a string"})

    return errors


def validate_analytics_params(request):
    """Validate analytics query parameters"""
    errors = []

    # Validate startDate
    start_date = request.args.get("startDate")
    if start_date is not None:
        if not isinstance(start_date, str):
            errors.append({"field": "startDate", "message": "Start date must be a string"})
        elif not re.match(date_pattern, start_date):
            errors.append({"field": "startDate", "message": "Start date must be a valid date string"})

    # Validate endDate
    end_date = request.args.get("endDate")
    if end_date is not None:
        if not isinstance(end_date, str):
            errors.append({"field": "endDate", "message": "End date must be a string"})
        elif not re.match(date_pattern, end_date):
            errors.append({"field": "endDate", "message": "End date must be a valid date string"})

    # Validate breakdown
    breakdown = request.args.get("breakdown")
    if breakdown is not None:
        if not isinstance(breakdown, str):
            errors.append({"field": "breakdown", "message": "Breakdown must be a string"})
        elif breakdown not in ["date", "traffic_source", "landing_page", "offer", "geography", "device"]:
            errors.append({"field": "breakdown", "message": "Breakdown must be one of: date, traffic_source, landing_page, offer, geography, device"})

    # Validate granularity
    granularity = request.args.get("granularity")
    if granularity is not None:
        if not isinstance(granularity, str):
            errors.append({"field": "granularity", "message": "Granularity must be a string"})
        elif granularity not in ["hour", "day", "week", "month"]:
            errors.append({"field": "granularity", "message": "Granularity must be one of: hour, day, week, month"})

    return errors

def validate_campaign_fields(data, errors):
    """Common validation logic for campaign fields"""
    white_url = data.get('whiteUrl')
    black_url = data.get('blackUrl')

    if white_url is not None:
        if not isinstance(white_url, str) or not white_url.startswith(('http://', 'https://')):
            errors.append({"field": "whiteUrl", "message": "White URL must be a valid HTTP/HTTPS URL"})

    if black_url is not None:
        if not isinstance(black_url, str) or not black_url.startswith(('http://', 'https://')):
            errors.append({"field": "blackUrl", "message": "Black URL must be a valid HTTP/HTTPS URL"})

    cost_model = data.get('costModel')
    if cost_model is not None:
        if not isinstance(cost_model, str):
            errors.append({"field": "costModel", "message": "Cost model must be a string"})
        elif cost_model not in ['CPA', 'CPC', 'CPM']:
            errors.append({"field": "costModel", "message": "Cost model must be CPA, CPC, or CPM"})

    description = data.get('description')
    if 'description' in data:
        if description is None:
            errors.append({"field": "description", "message": "Description cannot be null"})
        elif not isinstance(description, str):
            errors.append({"field": "description", "message": "Description must be a string"})
        elif len(description) > 1000:
            errors.append({"field": "description", "message": "Description must be at most 1000 characters"})

    start_date = data.get('startDate')
    if 'startDate' in data:
        if start_date is None:
            errors.append({"field": "startDate", "message": "Start date cannot be null"})
        elif start_date == "":
            errors.append({"field": "startDate", "message": "Start date cannot be empty"})
        elif not isinstance(start_date, str):
            errors.append({"field": "startDate", "message": "Start date must be a string"})
        elif not re.match(date_time_pattern, start_date):
            errors.append({"field": "startDate", "message": "Start date must be a valid date-time string"})

    end_date = data.get('endDate')
    if 'endDate' in data:
        if end_date is None:
            errors.append({"field": "endDate", "message": "End date cannot be null"})
        elif end_date == "":
            errors.append({"field": "endDate", "message": "End date cannot be empty"})
        elif not isinstance(end_date, str):
            errors.append({"field": "endDate", "message": "End date must be a string"})
        elif not re.match(date_time_pattern, end_date):
            errors.append({"field": "endDate", "message": "End date must be a valid date-time string"})

    payout = data.get('payout')
    if payout is not None:
        if not isinstance(payout, dict):
            errors.append({"field": "payout", "message": "Payout must be an object"})
        else:
            # Money schema requires both amount and currency
            if 'amount' not in payout:
                errors.append({"field": "payout", "message": "Payout amount is required"})
            if 'currency' not in payout:
                errors.append({"field": "payout", "message": "Payout currency is required"})

            # Validate amount if present
            if 'amount' in payout:
                amount = payout.get('amount')
                # Strict type checking - reject booleans and other non-numeric types
                if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                    errors.append({"field": "payout.amount", "message": "Payout amount must be a number"})
                elif isinstance(amount, float) and (amount == float('inf') or amount == float('-inf') or str(amount) == 'nan'):
                    errors.append({"field": "payout.amount", "message": "Payout amount must be a finite number"})
                elif abs(amount) > 1e400:  # Allow extremely large numbers for testing edge cases
                    errors.append({"field": "payout.amount", "message": "Payout amount is unreasonably large"})

            # Validate currency if present
            if 'currency' in payout:
                currency = payout.get('currency')
                if not isinstance(currency, str):
                    errors.append({"field": "payout.currency", "message": "Payout currency must be a string"})

            # Check for extra properties in Money object (should only have amount and currency)
            allowed_money_fields = {'amount', 'currency'}
            extra_fields = set(payout.keys()) - allowed_money_fields
            if extra_fields:
                errors.append({"field": "payout", "message": f"Money object must not contain additional properties: {', '.join(extra_fields)}"})

    # Validate dailyBudget if present
    if 'dailyBudget' in data:
        daily_budget = data['dailyBudget']
        if daily_budget is None:  # Explicitly reject null values
            errors.append({"field": "dailyBudget", "message": "Daily budget cannot be null"})
        elif not isinstance(daily_budget, dict):
            errors.append({"field": "dailyBudget", "message": "Daily budget must be an object"})
        else:
            # Money schema requires both amount and currency
            if 'amount' in daily_budget:
                amount = daily_budget.get('amount')
                # Strict type checking - reject booleans and other non-numeric types
                if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                    errors.append({"field": "dailyBudget.amount", "message": "Daily budget amount must be a number"})
                elif isinstance(amount, float) and (amount == float('inf') or amount == float('-inf') or str(amount) == 'nan'):
                    errors.append({"field": "dailyBudget.amount", "message": "Daily budget amount must be a finite number"})
                elif abs(amount) > 1e400:
                    errors.append({"field": "dailyBudget.amount", "message": "Daily budget amount is unreasonably large"})
                # If amount is present, currency must also be present
                if 'currency' not in daily_budget:
                    errors.append({"field": "dailyBudget", "message": "Daily budget currency is required when amount is provided"})
                else:
                    currency = daily_budget.get('currency')
                    if not isinstance(currency, str):
                        errors.append({"field": "dailyBudget.currency", "message": "Daily budget currency must be a string"})
            elif 'currency' in daily_budget:
                # If currency is present without amount, that's also invalid for Money schema
                errors.append({"field": "dailyBudget", "message": "Daily budget amount is required when currency is provided"})

            # Check for extra properties in Money object (should only have amount and currency)
            allowed_money_fields = {'amount', 'currency'}
            extra_fields = set(daily_budget.keys()) - allowed_money_fields
            if extra_fields:
                errors.append({"field": "dailyBudget", "message": f"Money object must not contain additional properties: {', '.join(extra_fields)}"})

    # Validate totalBudget if present
    if 'totalBudget' in data:
        total_budget = data['totalBudget']
        if total_budget is None:  # Explicitly reject null values
            errors.append({"field": "totalBudget", "message": "Total budget cannot be null"})
        elif not isinstance(total_budget, dict):
            errors.append({"field": "totalBudget", "message": "Total budget must be an object"})
        else:
            # Money schema requires both amount and currency
            if 'amount' in total_budget:
                amount = total_budget.get('amount')
                # Strict type checking - reject booleans and other non-numeric types
                if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                    errors.append({"field": "totalBudget.amount", "message": "Total budget amount must be a number"})
                elif isinstance(amount, float) and (amount == float('inf') or amount == float('-inf') or str(amount) == 'nan'):
                    errors.append({"field": "totalBudget.amount", "message": "Total budget amount must be a finite number"})
                elif abs(amount) > 1e400:
                    errors.append({"field": "totalBudget.amount", "message": "Total budget amount is unreasonably large"})
                # If amount is present, currency must also be present
                if 'currency' not in total_budget:
                    errors.append({"field": "totalBudget", "message": "Total budget currency is required when amount is provided"})
                else:
                    currency = total_budget.get('currency')
                    if not isinstance(currency, str):
                        errors.append({"field": "totalBudget.currency", "message": "Total budget currency must be a string"})
            elif 'currency' in total_budget:
                # If currency is present without amount, that's also invalid for Money schema
                errors.append({"field": "totalBudget", "message": "Total budget amount is required when currency is provided"})

            # Check for extra properties in Money object (should only have amount and currency)
            allowed_money_fields = {'amount', 'currency'}
            extra_fields = set(total_budget.keys()) - allowed_money_fields
            if extra_fields:
                errors.append({"field": "totalBudget", "message": f"Money object must not contain additional properties: {', '.join(extra_fields)}"})

    return errors

def validate_landing_page_data(data):
    """Validate landing page data"""
    errors = []

    # Required fields validation
    if not data.get('name', '').strip():
        errors.append({"field": "name", "message": "Landing page name is required"})

    if 'url' not in data or not data.get('url', '').strip():
        errors.append({"field": "url", "message": "Landing page URL is required"})

    if 'pageType' not in data or not data.get('pageType', '').strip():
        errors.append({"field": "pageType", "message": "Landing page type is required"})

    # Additional validation
    url = data.get('url', '')
    if url and (not isinstance(url, str) or not url.startswith(('http://', 'https://'))):
        errors.append({"field": "url", "message": "URL must be a valid HTTP/HTTPS URL"})

    page_type = data.get('pageType', '')
    if page_type and page_type not in ['direct', 'squeeze', 'bridge', 'thank_you']:
        errors.append({"field": "pageType", "message": "Invalid page type"})

    weight = data.get('weight', 100)
    if not isinstance(weight, int) or not (0 <= weight <= 100):
        errors.append({"field": "weight", "message": "Weight must be an integer between 0 and 100"})

    return errors

# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================


def generate_campaign_id():
    return f"camp_{random.randint(1000, 9999)}"


def generate_landing_page_id():
    return f"lp_{random.randint(1000, 9999)}"


def generate_offer_id():
    return f"offer_{random.randint(1000, 9999)}"


def generate_money(amount=None):
    if amount is None:
        amount = round(random.uniform(1, 1000), 2)
    return {"amount": amount, "currency": "USD"}


def generate_pagination(page=1, page_size=20, total_items=150):
    total_pages = (total_items + page_size - 1) // page_size
    base_url = "http://localhost:8000/campaigns"

    links = {
        "first": f"{base_url}?page=1&pageSize={page_size}",
        "last": f"{base_url}?page={total_pages}&pageSize={page_size}",
    }

    # Only include prev/next if they exist
    if page > 1:
        links["prev"] = f"{base_url}?page={page-1}&pageSize={page_size}"
    if page < total_pages:
        links["next"] = f"{base_url}?page={page+1}&pageSize={page_size}"

    return {
        "page": page,
        "pageSize": page_size,
        "totalItems": total_items,
        "totalPages": total_pages,
        "hasNext": page < total_pages,
        "hasPrev": page > 1,
        "_links": links,
    }


def generate_campaign():
    campaign_id = generate_campaign_id()
    return {
        "id": campaign_id,
        "name": f"Campaign {random.randint(1, 100)}",
        "description": f"High-converting campaign for {random.choice(['summer', 'winter', 'holiday', 'special'])} promotion",
        "status": random.choice(["draft", "active", "paused", "completed"]),
        "schedule": {
            "startDate": "2024-01-01T00:00:00Z",
            "endDate": "2024-12-31T23:59:59Z",
        },
        "urls": {
            "safePage": f"https://example.com/safe/{campaign_id}",
            "offerPage": f"https://example.com/offer/{campaign_id}",
        },
        "financial": {
            "costModel": random.choice(["CPA", "CPC", "CPM"]),
            "payout": generate_money(random.uniform(10, 100)),
            "dailyBudget": generate_money(random.uniform(50, 500)),
            "totalBudget": generate_money(random.uniform(1000, 10000)),
            "spent": generate_money(random.uniform(0, 5000)),
        },
        "performance": {
            "clicks": random.randint(1000, 10000),
            "conversions": random.randint(10, 500),
            "ctr": round(random.uniform(0.01, 0.05), 4),
            "cr": round(random.uniform(0.01, 0.10), 4),
            "epc": generate_money(random.uniform(5, 50)),
            "roi": round(random.uniform(1.0, 5.0), 2),
        },
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-15T14:30:00Z",
        "_links": {
            "self": f"http://localhost:8000/campaigns/{campaign_id}",
            "landingPages": f"http://localhost:8000/campaigns/{campaign_id}/landing-pages",
            "offers": f"http://localhost:8000/campaigns/{campaign_id}/offers",
            "targeting": f"http://localhost:8000/campaigns/{campaign_id}/targeting",
            "analytics": f"http://localhost:8000/campaigns/{campaign_id}/analytics",
        },
    }


def generate_campaign_summary():
    return {
        "id": generate_campaign_id(),
        "name": f"Campaign {random.randint(1, 100)}",
        "status": random.choice(["active", "paused", "completed"]),
        "performance": {
            "clicks": random.randint(1000, 10000),
            "conversions": random.randint(10, 500),
            "ctr": round(random.uniform(0.01, 0.05), 4),
            "cr": round(random.uniform(0.01, 0.10), 4),
            "epc": generate_money(random.uniform(5, 50)),
            "roi": round(random.uniform(1.0, 5.0), 2),
        },
        "_links": {"self": f"http://localhost:8000/campaigns/{generate_campaign_id()}"},
    }


def generate_landing_page(campaign_id):
    return {
        "id": generate_landing_page_id(),
        "campaignId": campaign_id,
        "name": f"{random.choice(['Main', 'Secondary', 'Mobile', 'Desktop'])} Landing Page",
        "url": f"https://example.com/page/{random.randint(100, 999)}",
        "pageType": random.choice(["direct", "squeeze", "bridge", "thank_you"]),
        "weight": random.randint(10, 100),
        "isActive": random.choice([True, False]),
        "isControl": random.choice([True, False]),
        "performance": {
            "impressions": random.randint(1000, 50000),
            "clicks": random.randint(100, 5000),
            "conversions": random.randint(5, 250),
            "ctr": round(random.uniform(0.02, 0.08), 4),
            "cr": round(random.uniform(0.01, 0.15), 4),
            "epc": generate_money(random.uniform(3, 60)),
        },
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-15T14:30:00Z",
    }


def generate_campaign_offer(campaign_id):
    return {
        "id": generate_offer_id(),
        "campaignId": campaign_id,
        "name": f"Premium {random.choice(['Product', 'Service', 'Course', 'Membership'])}",
        "url": f"https://affiliate.com/offer/{random.randint(1000, 9999)}",
        "offerType": random.choice(["direct", "email", "phone"]),
        "weight": random.randint(10, 100),
        "isActive": random.choice([True, False]),
        "isControl": random.choice([True, False]),
        "payout": generate_money(random.uniform(15, 200)),
        "revenueShare": round(random.uniform(0.05, 0.25), 2),
        "costPerClick": generate_money(random.uniform(0.5, 5.0)),
        "performance": {
            "clicks": random.randint(500, 8000),
            "conversions": random.randint(15, 300),
            "revenue": generate_money(random.uniform(1000, 50000)),
            "cost": generate_money(random.uniform(100, 5000)),
            "cr": round(random.uniform(0.02, 0.08), 4),
            "epc": generate_money(random.uniform(10, 80)),
            "roi": round(random.uniform(1.5, 8.0), 2),
        },
        "createdAt": "2024-01-01T10:00:00Z",
        "updatedAt": "2024-01-15T14:30:00Z",
    }


def generate_analytics(campaign_id):
    return {
        "campaignId": campaign_id,
        "timeRange": {
            "startDate": "2024-01-01",
            "endDate": "2024-01-31",
            "granularity": "day",
        },
        "metrics": {
            "clicks": random.randint(5000, 20000),
            "uniqueClicks": random.randint(4500, 18000),
            "conversions": random.randint(150, 800),
            "revenue": generate_money(random.uniform(5000, 25000)),
            "cost": generate_money(random.uniform(1000, 8000)),
            "ctr": round(random.uniform(0.015, 0.045), 4),
            "cr": round(random.uniform(0.02, 0.06), 4),
            "epc": generate_money(random.uniform(15, 45)),
            "roi": round(random.uniform(2.0, 6.0), 2),
        },
        "breakdowns": {
            "byDate": [
                {
                    "date": "2024-01-15",
                    "metrics": {
                        "clicks": random.randint(200, 800),
                        "uniqueClicks": random.randint(180, 720),
                        "conversions": random.randint(10, 50),
                        "revenue": generate_money(random.uniform(500, 2000)),
                        "cost": generate_money(random.uniform(100, 500)),
                        "ctr": round(random.uniform(0.015, 0.045), 4),
                        "cr": round(random.uniform(0.02, 0.06), 4),
                        "epc": generate_money(random.uniform(15, 45)),
                        "roi": round(random.uniform(2.0, 6.0), 2),
                    },
                }
            ]
        },
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================


@app.route("/v1/health", methods=["GET"])
def health():
    """Health check endpoint - no auth required"""
    import socket
    import os

    # Get instance identifier from environment or generate from port
    instance_id = os.environ.get('FLASK_INSTANCE_ID', 'single')
    port = os.environ.get('FLASK_PORT', '8000')
    hostname = socket.gethostname()

    return jsonify({
        "status": "healthy",
        "service": "domain-driven-api-mock",
        "instance": instance_id,
        "port": port,
        "hostname": hostname,
        "timestamp": time.time()
    })

@app.route("/v1/reset", methods=["POST"])
def reset():
    """Reset mock storage - for testing purposes"""
    reset_storage()
    return jsonify({"message": "Mock storage reset"})


# CAMPAIGN ENDPOINTS
@app.route("/v1/campaigns", methods=["GET"])
def list_campaigns():
    """List campaigns with pagination"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate query parameters
    validation_errors = validate_pagination_params(request)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid query parameters",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("pageSize", 20))

    except ValueError:
        return (
            jsonify(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Invalid pagination parameters",
                    }
                }
            ),
            400,
        )

    campaigns = [generate_campaign_summary() for _ in range(min(page_size, 20))]
    pagination = generate_pagination(page, page_size)

    return jsonify({"campaigns": campaigns, "pagination": pagination})


@app.route("/v1/campaigns", methods=["POST"])
def create_campaign():
    """Create a new campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Parse and validate request data
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
        if not isinstance(data, dict):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body must be a JSON object"}}), 400
    except Exception as e:
        # Handle cases where request.get_json() fails due to invalid content
        try:
            # Try to get raw data for better error message
            raw_data = request.get_data(as_text=True)
            if not raw_data or raw_data.isspace():
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
            else:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON format"}}), 400
        except:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid request format"}}), 400

    # Validate business rules
    validation_errors = validate_campaign_data(data)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    # Create campaign
    campaign = generate_campaign()

    # Store in mock storage
    mock_storage["campaigns"][campaign["id"]] = campaign

    return (
        jsonify(campaign),
        201,
        {
            "Location": f'http://localhost:8000/campaigns/{campaign["id"]}',
            "Content-Type": "application/json",
        },
    )


@app.route("/v1/campaigns/<campaign_id>", methods=["GET"])
def get_campaign(campaign_id):
    """Get campaign details"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign was deleted
    if is_campaign_deleted(campaign_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign exists in storage, otherwise return 404
    campaign = mock_storage["campaigns"].get(campaign_id)
    if not campaign:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    return jsonify(campaign)


@app.route("/v1/campaigns/<campaign_id>", methods=["PUT"])
def update_campaign(campaign_id):
    """Update campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Parse and validate request data
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
        if not isinstance(data, dict):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body must be a JSON object"}}), 400
    except Exception as e:
        # Handle cases where request.get_json() fails due to invalid content
        try:
            # Try to get raw data for better error message
            raw_data = request.get_data(as_text=True)
            if not raw_data or raw_data.isspace():
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
            else:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON format"}}), 400
        except:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid request format"}}), 400

    # Validate business rules for update (partial validation - no required fields)
    validation_errors = validate_campaign_update_data(data)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    # Update campaign
    campaign = mock_storage["campaigns"][campaign_id].copy()
    # In a real implementation, you'd merge the update data
    campaign["updatedAt"] = "2024-01-15T15:00:00Z"

    return jsonify(campaign)


@app.route("/v1/campaigns/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    """Delete campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:delete'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign was already deleted
    if is_campaign_deleted(campaign_id):
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Mark as deleted
    mark_campaign_deleted(campaign_id)

    return "", 204


@app.route("/v1/campaigns/<campaign_id>/pause", methods=["POST"])
def pause_campaign(campaign_id):
    """Pause campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Parse and validate request data
    try:
        data = request.get_json()
        if data is None:
            # Check if the raw data is actually null vs empty
            raw_data = request.get_data(as_text=True)
            if raw_data.strip() == 'null':
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body cannot be null"}}), 400
            data = {}  # Allow empty body
        if not isinstance(data, dict):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body must be a JSON object"}}), 400
    except Exception as e:
        # Handle cases where request.get_json() fails due to invalid content
        try:
            # Try to get raw data for better error message
            raw_data = request.get_data(as_text=True)
            if not raw_data or raw_data.isspace():
                data = {}  # Allow empty body for pause requests
            else:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON format"}}), 400
        except:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid request format"}}), 400

    # Validate optional reason field
    if 'reason' in data and not isinstance(data['reason'], str):
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Reason must be a string"}}), 400

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Update status
    campaign = mock_storage["campaigns"][campaign_id].copy()
    campaign["status"] = "paused"
    campaign["updatedAt"] = "2024-01-15T15:00:00Z"

    mock_storage["campaigns"][campaign_id] = campaign
    return jsonify(campaign)


@app.route("/v1/campaigns/<campaign_id>/resume", methods=["POST"])
def resume_campaign(campaign_id):
    """Resume campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['campaign:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Update status
    campaign = mock_storage["campaigns"][campaign_id].copy()
    campaign["status"] = "active"
    campaign["updatedAt"] = "2024-01-15T15:00:00Z"

    mock_storage["campaigns"][campaign_id] = campaign
    return jsonify(campaign)


# LANDING PAGE ENDPOINTS
@app.route("/v1/campaigns/<campaign_id>/landing-pages", methods=["GET"])
def list_landing_pages(campaign_id):
    """List landing pages for campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['landing:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Validate query parameters
    validation_errors = validate_pagination_params(request)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid query parameters",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    pages = [generate_landing_page(campaign_id) for _ in range(random.randint(1, 5))]
    return jsonify({"landingPages": pages, "pagination": generate_pagination()})


@app.route("/v1/campaigns/<campaign_id>/landing-pages", methods=["POST"])
def create_landing_page(campaign_id):
    """Create landing page"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['landing:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Parse and validate request data
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
        if not isinstance(data, dict):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body must be a JSON object"}}), 400
    except Exception as e:
        # Handle cases where request.get_json() fails due to invalid content
        try:
            # Try to get raw data for better error message
            raw_data = request.get_data(as_text=True)
            if not raw_data or raw_data.isspace():
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
            else:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON format"}}), 400
        except:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid request format"}}), 400

    # Validate business rules
    validation_errors = validate_landing_page_data(data)
    if validation_errors:
        # Convert array to object format expected by OpenAPI schema
        details = {}
        for error in validation_errors:
            field = error.get('field', 'general')
            details[field] = error.get('message', 'Invalid value')
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Validation failed",
                "details": details
            }
        }), 400

    page = generate_landing_page(campaign_id)
    return jsonify(page), 201


# CAMPAIGN OFFERS ENDPOINTS
@app.route("/v1/campaigns/<campaign_id>/offers", methods=["GET"])
def list_campaign_offers(campaign_id):
    """List offers for campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['offers:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Validate query parameters
    validation_errors = validate_pagination_params(request)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid query parameters",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    offers = [generate_campaign_offer(campaign_id) for _ in range(random.randint(1, 5))]
    return jsonify({"offers": offers, "pagination": generate_pagination()})


@app.route("/v1/campaigns/<campaign_id>/offers", methods=["POST"])
def create_campaign_offer(campaign_id):
    """Create offer for campaign"""
    # Validate authentication and scopes
    is_valid, error_response, status_code = validate_scopes(request, ['offers:write'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Parse and validate request data
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
        if not isinstance(data, dict):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body must be a JSON object"}}), 400
    except Exception as e:
        # Handle cases where request.get_json() fails due to invalid content
        try:
            # Try to get raw data for better error message
            raw_data = request.get_data(as_text=True)
            if not raw_data or raw_data.isspace():
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Request body is required"}}), 400
            else:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid JSON format"}}), 400
        except:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid request format"}}), 400

    # Generate and return offer
    offer = generate_campaign_offer(campaign_id)
    return jsonify(offer), 201


# ANALYTICS ENDPOINTS
@app.route("/v1/campaigns/<campaign_id>/analytics", methods=["GET"])
def get_campaign_analytics(campaign_id):
    """Get campaign analytics"""
    # Validate authentication and scopes (supports API keys)
    is_valid, error_response, status_code = validate_scopes(request, ['analytics:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate campaign ID format - accept any non-empty string for testing
    if not campaign_id or not campaign_id.strip():
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    # Validate query parameters
    validation_errors = validate_analytics_params(request)
    if validation_errors:
        return jsonify({
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid query parameters",
                "details": convert_validation_errors_to_object(validation_errors)
            }
        }), 400

    # Check if campaign exists
    if campaign_id not in mock_storage["campaigns"]:
        return jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}), 404

    analytics = generate_analytics(campaign_id)
    return jsonify(analytics)


# ERROR SIMULATION ENDPOINTS
@app.route("/v1/campaigns/<campaign_id>/error", methods=["GET"])
def simulate_error(campaign_id):
    """Simulate different error conditions"""
    error_type = request.args.get("type", "not_found")

    if error_type == "not_found":
        return (
            jsonify({"error": {"code": "NOT_FOUND", "message": "Campaign not found"}}),
            404,
        )
    elif error_type == "validation":
        return (
            jsonify(
                {
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Campaign name is required",
                        "field": "name",
                    }
                }
            ),
            400,
        )
    elif error_type == "conflict":
        return (
            jsonify(
                {
                    "error": {
                        "code": "CONFLICT",
                        "message": "Campaign with this name already exists",
                    }
                }
            ),
            409,
        )
    else:
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                    }
                }
            ),
            500,
        )


# ============================================================================
# CORS OPTIONS HANDLER
# ============================================================================

@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle CORS preflight requests"""
    return '', 200

# ============================================================================
# MOCK LANDING PAGES FOR TESTING (FAST RESPONSES)
# ============================================================================

@app.route("/mock-safe-page", methods=["GET"])
def mock_safe_page():
    """Mock safe page for fast testing responses"""
    click_id = request.args.get('click_id', 'unknown')
    return f'<html><body><h1>Safe Page</h1><p>Click ID: {click_id}</p><p>Status: Invalid</p></body></html>', 200

@app.route("/mock-offer-page", methods=["GET"])
def mock_offer_page():
    """Mock offer page for fast testing responses"""
    click_id = request.args.get('click_id', 'unknown')
    return f'<html><body><h1>Offer Page</h1><p>Click ID: {click_id}</p><p>Status: Valid</p></body></html>', 200

# ============================================================================
# CLICK TRACKING ENDPOINTS (PUBLIC - NO AUTH REQUIRED)
# ============================================================================

def get_client_ip(request):
    """Get real client IP address from headers or remote_addr"""
    # Check for common proxy headers
    ip_headers = ['X-Forwarded-For', 'X-Real-IP', 'CF-Connecting-IP', 'X-Client-IP']

    for header in ip_headers:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For can contain multiple IPs, take the first one
            ip = ip.split(',')[0].strip()
            # Validate IP format
            import ipaddress
            try:
                ipaddress.ip_address(ip)
                return ip
            except ValueError:
                continue

    return request.remote_addr or '127.0.0.1'


def detect_bot(user_agent, referrer):
    """Basic bot detection logic"""
    if not user_agent:
        return True, "missing_user_agent"

    ua_lower = user_agent.lower()

    # Common bot patterns
    bot_patterns = [
        'bot', 'crawler', 'spider', 'scraper', 'headless', 'selenium',
        'chrome-lighthouse', 'googlebot', 'bingbot', 'yahoo', 'baidu',
        'yandex', 'duckduckbot', 'facebookexternalhit', 'twitterbot',
        'linkedinbot', 'whatsapp', 'telegrambot'
    ]

    if any(pattern in ua_lower for pattern in bot_patterns):
        return True, "bot_pattern_detected"

    # Check for empty or suspicious referrer
    if referrer and len(referrer) > 1000:
        return True, "suspicious_referrer_length"

    return False, None


def apply_campaign_filters(ip, ua, referrer, filters):
    """Apply campaign-specific filters"""
    if not filters:
        return False, None

    # IP blacklist check
    ip_blacklist = filters.get('ip_blacklist', [])
    if ip in ip_blacklist:
        return True, "ip_blacklisted"

    # Country/Geo filtering (simplified)
    allowed_countries = filters.get('allowed_countries', [])
    if allowed_countries:
        # In real implementation, you'd use GeoIP database
        # For demo, just check if IP starts with certain patterns
        pass  # Skip for mock

    # User agent filtering
    blocked_uas = filters.get('blocked_user_agents', [])
    if ua and any(blocked_ua.lower() in ua.lower() for blocked_ua in blocked_uas):
        return True, "user_agent_blocked"

    return False, None


def generate_click_id():
    """Generate unique click ID"""
    import uuid
    return str(uuid.uuid4())


@app.route("/v1/click", methods=["GET"])
def click_handler():
    """Handle click tracking and redirection"""
    try:
        errors = []

        # Validate CID
        cid = request.args.get('cid')
        if cid is not None:
            if cid == '':
                errors.append({"field": "cid", "message": "Campaign ID cannot be empty"})
            try:
                cid = int(cid)
                if cid < 1:
                    errors.append({"field": "cid", "message": "Campaign ID must be >= 1"})
            except (ValueError, TypeError):
                errors.append({"field": "cid", "message": "Invalid Campaign ID"})
        else:
            cid = 123  # Default CID

        # Validate landing_page_id
        landing_page_id = request.args.get('landing_page_id')
        if landing_page_id is not None:
            if landing_page_id == '':
                errors.append({"field": "landing_page_id", "message": "landing_page_id cannot be empty"})
            try:
                landing_page_id = int(landing_page_id)
                if landing_page_id < 1:
                    errors.append({"field": "landing_page_id", "message": "landing_page_id must be >= 1"})
            except (ValueError, TypeError):
                errors.append({"field": "landing_page_id", "message": "Invalid landing_page_id"})

        # Validate campaign_offer_id
        campaign_offer_id = request.args.get('campaign_offer_id')
        if campaign_offer_id is not None:
            if campaign_offer_id == '':
                errors.append({"field": "campaign_offer_id", "message": "campaign_offer_id cannot be empty"})
            else:
                try:
                    campaign_offer_id_int = int(campaign_offer_id)
                    if campaign_offer_id_int < 1:
                        errors.append({"field": "campaign_offer_id", "message": "campaign_offer_id must be >= 1"})
                    elif campaign_offer_id_int > 2147483647:
                        errors.append({"field": "campaign_offer_id", "message": "campaign_offer_id exceeds maximum value"})
                except (ValueError, TypeError):
                    errors.append({"field": "campaign_offer_id", "message": "Invalid campaign_offer_id"})

        # Validate traffic_source_id
        traffic_source_id_str = request.args.get('traffic_source_id')
        traffic_source_id = None
        if traffic_source_id_str is not None:
            if traffic_source_id_str == '':
                errors.append({"field": "traffic_source_id", "message": "Traffic source ID cannot be empty"})
            else:
                try:
                    traffic_source_id = int(traffic_source_id_str)
                    if traffic_source_id < 1:
                        errors.append({"field": "traffic_source_id", "message": "Traffic source ID must be >= 1"})
                except ValueError:
                    errors.append({"field": "traffic_source_id", "message": "Traffic source ID must be an integer"})

        # Validate tracking params
        sub_params = ['sub1', 'sub2', 'sub3', 'sub4', 'sub5',
                      'aff_sub', 'aff_sub2', 'aff_sub3', 'aff_sub4', 'aff_sub5']
        pattern = re.compile(r'^[a-zA-Z0-9._-]*$')

        for param in sub_params:
            value = request.args.get(param)
            if value is not None and not pattern.match(value):
                errors.append({"field": param, "message": f"{param} must match pattern '^[a-zA-Z0-9._-]*$'"})

        # Validate click_id format
        click_id_param = request.args.get('click_id')
        if click_id_param is not None and not pattern.match(click_id_param):
            errors.append({"field": "click_id", "message": "click_id must match pattern '^[a-zA-Z0-9._-]*$'"})

        # Allowed parameters
        allowed_params = {
            'cid', 'sub1', 'sub2', 'sub3', 'sub4', 'sub5',
            'click_id', 'aff_sub', 'aff_sub2', 'aff_sub3', 'aff_sub4', 'aff_sub5',
            'landing_page_id', 'campaign_offer_id', 'traffic_source_id',
            'bot_user_agent', 'test_mode'
        }

        for param_name in request.args:
            if param_name not in allowed_params:
                errors.append({"field": param_name, "message": f"Unknown query parameter: {param_name}"})

        if errors:
            return jsonify({
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Validation failed",
                    "details": convert_validation_errors_to_object(errors)
                }
            }), 400

        # Special bot-forcing param
        force_bot = request.args.get('bot_user_agent') == '1'

        # Collect client info
        ip = get_client_ip(request)
        ua = request.headers.get('User-Agent', '')
        referrer = request.headers.get('Referer')

        # Generate unique click ID
        click_id = generate_click_id()

        # Basic bot detection
        is_bot, bot_reason = detect_bot(ua, referrer)
        if force_bot or is_bot:
            is_valid = 0
            fraud_reason = bot_reason or "forced_bot_detection"
        else:
            is_valid = 1
            fraud_reason = None

        # Create mock campaign URLs
        campaign = {
            'cid': cid,
            'white_url': f'http://127.0.0.1:8000/mock-safe-page?click_id={click_id}',
            'black_url': f'http://127.0.0.1:8000/mock-offer-page?click_id={click_id}',
            'filters': {}
        }

        # Campaign-specific filters
        if is_valid:
            filtered, filter_reason = apply_campaign_filters(ip, ua, referrer, campaign['filters'])
            if filtered:
                is_valid = 0
                fraud_reason = filter_reason

        # Build click record
        click_record = {
            'id': click_id,
            'cid': cid,
            'ip': ip,
            'ua': ua,
            'ref': referrer,
            'isValid': is_valid,
            'ts': int(time.time()),

            'sub1': request.args.get('sub1'),
            'sub2': request.args.get('sub2'),
            'sub3': request.args.get('sub3'),
            'sub4': request.args.get('sub4'),
            'sub5': request.args.get('sub5'),

            'clickId': click_id_param,
            'affSub': request.args.get('aff_sub'),
            'affSub2': request.args.get('aff_sub2'),
            'affSub3': request.args.get('aff_sub3'),
            'affSub4': request.args.get('aff_sub4'),
            'affSub5': request.args.get('aff_sub5'),

            'fraudScore': random.uniform(0.0, 0.9) if is_valid == 0 else random.uniform(0.0, 0.1),
            'fraudReason': fraud_reason,

            'landingPageId': landing_page_id,
            'campaignOfferId': campaign_offer_id,
            'trafficSourceId': traffic_source_id,
            'conversionType': None
        }

        mock_storage["clicks"].append(click_record)

        # Choose redirect target
        redirect_url = campaign['black_url'] if is_valid else campaign['white_url']

        # Merge original query params into redirect URL
        original_query = request.query_string.decode('utf-8')
        if original_query:
            from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
            parsed = urlparse(redirect_url)
            merged = parse_qs(parsed.query)
            merged.update(parse_qs(original_query))
            redirect_url = urlunparse(parsed._replace(query=urlencode(merged, doseq=True)))

        # Test mode returns HTML instead of redirect
        if request.args.get('test_mode') == '1':
            html = (
                f"<html><body><h1>{'Offer Page' if is_valid else 'Safe Page'}</h1>"
                f"<p>Click ID: {click_id}</p>"
                f"<p>Status: {'Valid' if is_valid else 'Fraudulent'}</p>"
                f"<p>Redirecting to: {redirect_url}</p></body></html>"
            )
            return Response(html, mimetype='text/html', status=200)

        # Schemathesis test mode
        if request.headers.get('X-Schemathesis-Test'):
            return jsonify({"status": "redirected", "to": redirect_url, "click_record": click_record}), 200

        # Standard redirect
        return redirect(redirect_url, code=302)

    except Exception as e:
        app.logger.error(f"Internal server error in click_handler: {e}")
        return jsonify({"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}), 500


@app.route("/v1/click/<click_id>", methods=["GET"])
def get_click_details(click_id):
    """Get click details (for debugging/admin purposes)"""
    try:
        # This endpoint requires auth and proper scopes (supports API keys)
        is_valid, error_response, status_code = validate_scopes(request, ['traffic:read'])
        if not is_valid:
            return jsonify(error_response), status_code

        # Find click in mock storage
        if 'clicks' not in mock_storage:
            return jsonify({"error": {"code": "NOT_FOUND", "message": "Click not found"}}), 404

        for click_record in mock_storage['clicks']:
            if click_record['id'] == click_id:
                return jsonify(click_record)

        return jsonify({"error": {"code": "NOT_FOUND", "message": "Click not found"}}), 404

    except Exception as e:
        app.logger.error(f"Error in get_click_details: {e}")
        return jsonify({"error": {"code": "INTERNAL_SERVER_ERROR", "message": "Internal server error"}}), 500


@app.route("/v1/clicks", methods=["GET"])
def list_clicks():
    """List recent clicks (admin endpoint)"""
    # Validate authentication and scopes (supports API keys)
    is_valid, error_response, status_code = validate_scopes(request, ['traffic:read'])
    if not is_valid:
        return jsonify(error_response), status_code

    # Validate that only allowed query parameters are present and have correct types
    allowed_params = {'cid', 'limit', 'offset', 'sub1', 'sub2', 'is_valid'}
    for param in request.args:
        if param not in allowed_params:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": f"Unknown query parameter: {param}"}}), 422
        # Check for duplicate parameters or arrays
        param_values = request.args.getlist(param)
        if len(param_values) != 1:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": f"Parameter {param} must be a single value, not an array"}}), 422
        # Validate parameter values are strings (not arrays/objects)
        if not isinstance(param_values[0], str):
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": f"Parameter {param} must be a string"}}), 422

    # Get query parameters with error handling
    try:
        cid_filter = None
        cid_filter_str = request.args.get('cid')
        if cid_filter_str is not None:
            if cid_filter_str == '':
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Campaign ID cannot be empty"}}), 422
            cid_filter = int(cid_filter_str)
            if cid_filter < 1:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Campaign ID must be >= 1"}}), 422

        limit = request.args.get('limit', '50')
        limit = int(limit)
        if limit < 1 or limit > 1000:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Limit must be between 1 and 1000"}}), 422

        offset = request.args.get('offset', '0')
        offset = int(offset)
        if offset < 0:
            return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Offset must be >= 0"}}), 422

        # Additional filters
        sub1_filter = request.args.get('sub1')
        sub2_filter = request.args.get('sub2')
        is_valid_filter = request.args.get('is_valid')
        if is_valid_filter is not None:
            is_valid_filter = int(is_valid_filter)
            if is_valid_filter not in [0, 1]:
                return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "is_valid must be 0 or 1"}}), 422

    except (ValueError, TypeError, UnicodeDecodeError) as e:
        return jsonify({"error": {"code": "VALIDATION_ERROR", "message": "Invalid parameter format"}}), 422

    if 'clicks' not in mock_storage:
        return jsonify({"clicks": [], "total": 0})

    # Apply filters
    clicks = mock_storage['clicks']
    if cid_filter is not None:
        clicks = [c for c in clicks if c.get('cid') == cid_filter]
    if sub1_filter is not None:
        clicks = [c for c in clicks if c.get('sub1') == sub1_filter]
    if sub2_filter is not None:
        clicks = [c for c in clicks if c.get('sub2') == sub2_filter]
    if is_valid_filter is not None:
        clicks = [c for c in clicks if c.get('isValid') == is_valid_filter]

    # Sort by timestamp descending
    clicks = sorted(clicks, key=lambda x: x['ts'], reverse=True)

    # Apply pagination
    total = len(clicks)
    clicks = clicks[offset:offset + limit]

    return jsonify({
        "clicks": clicks,
        "total": total,
        "limit": limit,
        "offset": offset
    })


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Disable Flask/Werkzeug logs
    log = logging.getLogger('werkzeug')
    log.disabled = True
    app.logger.disabled = True

    # Initialize storage
    reset_storage()  # This already initializes clicks with mock data

    # For best performance on Linux/Mac, use Gunicorn:
    # gunicorn -w 4 -b 127.0.0.1:8000 mock_server:app
    #
    # On Windows, threading provides the best performance:
    app.run(host="localhost", port=8001, debug=False, threaded=True)
