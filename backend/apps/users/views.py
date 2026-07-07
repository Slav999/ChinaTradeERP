from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .access import ensure_default_access_structure
from .cookies import clear_auth_cookies, set_auth_cookies
from .models import AccessRole, CompanyMembership, Department, Invitation
from .serializers import (
    AcceptInvitationSerializer,
    AccessRoleSerializer,
    CompanyMembershipSerializer,
    CustomTokenObtainPairSerializer,
    DepartmentSerializer,
    EmployeeMembershipSerializer,
    InvitationPreviewSerializer,
    InvitationSerializer,
    InviteUserSerializer,
    RegisterSerializer,
    SwitchCompanySerializer,
    UserSerializer,
    code_matches,
    generate_numeric_code,
    hash_code,
    validate_password_strength,
)
from .throttles import (
    EmailCodeThrottle,
    InvitationAcceptThrottle,
    InvitationManageThrottle,
    LoginThrottle,
    PasswordResetThrottle,
    RegisterThrottle,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegisterThrottle]

    def perform_create(self, serializer):
        email = serializer.validated_data.get('email', '').lower()
        serializer.save(email=email)


class InviteUserView(generics.CreateAPIView):
    serializer_class = InviteUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvitationManageThrottle]


class InvitationListCreateView(generics.ListCreateAPIView):
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [InvitationManageThrottle]

    def get_queryset(self):
        if not self.request.user.is_company_admin:
            return Invitation.objects.none()
        return Invitation.objects.select_related(
            'company', 'department', 'access_role', 'invited_by'
        ).filter(
            company=self.request.user.company,
            status=Invitation.STATUS_PENDING,
        )


