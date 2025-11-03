Quantra
======

Status: In active development
Purpose: Educational template for an exchange-style app (wallets, simple order flow, staking demo). NOT for production use.

DISCLAIMER
----------
- EDUCATIONAL USE ONLY. Quantra is a learning template and NOT a real exchange.
- NO WARRANTY. Provided “AS IS”, with no warranties or guarantees of any kind.
- NO LIABILITY. The authors/contributors assume NO responsibility for losses, damages, or legal issues resulting from use.
- NO FINANCIAL/LEGAL ADVICE. Nothing here is investment, financial, or legal advice.
- REGULATORY COMPLIANCE IS YOUR RESPONSIBILITY. If you adapt this code, ensure compliance with all laws/regulations in your jurisdiction.
- SECURITY NOT REVIEWED. No audits; expect bugs/incomplete logic. Use at your own risk.

By using, copying, modifying, or deploying this code, you agree to the above terms.

WHAT IS QUANTRA?
----------------
Quantra is a minimal, educational scaffold showing patterns commonly seen in exchange-like apps:
- Basic account & wallet abstractions (mock/local only)
- Toy order flow primitives (limit/market stubs for demos)
- Staking demo (illustrative APR math; not real DeFi)
- Mock market data & simple order book visualization
- Admin/dev scripts to seed demo data and reset state
- Clear boundaries for safe demos vs. never using real value

ROADMAP (WIP)
-------------
- Harder domain types and invariants
- Better market/liquidity mocks
- Expanded staking scenarios (penalties, tiers)
- API docs & typed SDK stubs
- Unit/integration tests and CI
- Security notes & threat model checklist

TECH STACK (example)
--------------------
- Backend: Python/Django (DRF) or FastAPI (alternate branch)
- Workers: Celery/RQ
- DB: PostgreSQL (dev), SQLite (quick start)
- Frontend: Next.js + Tailwind
- Messaging: Redis (optional)
- Infra: Docker

QUICK START (LOCAL ONLY)
------------------------
Never connect to mainnet or handle real funds.

1) Clone
   git clone https://example.com/quantra.git
   cd quantra

2) Environment
   cp .env.example .env
   Set: ENV=development, DISABLE_REAL_NETS=1, FAKE_FUNDS_ONLY=1

3) Docker (optional)
   docker compose up --build

4) Local run
   # backend
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload

   # frontend
   cd frontend
   npm install
   npm run dev

Seeding demo data:
   python scripts/seed_demo.py

TESTING
-------
   pytest -q
   # or
   npm run test

SECURITY & SAFETY
-----------------
- Do not import private keys or connect real wallets.
- Do not enable withdrawals/bridges on public networks.
- Treat all balances as fake demo balances.
- Run only in a local/sandbox environment.

LICENSE
-------
Unless a different LICENSE file is added, contents are provided AS IS for educational purposes. Reuse with attribution. If you need a specific license (MIT/Apache-2.0), add it explicitly.

CV NOTE
-------
You may reference Quantra in your CV as an educational template demonstrating modular domain design, clear demo/production boundaries, and documentation-first practices.

CONTACT
-------
Project: Quantra
Owner: Daniel Sklyarov (developer)
Purpose: Educational demo only
Issues: open a ticket in the repository
