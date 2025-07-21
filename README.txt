
# Hire Ready Resume Builder

## Backend Deployment (Render)
1. Create a new FastAPI service in Render
2. Use `backend/main.py` as the entry point
3. Install packages from `backend/requirements.txt`

## Frontend Setup (Elementor)
1. Add your form with ID `resume-form`
2. Add `frontend/custom_form.js` into a Custom HTML widget on the same page
3. Ensure your backend URL is set correctly in the JS

## Output
- Resume preview will display on the same page
- PDF link will be provided for download
