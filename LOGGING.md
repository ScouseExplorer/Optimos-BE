# Logging Configuration

This backend uses structured logging with both console and JSON file outputs for production-ready monitoring.

## Features

- **Structured Logging**: JSON format for easy parsing in production environments
- **Rotating File Handlers**: Automatic log rotation to prevent disk overflow
- **Request Logging**: Automatic HTTP request/response logging via middleware
- **Error Tracking**: Dedicated error log file for quick troubleshooting
- **Request ID Tracing**: Unique request IDs for distributed tracing

## Log Files

All logs are stored in the `logs/` directory:

- `logs/app.log` - All application events (rotated at 10MB)
- `logs/error.log` - Only ERROR level events (rotated at 10MB)

Each file keeps up to 10 backups before being deleted.

## Log Format

### Console Output (Human-Readable)
```
2024-01-15 10:30:45,123 - app.services.user_service - INFO - User created successfully
```

### File Output (JSON)
```json
{
  "asctime": "2024-01-15 10:30:45,123",
  "name": "app.services.user_service",
  "levelname": "INFO",
  "message": "User created successfully",
  "user_id": 42,
  "email": "user@example.com",
  "event": "user_created"
}
```

## Events Tracked

### Authentication
- `user_created` - New user registration
- `user_authenticated` - Successful login
- `login_failed_user_not_found` - Login attempt with non-existent user
- `login_failed_wrong_password` - Login attempt with wrong password

### Email Verification
- `email_verified` - Email successfully verified
- `email_verification_failed_invalid_token` - Invalid verification token
- `email_verification_error` - Error during verification

### Password Reset
- `password_reset_successful` - Password reset completed
- `password_reset_failed_invalid_token` - Invalid reset token
- `password_reset_failed_expired_token` - Expired reset token

### HTTP Requests
- `request_started` - Request began processing
- `request_completed` - Request finished with status code
- `request_error` - Unhandled error during request
- `error_response` - 4xx or 5xx response returned

## Using Logging in Your Code

### Get a Logger
```python
import logging
from app.core.logging import get_logger

logger = get_logger(__name__)
```

### Log Events with Context
```python
logger.info(
    "User action completed",
    extra={
        "user_id": user.id,
        "action": "profile_updated",
        "event": "profile_updated"
    }
)
```

### Log Errors with Stack Trace
```python
try:
    # risky operation
except Exception as e:
    logger.error(
        f"Operation failed: {str(e)}",
        extra={
            "user_id": user_id,
            "event": "operation_failed",
            "error": str(e)
        },
        exc_info=True  # Includes full stack trace
    )
```

## Integration with Monitoring Tools

### Sentry (Error Tracking)
To add Sentry, install and configure:
```bash
pip install sentry-sdk
```

See `app/core/logging.py` and add Sentry initialization there.

### ELK Stack (Elasticsearch, Logstash, Kibana)
The JSON log format is perfect for ELK. Point Logstash to `logs/app.log` for centralized log aggregation.

### CloudWatch / DataDog
Forward `logs/app.log` to your cloud logging service for analysis.

## Request Tracing

Every HTTP request includes a unique `X-Request-ID` header:

**Request:**
```
GET /api/users/me
X-Request-ID: 1234567890.123
```

**Response:**
```
200 OK
X-Request-ID: 1234567890.123
```

Use this ID to correlate logs across requests in your logging dashboard.

## Configuration

Edit `app/core/logging.py` to customize:
- Log level (DEBUG, INFO, WARNING, ERROR)
- File rotation size (currently 10MB)
- Number of backup files (currently 10)
- Log format and fields
- Third-party logger levels (SQLAlchemy, uvicorn, etc.)

## Log Levels

- **DEBUG** - Detailed diagnostic info
- **INFO** - General informational messages (default level)
- **WARNING** - Warning messages for suspicious activity
- **ERROR** - Error messages that need attention
- **CRITICAL** - Critical errors that may crash the application
