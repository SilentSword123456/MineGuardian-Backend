# Authentication API

> **Source:** `services/auth.py`

---

## Endpoints

### `POST /login`

- **Purpose:** Authenticate a user and return a JWT access token.
- **Request body:** `{ "user_id": "<username>", "password": "<plaintext>" }`
- **Responses:**

| Status | Condition          | Body                              |
|--------|--------------------|-----------------------------------|
| 200    | Credentials valid  | `{ "access_token": "<JWT>" }`     |
| 400    | Missing `user_id` or `password` | `{ "message": "Missing user_id or password" }` |
| 401    | Invalid credentials | `{ "message": "Invalid credentials" }` |

- **Extras:** Uses `UserRepository.verify` for credential check; uses `UserRepository.getUserId` to embed the user's numeric ID in the JWT identity claim.

---

[← Back to Home](Home.md)
