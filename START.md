# Run JailoApp locally (2 terminals)

## 1. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          (Windows)   |   source .venv/bin/activate   (Mac/Linux)
pip install -r requirements.txt
copy .env.example .env          (Windows)   |   cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8000

## 2. Front end
npm install
npm run dev
-> open http://localhost:5173

Demo logins (code is shown on screen): villager +996700000003, rescuer +996700000002, buyer +996700000004
