# Microfinance API

A Spring Boot REST API for a micro-finance back office: head-office user login and password
management, plus reporting over wallet withdrawal transactions (all withdrawals, by date range,
by agent, and AEPS withdrawal / mini-statement / balance-enquiry counts).

Stack: Java 11, Spring Boot 2.5, Spring Data JPA, SQLite (default) or MySQL, BCrypt password hashing.

## Run it

Requires Java 11+. No database server needed: by default the API uses a local SQLite file
(`microfinance.db`) that is created and filled with **fake demo data** on first start.

```bash
./mvnw spring-boot:run        # http://localhost:8080
```

Demo logins (fake): `demo.admin` / `DemoAdmin@2026` and `demo.branch` / `DemoBranch@2026`.

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"username":"demo.admin","password":"DemoAdmin@2026"}' http://localhost:8080/fin/auth/login
curl -s http://localhost:8080/fin/getallwithdrawal
curl -s -H 'Content-Type: application/json' \
  -d '{"agentid":"AG1001","date1":"2026-09-01","date2":"2026-10-31"}' http://localhost:8080/fin/getbwdatesbyagent
```

Delete `microfinance.db` to reset the demo data. The seed scripts are
`src/main/resources/schema-sqlite.sql` and `data-sqlite.sql`.

### Using MySQL instead

Configuration comes only from environment variables. Copy `.env.example` to `.env`,
uncomment the MySQL block, then:

```bash
set -a; source .env; set +a
./mvnw spring-boot:run
```

| Variable | Default | Purpose |
|---|---|---|
| `DB_URL` | `jdbc:sqlite:microfinance.db?...` | JDBC URL |
| `DB_USERNAME` / `DB_PASSWORD` | empty | Database credentials |
| `DB_DIALECT` | SQLite dialect | `org.hibernate.dialect.MySQL5Dialect` for MySQL |
| `DB_POOL_SIZE` | `4` | Connection pool size (keep at least 2) |
| `DB_SEED` | `always` | Load the demo seed scripts; `never` for a real database |
| `JPA_DDL_AUTO` | `update` | Hibernate schema mode (`validate` in production) |
| `PORT` | `8080` | HTTP port |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated front-end origins |

Tests (no database server needed):

```bash
./mvnw test
```

## Endpoints

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/fin/auth/login` | `{username, password}` | `{status: 200}` or `{status: 401}` |
| POST | `/fin/auth/getuserdata` | `{username, password}` | The user record, without the password hash |
| POST | `/fin/auth/updatePassword` | `{username, currentPassword, newPassword}` | `{status: 200}` or `{status: 401}` |
| POST | `/fin/auth/loginlog` | login log entry | The saved entry |
| GET | `/fin/getallwithdrawal` | | All withdrawal transactions |
| POST | `/fin/getbwdates` | `{date1, date2}` | Withdrawals between two dates |
| POST | `/fin/getbwdatesbyagent` | `{agentid, date1, date2}` | Withdrawals for one agent between two dates |
| GET | `/fin/getaepswithdrawal`, `/fin/getaepsmini`, `/fin/getaepsbal` | | AEPS transaction counts |

## Security changes in this cleanup

- **Password reset required no password.** `updatePassword` was an unauthenticated GET that set any
  user's password from a username alone. It is now a POST that verifies `currentPassword` first,
  and new passwords must be at least 8 characters.
- **User data leaked the password hash.** `getuserdata` returned the full record, hash included, for
  any username. It now requires the user's password and the hash is never serialized.
- **Passwords were written to the log.** Login printed the submitted password and the stored hash
  to stdout and `imfin.log`. Nothing secret is logged now.
- **Login revealed which usernames exist.** Unknown user and wrong password now return the same 401.
- **Validation was silently off.** `@Valid` / `@NotBlank` had no validator on the classpath, so blank
  credentials passed. `spring-boot-starter-validation` is now included.
- **CORS allowed every website.** `@CrossOrigin("*")` on each endpoint is replaced by one policy that
  only allows `CORS_ALLOWED_ORIGINS`.
- **`/loginlog` always crashed.** Its repository was never injected (NullPointerException). Fixed with
  constructor injection.
- **Config and build output.** Database settings moved to environment variables; compiled output
  (`bin/`, `out/`, `target/`), logs and IDE files are no longer tracked; unused and conflicting
  dependencies removed; the missing Maven wrapper config was added so `./mvnw` works.

## Known gaps, before any deployment

- **The `/fin/**` reporting endpoints have no authentication.** Anyone who can reach the server can
  read withdrawal data. Put the API behind real auth (for example Spring Security with JWT or
  session login) before exposing it.
- Login does not issue a session or token, it only answers yes or no.
- Spring Boot 2.5 is end of life. Upgrading to Spring Boot 3 means Java 17 and `javax` to `jakarta`
  package renames.
- `UserRequest` is annotated as a JPA `@Entity`, so Hibernate creates an unused `user_request` table.
