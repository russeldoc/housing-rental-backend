# 🏠 HomeRent API — Backend

REST API backend for the **HomeRent** rental platform. Built with **FastAPI**, **SQLAlchemy** and **PostgreSQL**, it handles user authentication, property listings, rental requests and admin management.

---

## 🔗 Live Links

| | URL |
|---|---|
| **API Base URL** | https://home-rental-api-jr53.onrender.com |
| **Swagger Docs (Live)** | https://home-rental-api-jr53.onrender.com/docs |
| **ReDoc (Live)** | https://home-rental-api-jr53.onrender.com/redoc |
| **Health Check** | https://home-rental-api-jr53.onrender.com/health |

> Open the Swagger Docs link to test every endpoint directly from the browser.

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Server | Uvicorn |
| ORM | SQLAlchemy 2.x |
| Database | PostgreSQL (psycopg 3) |
| Validation | Pydantic v2 |
| Auth | JWT (PyJWT, HS256) + Access/Refresh tokens |
| Password Hashing | pwdlib (Bcrypt + Argon2) |
| Env Files | python-dotenv |
| Docs | OpenAPI / Swagger UI / ReDoc |

---

## 📁 Project Structure

```
backend/
├── main.py             # App entry point, CORS, routers, / and /health
├── database.py         # Engine, SessionLocal, Base, get_db()
├── models.py           # SQLAlchemy models (User, Property, RentalRequest)
├── schemas.py          # Pydantic request/response schemas
├── auth.py             # Register, login, refresh, reset password, JWT logic
├── properties.py       # Property CRUD + search/filter/pagination
├── rental_requests.py  # Tenant requests + admin approve/reject
├── users.py            # Profile + admin user management
├── test_db.py          # DB connection test script
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variable template
└── .gitignore
```

---

## ⚙️ Step-by-Step Local Setup

### Step 1 — Prerequisites

Make sure these are installed:

- **Python 3.10+** → https://www.python.org/downloads/
- **PostgreSQL** → https://www.postgresql.org/download/
- **Git** → https://git-scm.com/downloads

Verify:

```bash
python --version
psql --version
git --version
```

### Step 2 — Clone the Repository

```bash
git clone https://github.com/russeldoc/housing-rental-backend.git
cd housing-rental-backend
```

### Step 3 — Create a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 4 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Create the PostgreSQL Database

```bash
psql -U postgres
```

```sql
CREATE DATABASE homerent_db;
\q
```

### Step 6 — Configure Environment Variables

Copy the example env file:

```bash
copy .env.example .env      # Windows
# cp .env.example .env      # macOS / Linux
```

Then edit `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/homerent_db
SECRET_KEY=generate_a_long_random_string_here
```

> 🔑 Generate a strong `SECRET_KEY` with:
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```
> `SECRET_KEY` and `DATABASE_URL` are **required** — the app raises an error if they are missing.

### Step 7 — Run the Server

```bash
uvicorn main:app --reload
```

The API starts at **http://127.0.0.1:8000**.

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

> Tables are created automatically on startup (`Base.metadata.create_all`), so no manual migration step is needed.

### Step 8 — Verify It Works

Open http://127.0.0.1:8000/health — you should see:

```json
{ "status": "healthy", "database": "connected" }
```

You can also run the quick DB test:

```bash
python test_db.py
```

---

## 🔐 Authentication Flow

1. **Register** a tenant account → `POST /auth/register`
2. **Login** → `POST /auth/login` returns:
   - `access_token` — valid for **30 minutes**
   - `refresh_token` — valid for **7 days**
3. Send the access token on protected routes:
   ```
   Authorization: Bearer <access_token>
   ```
4. When the access token expires, call `POST /auth/refresh` with the refresh token to get a new one.

**Roles:** `tenant` (default on registration) and `admin` (assigned directly in the database).

---

## 📖 API Endpoints

### 🌐 General

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | Public | Welcome message |
| GET | `/health` | Public | Health + DB connectivity check |

### 👤 Authentication — `/auth`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register a tenant (requires National ID **or** Passport) |
| POST | `/auth/login` | Public | Login → access + refresh tokens |
| POST | `/auth/refresh` | Public | Get a new access token |
| POST | `/auth/forgot-password` | Public | Generate a password-reset token (dev mode) |
| POST | `/auth/reset-password` | Public | Reset password using the reset token |
| GET | `/auth/me` | Bearer | Current logged-in user |

### 🏡 Properties — `/properties`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/properties/` | Public | List properties (search, filter, sort, paginate) |
| GET | `/properties/{id}` | Public | Get a single available property |
| POST | `/properties/` | Admin | Create a property |
| PUT | `/properties/{id}` | Admin | Update a property |
| DELETE | `/properties/{id}` | Admin | Delete a property (blocked if it has requests) |

