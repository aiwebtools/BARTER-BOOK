# Auth Testing Playbook (Emergent Google OAuth + JWT)

## Test user creation via mongosh
```bash
mongosh --eval "
use('test_database');
var userId = 'user_' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  display_name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  auth_provider: 'google',
  created_at: new Date().toISOString(),
  city: 'San Francisco',
  state: 'CA',
  country: 'USA',
  approx_lat: 37.7749,
  approx_lng: -122.4194,
  reputation_score: 0,
  successful_trades: 0,
  email_verified: true
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Backend API test
```bash
curl -X GET "$REACT_APP_BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Browser test
Use playwright add_cookies with `session_token` value obtained from `db.user_sessions`.
