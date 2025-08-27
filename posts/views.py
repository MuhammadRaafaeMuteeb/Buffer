from django.conf import settings
import requests
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages

import cloudinary
import cloudinary.uploader
import json

from social_auth.models import SocialAccount
from .models import Post

# -------------------------------
# DASHBOARD
# -------------------------------
@login_required
def manage_accounts(request):
    accounts = SocialAccount.objects.filter(user=request.user)
    connected = {}
    for acc in accounts:
        if acc.provider == 'meta':
            # For Facebook and Instagram, use the 'kind' from 'extra' field
            kind = acc.extra.get('kind')
            if kind:
                connected[kind] = acc
        else:
            connected[acc.provider] = acc
    return render(request, "social_auth/manage_accounts.html", {
        "connected": connected
    })

@login_required
def disconnect_account(request, platform):
    if platform in ['facebook', 'instagram']:
        # For Facebook and Instagram, the provider is 'meta', and the specific platform is in 'extra__kind'
        SocialAccount.objects.filter(user=request.user, provider='meta', extra__kind=platform).delete()
    else:
        # For other platforms like LinkedIn, the provider matches the platform name
        SocialAccount.objects.filter(user=request.user, provider=platform).delete()
    messages.success(request, f"{platform.capitalize()} account disconnected.")
    return redirect("manage_accounts")

@login_required
def dashboard(request):
    accounts = SocialAccount.objects.filter(user=request.user)
    meta_accounts = accounts.filter(provider='meta')
    linkedin = accounts.filter(provider='linkedin').first()

    published_posts = Post.objects.filter(user=request.user).exclude(
        platforms__isnull=True
    ).exclude(platforms="").order_by("-created")

    context = {
        "accounts": accounts,
        "meta_accounts": meta_accounts,
        "linkedin": linkedin,
        "total_accounts": accounts.count(),
        "published_posts": published_posts,
    }
    return render(request, "dashboard.html", context)

# -------------------------------
# HELPERS
# -------------------------------
def publish_to_facebook(user, message, image_url=None):
    fb = SocialAccount.objects.filter(
        user=user,
        provider='meta',
        extra__kind='facebook'
    ).first()
    if not fb:
        raise Exception("No connected Facebook account")

    pages = requests.get(
        "https://graph.facebook.com/v17.0/me/accounts",
        params={"access_token": fb.access_token, "fields": "id,name,access_token"},
        timeout=10
    ).json()

    if 'data' not in pages or not pages['data']:
        raise Exception("No pages found for this FB user")

    page = pages['data'][0]
    page_token = page.get('access_token')
    page_id = page.get('id')

    if image_url:
        resp = requests.post(
            f"https://graph.facebook.com/v17.0/{page_id}/photos",
            data={"url": image_url, "caption": message, "access_token": page_token},
            timeout=10
        ).json()
        post_id = resp.get("post_id")
    else:
        resp = requests.post(
            f"https://graph.facebook.com/v17.0/{page_id}/feed",
            data={"message": message, "access_token": page_token},
            timeout=10
        ).json()
        post_id = resp.get("id")

    if "error" in resp:
        raise Exception(resp["error"].get("message", "Unknown Facebook error"))

    permalink = None
    if post_id:
        details = requests.get(
            f"https://graph.facebook.com/v17.0/{post_id}",
            params={"access_token": page_token, "fields": "permalink_url"},
            timeout=10
        ).json()
        permalink = details.get("permalink_url")

    return {"id": post_id, "permalink": permalink}

def publish_to_instagram(user, text, image_url):
    if not image_url:
        raise Exception("Instagram requires an image")

    ig = SocialAccount.objects.filter(
        user=user,
        provider='meta',
        extra__kind='instagram'
    ).first()
    if not ig:
        raise Exception("No connected Instagram account")

    pages = requests.get(
        "https://graph.facebook.com/v17.0/me/accounts",
        params={
            "access_token": ig.access_token,
            "fields": "id,name,instagram_business_account,access_token"
        },
        timeout=10
    ).json()

    page_token = None
    for p in pages.get("data", []):
        insta = p.get("instagram_business_account")
        if insta and insta.get("id") == ig.account_id:
            page_token = p.get("access_token")
            break

    if not page_token and pages.get("data"):
        page_token = pages["data"][0].get("access_token")

    if not page_token:
        raise Exception("No page token available for IG publishing")

    create = requests.post(
        f"https://graph.facebook.com/v17.0/{ig.account_id}/media",
        data={
            "image_url": image_url,
            "caption": text,
            "access_token": page_token
        },
        timeout=10
    ).json()

    creation_id = create.get("id")
    if not creation_id:
        raise Exception(f"Failed to create IG media: {create}")

    publish = requests.post(
        f"https://graph.facebook.com/v17.0/{ig.account_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": page_token
        },
        timeout=10
    ).json()

    if "error" in publish:
        raise Exception(publish["error"].get("message", "Unknown Instagram error"))

    # Get permalink for Instagram post
    instagram_url = None
    media_id = publish.get("id")
    if media_id:
        media_details = requests.get(
            f"https://graph.facebook.com/v17.0/{media_id}",
            params={"access_token": page_token, "fields": "permalink"},
            timeout=10
        ).json()
        instagram_url = media_details.get("permalink")

    return {"id": media_id, "permalink": instagram_url}

