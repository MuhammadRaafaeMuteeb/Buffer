# Buffer Clone (Prototype)

This is a minimal Django prototype that demonstrates:
- User signup/login
- Connect Meta (Facebook/Instagram) and LinkedIn using OAuth2
- Create a post and publish to connected accounts (Facebook Pages, LinkedIn, Instagram via Graph API)

## Quick start

1. Copy `.env.example` to `.env` and fill in your app credentials and SECRET_KEY.
2. Create virtualenv & install:
   ```
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Run migrations and create superuser:
   ```
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. Run the server:
   ```
   python manage.py runserver
   ```
5. Visit http://localhost:8000/accounts/signup/ to create a tester user. Ensure your developer app has the tester in App Roles (Meta) so OAuth works in dev mode.

## Notes & Caveats

- This is a **prototype**. In production you must secure tokens, exchange Meta short-lived tokens for long-lived tokens, refresh tokens, handle errors, and validate callbacks (state param).
- Instagram publishing requires that the connected Facebook Page has an Instagram Business account and that the user has granted the required scopes.
- LinkedIn requests are rate-limited and require `w_member_social`.
- Tailwind is used via CDN for quick prototyping. For production consider building Tailwind locally.