**Query parameters for `GET /properties/`:**

| Param | Type | Default | Notes |
|---|---|---|---|
| `search` | string | – | Matches title or location (case-insensitive) |
| `property_id` | int | – | Filter by exact ID |
| `min_rent` / `max_rent` | float | – | Rent range filter |
| `is_available` | bool | `true` | Show available/unavailable |
| `sort_by` | enum | `newest` | `newest`, `title_asc`, `price_asc`, `price_desc` |
| `page` | int | `1` | Page number |
| `page_size` | int | `10` | 1–100 |

### 📝 Rental Requests — `/rental-requests`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/rental-requests/` | Tenant | Submit a request for a property |
| GET | `/rental-requests/my` | Tenant | View own requests |
| GET | `/rental-requests/` | Admin | View all requests |
| PATCH | `/rental-requests/{id}/status` | Admin | Approve or reject a request |

**Notes:**
- A tenant can only have **one pending** request per property.
- Approving a request marks the property **unavailable** and automatically **rejects** all other pending requests for it.
- List endpoints support `search`, `request_status`, `start_date`, `end_date`, `sort_by`, `page`, `page_size`.

### 👥 Users — `/users`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | Bearer | Get own profile |
| PATCH | `/users/me` | Bearer | Update own profile (name, phone, family members, district) |
| GET | `/users/` | Admin | List/search users (paginated) |
| GET | `/users/{id}` | Admin | Get one user |
| PATCH | `/users/{id}/status` | Admin | Activate / deactivate an account |

---

## 🗄 Database Schema

**users**
`id`, `full_name`, `email` (unique), `phone_number`, `family_members`, `home_district`, `national_id` (unique) / `passport_number` (unique — at least one required), `hashed_password`, `role`, `is_active`, `created_at`

**properties**
`id`, `title`, `description`, `location`, `monthly_rent`, `bedrooms`, `bathrooms`, `image_url`, `is_available`, `created_at`

**rental_requests**
`id`, `tenant_id` → `users.id`, `property_id` → `properties.id`, `message`, `status` (`pending` / `approved` / `rejected`), `created_at`

---

## ☁️ Deployment (Render)

1. Push the repository to GitHub.
2. Create a **PostgreSQL** instance on Render (or any hosted PostgreSQL) and copy its **External Database URL**.
3. Create a **Web Service** pointing at this repository:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in the Render dashboard:
   - `DATABASE_URL` = your PostgreSQL URL (use the `postgresql+psycopg://` format)
   - `SECRET_KEY` = a long random string
5. Deploy — the live API will be available at:
   **https://home-rental-api-jr53.onrender.com**

---

## ✅ Example Requests

**Register:**
```bash
curl -X POST https://home-rental-api-jr53.onrender.com/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"John Doe","email":"john@example.com","phone_number":"01700000000","family_members":3,"home_district":"Dhaka","national_id":"1234567890","password":"password123"}'
```

**Login:**
```bash
curl -X POST https://home-rental-api-jr53.onrender.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"john@example.com","password":"password123"}'
```

**List properties:**
```bash
curl https://home-rental-api-jr53.onrender.com/properties/?page=1&page_size=5&sort_by=price_asc
```

---

## 🧪 Stopping the Server

Press `Ctrl + C` in the terminal, then deactivate the environment:

```bash
deactivate
```

---

**Made with FastAPI ❤️**
