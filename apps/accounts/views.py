from django.contrib.auth import login, logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.common.ratelimit import LIMITS, check, client_ip, rate_limit, too_many

from .forms import ProfileForm, RegistrationForm
from .models import User


class ThrottledLoginView(auth_views.LoginView):
    """Login with brute-force protection on two axes: per-IP (blunts spraying
    across many accounts) and per-submitted-email (blunts targeting one
    account). Checked before the credentials are evaluated. The response is a
    generic 429 that does not reveal whether the email exists."""

    def post(self, request, *args, **kwargs):
        allowed_ip, retry_ip = check("login_ip", client_ip(request), LIMITS["login_ip"])
        # Django's AuthenticationForm names the identifier field "username";
        # for our email-login user that field carries the email address.
        email = (request.POST.get("username") or "").strip().lower()
        allowed_email, retry_email = (True, 0)
        if email:
            allowed_email, retry_email = check(
                "login_email", email, LIMITS["login_email"]
            )
        if not (allowed_ip and allowed_email):
            return too_many(request, max(retry_ip, retry_email))
        return super().post(request, *args, **kwargs)


class ThrottledPasswordResetView(auth_views.PasswordResetView):
    """Password-reset throttled per-IP and per-submitted-email. Django's view
    already returns an identical response whether or not the email exists, so
    this adds no enumeration signal — the limits simply cap abuse of the
    reset-email sender."""

    def post(self, request, *args, **kwargs):
        allowed_ip, retry_ip = check(
            "password_reset_ip", client_ip(request), LIMITS["password_reset_ip"]
        )
        email = (request.POST.get("email") or "").strip().lower()
        allowed_email, retry_email = (True, 0)
        if email:
            allowed_email, retry_email = check(
                "password_reset_email", email, LIMITS["password_reset_email"]
            )
        if not (allowed_ip and allowed_email):
            return too_many(request, max(retry_ip, retry_email))
        return super().post(request, *args, **kwargs)


@rate_limit("register", LIMITS["register"], methods=("POST",))
def register(request):
    if request.user.is_authenticated:
        return redirect("profile")
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # auto-login after registration
            return redirect("profile")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_detail(request, pk=None):
    """Own profile (pk=None) or another member's (pk set). Auth required to
    view any profile (M2)."""
    user = request.user if pk is None else get_object_or_404(User, pk=pk)
    is_own = user == request.user
    # Local imports avoid app-load import cycles (these apps depend on accounts).
    from apps.moderation.services import is_blocking
    from apps.reviews.models import Review
    reviews = (Review.objects.filter(reviewee=user)
               .select_related("reviewer__profile")[:20])
    is_blocked = False if is_own else is_blocking(request.user, user)
    return render(
        request,
        "accounts/profile_detail.html",
        {"profile_user": user, "profile": user.profile, "is_own": is_own,
         "reviews": reviews, "is_blocked": is_blocked},
    )


@login_required
def settings_edit(request):
    """Edit ONLY the logged-in user's own profile. There is no path to edit
    another member's profile — object ownership is structural (M2)."""
    profile = request.user.profile
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)
    return render(request, "accounts/settings.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def deactivate(request):
    if request.method == "POST":
        user = request.user
        user.is_deactivated = True
        user.deactivated_at = timezone.now()
        user.is_active = False  # blocks future logins
        user.save(update_fields=["is_deactivated", "deactivated_at", "is_active"])
        logout(request)
        return redirect("home")
    return render(request, "accounts/deactivate.html")
