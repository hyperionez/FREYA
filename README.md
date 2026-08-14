# Run Project

### Docker
docker compose up --build -d

### local
Backend harus dijalankan duluan, karena frontend cuma UI yang manggil API  kalau UI dibuka duluan tanpa backend hidup, dia akan tampil tapi error.

Terminal 1 — backend:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000

Terminal 2 (baru, biarkan terminal 1 tetap jalan)  frontend:
.\.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py