# Quantra

> **Status:** 🚧 In active development  
> **Purpose:** Educational template for a crypto exchange–style app (e.g., wallets, simple order flow, staking demo).  
> **Not for production. Do **NOT** deploy to mainnet or handle real funds.

---

## ⚠️ Disclaimer (Read First)

- **Educational Use Only.** Quantra is a learning template and **not** a real exchange.  
- **No Warranty.** Provided “AS IS”, without warranties or guarantees of any kind.  
- **No Liability.** The authors and contributors **assume no responsibility** for loss, damage, legal issues, or other consequences arising from the use of this code.  
- **No Financial/Legal Advice.** Nothing here constitutes investment, financial, or legal advice.  
- **Regulatory Compliance Is Your Responsibility.** If you adapt this code, you must ensure compliance with all applicable laws, regulations, and licensing requirements in your jurisdiction.  
- **Security Not Reviewed.** No formal audits. Expect bugs, incomplete logic, and insecure defaults. Use at your own risk.

> By using, copying, modifying, or deploying this code, you agree to the above terms.

---

## ✨ What is Quantra?

Quantra is a minimal, **educational** scaffold showcasing common patterns you might see in an exchange-like app:

- Basic account & wallet abstractions (mocked/local, not custodial)
- Toy order flow primitives (limit/market **stubs** for demos)
- **Staking demo** (illustrative APR math & lockup logic — **not** DeFi)
- Mocked market data & basic order book visualization (**non-binding** demo)
- Admin/dev tooling to seed demo data and reset the environment
- Clear boundaries for safe demos vs. **never** use with real value

> The goal is to help recruiters understand your architecture thinking and code hygiene — **not** to run real money.

---

## 🗺️ Roadmap (WIP)

- [ ] Hardening of domain types and invariants
- [ ] Better mocking for markets/liquidity
- [ ] Expand staking scenarios (early exit penalties, tiers)
- [ ] API docs & typed SDK stubs
- [ ] Unit/integration tests and CI
- [ ] Security notes & threat model checklist

---

## 🧰 Tech Stack (example)

- Backend: Python / Django (DRF) or FastAPI (choose one in your branch)
- Workers: Celery / RQ for async demos
- DB: PostgreSQL (local dev), SQLite for quick start
- Frontend: Next.js + Tailwind (demo screens)
- Messaging/Streams (optional): Redis
- Infra: Docker for local dev

> This repo may contain multiple branches demonstrating alternative stacks.

---

## 🚀 Quick Start (Local Only)

> **Never** point this at mainnet or any chain with real value. Use local mocks/testnets only.

```bash
# 1) Clone
git clone https://example.com/quantra.git
cd quantra

# 2) Local env
cp .env.example .env
# Set: ENV=development, DISABLE_REAL_NETS=1, FAKE_FUNDS_ONLY=1

# 3) (Optional) Docker
docker compose up --build

# 4) Or run locally
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# frontend
cd frontend
npm i && npm run dev
```

### Seeding Demo Data

```bash
python scripts/seed_demo.py  # users, wallets (fake), markets (mock)
```

---

## 🧪 Testing

```bash
pytest -q
# or
npm run test
```

---

## 🔐 Security & Safety Notes

- **Do not** import private keys or connect real wallets.  
- **Do not** enable withdrawals/bridges on public networks.  
- Assume **all** balances here are **fake**.  
- Treat this as untrusted code running in a dev sandbox.

---

## 📄 License

Unless a different LICENSE file is provided, the contents are offered **AS IS** for educational purposes. You may reuse with attribution. If you need a specific license (e.g., MIT/Apache-2.0), add it explicitly.

---

## 🤝 Attribution / Use in CV

You may reference **Quantra** in your CV as an **educational template** showcasing:
- modular domain design
- clear boundaries between demo and production concerns
- documentation-first approach with safety disclaimers

If a recruiter asks: emphasize **this is a non-production, educational repo**.

---

## 📬 Contact / Maintainer

Project: **Quantra**  
Owner: Daniel Sklyarov (developer)  
Purpose: Educational demo only  
Issues & feedback: open a ticket in the repo

