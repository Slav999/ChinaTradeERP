from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


class RegisterThrottle(AnonRateThrottle):
    scope = 'register'


class EmailCodeThrottle(AnonRateThrottle):
    scope = 'email_code'


class PasswordResetThrottle(AnonRateThrottle):
    scope = 'password_reset'


class InvitationAcceptThrottle(AnonRateThrottle):
    scope = 'invitation_accept'


class InvitationManageThrottle(UserRateThrottle):
    scope = 'invitation_manage'
