# Finance Tracker (Streamlit)

Minimal Streamlit app for a personal finance tracker.

## Quick start (local)
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud
1. Push this folder to a **public GitHub repo**.
2. Go to https://share.streamlit.io/ (Deploy an app).
3. Fill the form:
   - **Repository**: your-username/your-repo
   - **Branch**: `main` (or whatever your repo uses)
   - **Main file path**: `app.py`
4. Click **Deploy**.

> Note: The app writes CSV files into the `data/` folder on the server's ephemeral storage. For a class demo this is fine. For persistent cloud storage use a database (e.g., SQLite on a mounted volume, Firebase, or Supabase).

## Files
- `app.py` – main Streamlit app
- `requirements.txt` – Python dependencies
- `data/` – runtime CSV storage (created automatically)

