# Project Structure Details

## System Architecture

The application comprises:
1. **Frontend**: Streamlit or React (TypeScript) connecting via client code in `frontend/api/`.
2. **FastAPI Backend**: Provides REST endpoints for receipt processing and CRUD actions.
3. **Database**: MySQL managed with SQLAlchemy models and Alembic migrations.
4. **Gemini API**: Performs AI analysis on receipt uploads.
5. **Pandas/OpenPyXL**: Exports monthly report summaries to Excel files.