def publish_to_linkedin(user, message, image_url=None):
    linkedin = SocialAccount.objects.filter(
        user=user,
        provider='linkedin'
    ).first()
    if not linkedin:
        raise Exception("No connected LinkedIn account")

    headers = {
        "Authorization": f"Bearer {linkedin.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }

    author = f"urn:li:person:{linkedin.account_id}"

    if not image_url:
        # ---------------- Text-only Post ----------------
        post_data = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            data=json.dumps(post_data),
            timeout=10
        ).json()
    else:
        # ---------------- Image Post ----------------
        register_payload = {
            "registerUploadRequest": {
                "owner": author,
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "serviceRelationships": [{
                    "identifier": "urn:li:userGeneratedContent",
                    "relationshipType": "OWNER"
                }]
            }
        }

        upload_resp = requests.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            data=json.dumps(register_payload),
            timeout=10
        ).json()

        if "value" not in upload_resp:
            raise Exception(f"Failed to register upload: {upload_resp}")

        upload_url = upload_resp["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = upload_resp["value"]["asset"]

        image_bytes = requests.get(image_url).content
        upload_headers = {"Authorization": f"Bearer {linkedin.access_token}"}
        upload_put = requests.put(upload_url, headers=upload_headers, data=image_bytes)

        if upload_put.status_code not in (200, 201, 202):
            raise Exception(f"Image upload failed: {upload_put.text}")

        post_data = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": message},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "description": {"text": message[:200]},
                        "media": asset_urn,
                        "title": {"text": "Image"}
                    }]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }

        resp = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            data=json.dumps(post_data),
            timeout=10
        ).json()

    if "serviceErrorCode" in resp:
        raise Exception(resp.get("message", "Unknown LinkedIn error"))

    # ---------------- Extract permalink ----------------
    post_id = resp.get("id")  # e.g. "urn:li:share:1234567890123456789"
    permalink = None
    if post_id and post_id.startswith("urn:li:share:"):
        share_id = post_id.split(":")[-1]
        permalink = f"https://www.linkedin.com/feed/update/urn:li:share:{share_id}"

    return {"id": post_id, "permalink": permalink}

# -------------------------------
# NEW POST VIEW
# -------------------------------
@login_required
def new_post(request):
    selected_platforms = []

    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        image_url = request.POST.get("image_url", "").strip()
        selected_platforms = request.POST.getlist("platforms")

        if "image" in request.FILES:
            upload_result = cloudinary.uploader.upload(request.FILES["image"])
            image_url = upload_result.get("secure_url")

        published_platforms = []
        fb_url = ig_url = li_url = None

        if "facebook" in selected_platforms:
            try:
                fb_resp = publish_to_facebook(request.user, message, image_url=image_url)
                fb_url = fb_resp.get("permalink")
                published_platforms.append("Facebook")
            except Exception as e:
                messages.error(request, f"Facebook error: {str(e)}")

        if "instagram" in selected_platforms:
            try:
                ig_resp = publish_to_instagram(request.user, text=message, image_url=image_url)
                ig_url = ig_resp.get("permalink")
                published_platforms.append("Instagram")
            except Exception as e:
                messages.error(request, f"Instagram error: {str(e)}")

        if "linkedin" in selected_platforms:
            try:
                li_resp = publish_to_linkedin(request.user, message, image_url=image_url)
                li_url = li_resp.get("permalink")
                published_platforms.append("LinkedIn")
            except Exception as e:
                messages.error(request, f"LinkedIn error: {str(e)}")

        if message or image_url:
            Post.objects.create(
                user=request.user,
                text=message,
                image_url=image_url,
                platforms=",".join(published_platforms) if published_platforms else None,
                facebook_url=fb_url,
                instagram_url=ig_url,
                linkedin_url=li_url,
            )

        if published_platforms:
            messages.success(request, f"Post published to: {', '.join(published_platforms)}")
        else:
            messages.success(request, "Post saved locally (not published).")

        return redirect("dashboard")

    return render(request, "posts/new_post.html", {
        "selected_platforms": selected_platforms
    })

# -------------------------------
# API-STYLE VIEWS
# -------------------------------
@csrf_exempt
@login_required
def post_to_facebook(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)
    try:
        resp = publish_to_facebook(
            request.user,
            message=request.POST.get("message"),
            image_url=request.POST.get("image_url")
        )
        return JsonResponse({"success": True, "response": resp})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
@login_required
def post_to_instagram(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)
    try:
        resp = publish_to_instagram(
            request.user,
            text=request.POST.get("caption") or request.POST.get("message"),
            image_url=request.POST.get("image_url")
        )
        return JsonResponse({"success": True, "response": resp})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
@login_required
def post_to_linkedin(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=400)
    try:
        resp = publish_to_linkedin(
            request.user,
            message=request.POST.get("message"),
            image_url=request.POST.get("image_url")
        )
        return JsonResponse({"success": True, "response": resp})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})
