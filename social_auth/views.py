import requests
import secrets
import urllib.parse
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import SocialAccount

@login_required
def connect_facebook(request):
    fb_auth_url = "https://www.facebook.com/v17.0/dialog/oauth"
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.FACEBOOK_REDIRECT_URI,
        "scope": "pages_manage_posts,pages_read_engagement,pages_show_list",
        "response_type": "code"
    }
    return redirect(f"{fb_auth_url}?{urllib.parse.urlencode(params)}")


@login_required
def connect_instagram(request):
    ig_auth_url = "https://www.facebook.com/v17.0/dialog/oauth"
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": settings.INSTAGRAM_REDIRECT_URI,
        "scope": "instagram_basic,instagram_content_publish,pages_show_list",
        "response_type": "code"
    }
    return redirect(f"{ig_auth_url}?{urllib.parse.urlencode(params)}")


@login_required
def connect_linkedin(request):
    linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"

    # Generate CSRF protection state token and save it in session
    state = secrets.token_urlsafe(16)
    request.session["linkedin_oauth_state"] = state

    params = {
        "response_type": "code",
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "scope": "openid profile email w_member_social",
        "state": state,
    }
    return redirect(f"{linkedin_auth_url}?{urllib.parse.urlencode(params)}")


@login_required
def facebook_callback(request):
    code = request.GET.get('code')
    if not code:
        return redirect('dashboard')

    token_resp = requests.get(
        'https://graph.facebook.com/v17.0/oauth/access_token',
        params={
            'client_id': settings.META_APP_ID,
            'redirect_uri': settings.FACEBOOK_REDIRECT_URI,
            'client_secret': settings.META_APP_SECRET,
            'code': code
        },
        timeout=10
    ).json()
    short_token = token_resp.get('access_token')
    if not short_token:
        return redirect('dashboard')

    long_token_resp = requests.get(
        'https://graph.facebook.com/v17.0/oauth/access_token',
        params={
            'grant_type': 'fb_exchange_token',
            'client_id': settings.META_APP_ID,
            'client_secret': settings.META_APP_SECRET,
            'fb_exchange_token': short_token
        },
        timeout=10
    ).json()
    long_token = long_token_resp.get('access_token', short_token)

    user_info = requests.get(
        'https://graph.facebook.com/me',
        params={'fields': 'id,name', 'access_token': long_token},
        timeout=10
    ).json()

    fb_id = user_info.get('id')
    fb_name = user_info.get('name') or "Facebook User"
    fb_url = f"https://www.facebook.com/{fb_id}" if fb_id else None

    SocialAccount.objects.update_or_create(
        user=request.user,
        provider='meta',
        account_id=fb_id or f"fb_unknown_{request.user.id}",
        defaults={
            'access_token': long_token,
            'extra': {
                'kind': 'facebook',
                'name': fb_name,
                'profile_url': fb_url
            }
        }
    )
    return redirect('dashboard')


@login_required
def instagram_callback(request):
    code = request.GET.get('code')
    if not code:
        return redirect('dashboard')

    # 1️⃣ Exchange code for short-lived token
    token_resp = requests.get(
        'https://graph.facebook.com/v17.0/oauth/access_token',
        params={
            'client_id': settings.META_APP_ID,
            'redirect_uri': settings.INSTAGRAM_REDIRECT_URI,
            'client_secret': settings.META_APP_SECRET,
            'code': code
        },
        timeout=10
    ).json()
    short_token = token_resp.get('access_token')
    if not short_token:
        return redirect('dashboard')

    # 2️⃣ Upgrade to long-lived token
    long_token_resp = requests.get(
        'https://graph.facebook.com/v17.0/oauth/access_token',
        params={
            'grant_type': 'fb_exchange_token',
            'client_id': settings.META_APP_ID,
            'client_secret': settings.META_APP_SECRET,
            'fb_exchange_token': short_token
        },
        timeout=10
    ).json()
    long_token = long_token_resp.get('access_token', short_token)

    # 3️⃣ Get all pages + linked IG accounts
    me_info = requests.get(
        'https://graph.facebook.com/v17.0/me/accounts',
        params={
            'access_token': long_token,
            'fields': 'id,name,instagram_business_account'
        },
        timeout=10
    ).json()

    # 4️⃣ Let’s collect ALL available IG accounts instead of just first one
    instagram_accounts = []
    if 'data' in me_info:
        for p in me_info['data']:
            ig = p.get('instagram_business_account')
            if ig and ig.get('id'):
                instagram_accounts.append({
                    "ig_id": ig.get('id'),
                    "page_id": p.get('id'),
                    "page_name": p.get('name')
                })

    # 5️⃣ For now, pick the first one (⚠️ but better: show a selection UI to the user)
    ig_id = None
    page_name = None
    if instagram_accounts:
        chosen = instagram_accounts[0]   # <-- You can change this to user’s selection
        ig_id = chosen['ig_id']
        page_name = chosen['page_name']

    # 6️⃣ Fetch IG username for clarity
    ig_username = None
    if ig_id:
        ig_info = requests.get(
            f'https://graph.facebook.com/v17.0/{ig_id}',
            params={'fields': 'username', 'access_token': long_token},
            timeout=10
        ).json()
        ig_username = ig_info.get('username')

    SocialAccount.objects.update_or_create(
        user=request.user,
        provider='meta',
        account_id=ig_id or f"ig_unknown_{request.user.id}",
        defaults={
            'access_token': long_token,
            'extra': {
                'kind': 'instagram',
                'name': ig_username or page_name or 'Instagram Account',
                'profile_url': f"https://www.instagram.com/{ig_username}/" if ig_username else None
            }
        }
    )

    return redirect('dashboard')



@login_required
def linkedin_callback(request):
    code = request.GET.get("code")
    if not code:
        messages.error(request, "Missing authorization code.")
        return redirect("/")

    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        "client_id": settings.LINKEDIN_CLIENT_ID,
        "client_secret": settings.LINKEDIN_CLIENT_SECRET,
    }
    resp = requests.post(token_url, data=data)
    if resp.status_code != 200:
        messages.error(request, f"LinkedIn token request failed: {resp.text}")
        return redirect("/")
    token_json = resp.json()

    access_token = token_json.get("access_token")
    if not access_token:
        messages.error(request, f"LinkedIn token error: {token_json}")
        return redirect("/")

    # ✅ Fetch userinfo instead of /me and /emailAddress
    userinfo_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    ).json()

    linkedin_id = userinfo_resp.get("sub", f"li_unknown_{request.user.id}")
    linkedin_name = userinfo_resp.get("name") or "LinkedIn User"
    email = userinfo_resp.get("email")
    picture = userinfo_resp.get("picture")
    profile_url = f"https://www.linkedin.com/in/{linkedin_id}"  # may not always resolve, but useful

    SocialAccount.objects.update_or_create(
        user=request.user,
        provider="linkedin",
        account_id=linkedin_id,
        defaults={
            "access_token": access_token,
            "extra": {
                "kind": "linkedin",
                "name": linkedin_name,
                "profile_url": profile_url,
                "email": email,
                "picture": picture,
                "expires_in": token_json.get("expires_in"),
                "refresh_token": token_json.get("refresh_token"),
            }
        }
    )

    messages.success(request, "LinkedIn connected successfully!")
    return redirect("dashboard")