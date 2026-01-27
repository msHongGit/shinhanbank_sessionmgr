
# 🚀 AI Agent Prompt: Financial Chatbot Session Architecture

You are an expert **Backend Architect & Lead Developer** specializing in high-security financial systems.
Your task is to implement a **Session Management & Authentication System** for a chatbot based on the following strict specifications.

## 1. System Overview

* **Architecture Pattern:** Reference Token + Async Binding + Native Recovery.
* **Goal:** Secure, seamless chat experience where sessions persist even if cookies are lost, utilizing the Native App's authentication context.
* **Key Constraints:**
1. **Cookie-Only:** No `Authorization` headers.
2. **Server-Side Identification:** Client never sends `userId` directly; Server extracts it from `Sol Token`.
3. **Dumb Relay:** SSE Relay server delegates all auth verification to the Auth Gateway (AGW).
4. **Atomic Redis:** Use Lua scripts to maintain consistency between Session Data and User Indexes.



---

## 2. Data & Security Specifications

### A. Token Strategy (Stateful JWT)

All tokens are **Reference Tokens** (Payload contains only `jti`).
| Token | Storage | Path | Expiry | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Access Token (AT)** | Cookie | `/` | **10 min** | API Access, SSE Connection |
| **Refresh Token (RT)** | Cookie | `/refresh` | **24 hours** | RTR (Rotation), Keep-Alive |
| **Sol Token** | Header | (Native App) | **1 hour** | Financial Auth, **Session Recovery** |

* **Cookie Flags:** `HttpOnly`, `Secure`, `SameSite=Strict`.

### B. Redis Schema (Two-Key Strategy)

Data must be managed via **Lua Scripts** to ensure atomicity.

1. **Main Session (Hash):** `chat:sess:{jti}`
* Fields: `status` ("PENDING" | "ACTIVE"), `userId`, `solToken`, `createdAt`
* TTL: **30 mins** (Sliding Expiration on 'Invoke')


2. **Reverse Index (String):** `chat:idx:{userId}`
* Value: `"{jti}"` (UUID)
* TTL: **30 mins** (Sync with Main Session)
* *Purpose:* Allows finding the session ID using User ID during recovery.



---

## 3. Process Workflows (The Logic)

### Phase 1: Connection & Async Binding (The Handshake)

1. **Start:** Web Client calls `/start`.
* Server generates `jti` (UUID), creates empty Redis session (`PENDING`), sets AT/RT Cookies.


2. **SSE Connect:** Web Client connects to `/sse/connect` (Cookies sent automatically).
* **Relay -> AGW:** Relay calls `GET /internal/verify`.
* **AGW:** Validates cookie. Returns `{ valid: true, jti: "..." }`.
* **Relay:** Subscribes to Redis channel `{jti}`. Connection Established.


3. **Async Binding:**
* Web triggers Native App.
* Native App calls Sol WAS (Legacy).
* Sol WAS calls AGW (Internal API) with User Info.
* **AGW:** Updates `chat:sess:{jti}` to `ACTIVE` **AND** creates `chat:idx:{userId}`.



### Phase 2: Token Rotation (RTR) - Happy Path

* **Trigger:** AT expired (401).
* **Action:** Web calls `/refresh`.
* **Logic:**
* Verify RT.
* **Rotate:** Issue new AT & new RT.
* **Side Effect:** Do **NOT** extend Redis Session TTL (Keep connectivity only).



### Phase 3: Native Recovery (The Core Feature) - Edge Case

* **Trigger:** Cookie lost (ITP/Deleted) OR Sol Token expired.
* **Action:** Web catches 401/No Cookie -> Calls Native Bridge (`renewAuth`).
* **Native Logic:**
* Checks internal login status.
* Calls AGW `/bind` API with Header `X-SOL-TOKEN`.


* **AGW Logic:**
1. Validate `Sol Token` & **Extract `userId**`.
2. **Lookup:** `GET chat:idx:{userId}`.
* **Hit:** Reuse existing `jti`.
* **Miss:** Create new `jti`.


3. Issue new AT/RT Cookies.


* **Final:** Native App injects cookies into Webview -> Web retries request.

---

## 4. Component Responsibilities (R&R)

### 🖥️ AGW (Auth Gateway / Session Manager)

* **Lua Scripting:** Implement `touch_session.lua` to extend both `chat:sess:{jti}` and `chat:idx:{userId}` atomically upon user message (`Invoke`).
* **Verification API:** Provide `/internal/verify` for Relay. Must return the `jti` in the response body.
* **Recovery API:** Provide `/bind`. Must NOT accept `userId` in body/param. Must extract it from the `Sol Token`.

### 📡 SSE Relay Server

* **Pass-through:** Extract Cookie from handshake request -> Call AGW `/verify`.
* **Mapping:** Use the `jti` returned by AGW to subscribe to the correct Redis channel.
* **No Logic:** Do not parse JWT, do not access Redis for Auth.

### 📱 Client (Native App & Web)

* **Implicit Connection:** SSE connection uses Cookies, no `roomId` in URL.
* **Bridge:** Native App must implement a bridge to handle `renewAuth` requests from Web and inject cookies manually via `CookieManager`.

---

## 5. Implementation Plan

Please generate code following this plan:

### Step 1: Redis Repository & Lua Scripts

* Implement `SessionRepository` with `RedisTemplate`.
* Write `create_session.lua` (Atomic set session & index).
* Write `touch_session.lua` (Atomic expire extension for session & index).

### Step 2: JWT & Cookie Utilities

* Implement `JwtProvider` (Generate/Parse/Validate).
* Implement `CookieUtil` (Generate HttpOnly cookies with correct paths).

### Step 3: AGW Core Logic (Controller/Service)

* `POST /start`: Initialize session.
* `GET /internal/verify`: For Relay.
* `POST /bind` (Recovery): Extract UserID from SolToken -> Lookup Index -> Re-issue Cookies.
* `POST /refresh`: RTR logic.

### Step 4: SSE Relay Logic (Mock)

* Simulate the Relay's behavior: Receive request -> Call AGW -> Subscribe Redis.

---

**Action:**
Based on the specs above, please start by writing the **Redis Lua Scripts** and the **Java (Spring Boot) Service Layer** that handles the *Native Recovery* logic (`recoverSession`).
 

[추가 로직 검토 필요]
 1. 만료 확인 (Client)
   └─ 401 에러 및 쿠키 없음 감지

2. 토큰 재발급 (Client → AGW)
   ├─ [변경] App: `/bind` API 호출 (Header: `X-SOL-TOKEN`만 전송)
   ├─ [신규] AGW: Sol Token 검증 로직을 통해 `userId` 추출 (Server-Side Identification)
   ├─ AGW: Redis Index(`chat:idx:{userId}`) 조회
   │      ├─ 기존 세션 있음: 기존 `jti` 반환 (대화 유지)
   │      └─ 기존 세션 없음: 신규 `jti` 생성
   └─ AGW: 새 AT/RT 쿠키 발급 및 응답

3. redis expire trigger
- task_queue가 남아있을 때 세션 종료 시 세션 관련 정보(세션 조회로 master agent가 가져가는 정보)는 maria db에 저장 필요

4. client와의 edge 테스트 진행 필요
- expire 되었을 때
- 402 등 error 시

5. redis에 user_id/jti pipe로 묶어서 동기화 필요