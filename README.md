# Agro-Mind

Agro-Mind is an AI-powered agricultural customer support assistant built for a bootcamp client project.

The system helps agricultural customers with crop issue questions, pesticide safety concerns, product recommendations, order lookup, escalation detection, and support case saving.

## Current MVP

The current version includes:

- React chatbot frontend
- FastAPI backend
- Intent classification
- Safety risk checking
- Product recommendation from mock CSV data
- Order/logistics lookup from mock CSV data
- SQLite case saving
- Duplicate case protection for repeated messages
- Agent analysis panel showing intent, risk, product/order details, escalation, and case ID

## Tech Stack

### Frontend

- React
- Vite
- Lucide React icons
- CSS

### Backend

- Python
- FastAPI
- Pandas
- SQLAlchemy
- SQLite

## Project Structure

```text
agro-mind/
├── backend/
│   ├── main.py
│   ├── data/
│   │   ├── products.csv
│   │   └── orders.csv
│   ├── database/
│   │   ├── db.py
│   │   └── models.py
│   └── tools/
│       ├── intent_classifier.py
│       ├── safety_checker.py
│       ├── product_recommender.py
│       ├── logistics_lookup.py
│       └── case_memory.py
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── index.html
│
├── requirements.txt
├── README.md
└── .gitignore
```

## How to Run the Backend

Open a terminal in the root project folder:

cd C:\agro-mind
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload

Backend runs at:

http://127.0.0.1:8000

FastAPI docs are available at:

http://127.0.0.1:8000/docs
How to Run the Frontend

Open another terminal:

cd C:\agro-mind\frontend
npm run dev

Frontend runs at:

http://localhost:5173

## Example Messages

Try these in the chatbot:

My tomato leaves have yellow spots. What should I use?
My child touched pesticide and his skin is burning
Can you recommend a product for tomato aphids?
Where is my order?
Where is my order 1001?

## Important MVP Notes

This project currently uses mock data for products, orders, and customer IDs.

The Customer ID input is for MVP testing only. In a production system, customer identity should come from authentication, such as a login session, JWT token, Firebase Auth, Auth0, Supabase Auth, or the client company's existing user system.

The SQLite database is generated locally when the backend runs. The actual .db file should not be uploaded to GitHub.

Next Planned Features
RAG knowledge base using agricultural documents
Better company FAQ support
Image upload and mock crop diagnosis
Reports summary endpoint
Case history view
Improved production authentication flow

---

After pasting, save with:

```text
Ctrl + S

Then delete:

backend/database/agro_mind.db

Keep:

backend/database/db.py
backend/database/models.py

Then you’re good for GitHub.
```