class InvitationPreviewView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InvitationAcceptThrottle]

    def get(self, request, token):
        invitation = self.get_invitation(token)
        if not invitation:
            return Response({"detail": "Invitation is invalid or expired."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InvitationPreviewSerializer(invitation).data)

    def get_invitation(self, token):
        try:
            invitation = Invitation.objects.select_related(
                'company', 'department', 'access_role'
            ).get(token_hash=Invitation.hash_token(token))
        except Invitation.DoesNotExist:
            return None
        invitation.mark_expired_if_needed()
        if invitation.status != Invitation.STATUS_PENDING:
            return None
        return invitation


class AcceptInvitationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [InvitationAcceptThrottle]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Invitation accepted."}, status=status.HTTP_201_CREATED)


class DepartmentListView(generics.ListAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Department.objects.filter(company=self.request.user.company)


class AccessRoleListView(generics.ListAPIView):
    serializer_class = AccessRoleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.company_id:
            ensure_default_access_structure(self.request.user.company)
        return AccessRole.objects.prefetch_related('permissions').filter(company=self.request.user.company)


class CompanyMembershipListView(generics.ListAPIView):
    serializer_class = CompanyMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.company_memberships.select_related(
            'company', 'department', 'access_role'
        ).filter(status='active')


class EmployeeListView(generics.ListAPIView):
    serializer_class = EmployeeMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_company_admin:
            return self.request.user.company_memberships.none()

        employee_status = self.request.query_params.get('status')
        queryset = self.request.user.company.memberships.select_related(
            'user', 'company', 'company__created_by', 'department', 'access_role', 'disabled_by'
        ).order_by('status', 'user__last_name', 'user__first_name', 'user__email')

        if employee_status in {CompanyMembership.STATUS_ACTIVE, CompanyMembership.STATUS_DISABLED}:
            queryset = queryset.filter(status=employee_status)

        return queryset


class DismissEmployeeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_company_admin:
            return Response({"detail": "Only company admins can dismiss employees."}, status=status.HTTP_403_FORBIDDEN)

        try:
            membership = request.user.company.memberships.select_related(
                'user', 'company', 'company__created_by', 'department', 'access_role'
            ).get(pk=pk)
        except CompanyMembership.DoesNotExist:
            return Response({"detail": "Employee was not found."}, status=status.HTTP_404_NOT_FOUND)

        if membership.user_id == request.user.id:
            return Response({"detail": "You cannot dismiss yourself."}, status=status.HTTP_400_BAD_REQUEST)

        if membership.is_company_admin and membership.company.created_by_id != request.user.id:
            return Response(
                {"detail": "Only the company creator can dismiss company admins."},
                status=status.HTTP_403_FORBIDDEN,
            )

        membership.status = CompanyMembership.STATUS_DISABLED
        membership.disabled_at = timezone.now()
        membership.disabled_by = request.user
        membership.disable_reason = request.data.get('reason', '').strip()
        membership.is_company_admin = False
        membership.save(update_fields=[
            'status', 'disabled_at', 'disabled_by',
            'disable_reason', 'is_company_admin',
        ])

        if membership.user.company_id == membership.company_id:
            next_membership = membership.user.company_memberships.select_related(
                'company', 'department', 'access_role'
            ).filter(status=CompanyMembership.STATUS_ACTIVE).exclude(pk=membership.pk).first()
            if next_membership:
                next_membership.apply_to_user()
            else:
                membership.user.company = None
                membership.user.role = 'viewer'
                membership.user.department_ref = None
                membership.user.department = ''
                membership.user.access_role = None
                membership.user.position = ''
                membership.user.is_company_admin = False
                membership.user.save(update_fields=[
                    'company', 'role', 'department_ref', 'department',
                    'access_role', 'position', 'is_company_admin',
                ])

        return Response(EmployeeMembershipSerializer(membership).data)


class SwitchCompanyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SwitchCompanySerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        request.user.refresh_from_db()
        return Response(UserSerializer(request.user).data)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        access_token = response.data.get('access')
        refresh_token = response.data.get('refresh')
        response.data = {'detail': 'Login successful.'}
        set_auth_cookies(response, access_token, refresh_token, request=request)
        return response


class CookieTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh') or request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh_token:
            response = Response({"detail": "Refresh token is missing."}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(response)
            return response

        serializer = self.get_serializer(data={'refresh': refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError):
            response = Response({"detail": "Refresh token is invalid or expired."}, status=status.HTTP_401_UNAUTHORIZED)
            clear_auth_cookies(response)
            return response

        data = serializer.validated_data
        response = Response({"detail": "Token refreshed."}, status=status.HTTP_200_OK)
        set_auth_cookies(response, data.get('access'), data.get('refresh'), request=request)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user


class SessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh") or request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        response = Response(status=status.HTTP_205_RESET_CONTENT)
        clear_auth_cookies(response)
        return response


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [EmailCodeThrottle]

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get("code")
        if not email or not code:
            return Response({"error": "Email and code are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response({"error": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        code_is_valid = code_matches(user.verification_code, code)
        code_not_expired = (
            not user.verification_code_expires_at
            or user.verification_code_expires_at >= timezone.now()
        )
        if not (code_is_valid and code_not_expired):
            return Response({"error": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_email_verified = True
        user.verification_code = ""
        user.verification_code_expires_at = None
        user.save(update_fields=['is_email_verified', 'verification_code', 'verification_code_expires_at'])
        return Response({"message": "Email verified."}, status=status.HTTP_200_OK)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        key = f"forgot_password:{ip}"
        attempts = cache.get(key, 0)

        if attempts >= 5:
            return Response({"detail": "Too many attempts. Please wait."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        cache.set(key, attempts + 1, timeout=60)

        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
            code = generate_numeric_code()
            user.reset_code = hash_code(code)
            user.reset_code_expires_at = timezone.now() + timezone.timedelta(minutes=15)
            user.save(update_fields=['reset_code', 'reset_code_expires_at'])

            send_mail(
                subject='Password reset code',
                message=f'Your code: {code}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        except User.DoesNotExist:
            pass

        return Response({"detail": "If the email exists, a reset code will be sent."})


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        key = f"reset_password:{ip}"
        attempts = cache.get(key, 0)

        if attempts >= 5:
            return Response({"detail": "Too many attempts. Please wait."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        cache.set(key, attempts + 1, timeout=60)

        email = request.data.get('email')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        if not all([email, code, new_password]):
            return Response({"detail": "All fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password_strength(new_password)
        except Exception as exc:
            detail = exc.detail[0] if hasattr(exc, 'detail') else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email.lower())
        except User.DoesNotExist:
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        code_is_valid = code_matches(user.reset_code, code)
        code_not_expired = user.reset_code_expires_at and user.reset_code_expires_at >= timezone.now()
        if not (code_is_valid and code_not_expired):
            return Response({"detail": "Invalid code."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.reset_code = ''
        user.reset_code_expires_at = None
        user.save()

        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)
