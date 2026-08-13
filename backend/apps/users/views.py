from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from rest_framework import filters, mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.exceptions import AuthenticationFailed
from .permissions import IsAdministrator
from .serializers import CurrentUserSerializer, UserCreateSerializer, UserSerializer
from apps.audit.mixins import AuditedWriteMixin
from apps.audit.models import AuditAction
from apps.audit.services import record_audit
from apps.notifications.models import NotificationLevel, NotificationType
from apps.notifications.services import NotificationService
from apps.sectors.models import UserSectorMembership

User = get_user_model()


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            request = self.context.get("request")
            record_audit(action=AuditAction.LOGIN_FAILED, description="Tentativa de login inválida", request=request, new_values={"username": str(attrs.get("username", ""))[:150]})
            raise
        data["user"] = CurrentUserSerializer(self.user, context=self.context).data
        return data


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            user = User.objects.filter(pk=response.data.get("user", {}).get("id")).first()
            record_audit(action=AuditAction.LOGIN, description="Login realizado", request=request, user=user, entity=user)
        return response


class LogoutView(APIView):
    # O refresh token é a credencial necessária para invalidar a sessão. Isso
    # permite logout correto mesmo quando o access token acabou de expirar.
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"refresh": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            refresh = RefreshToken(token)
            user = User.objects.filter(pk=refresh.get("user_id")).first()
            refresh.blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        record_audit(action=AuditAction.LOGOUT, description="Logout realizado", request=request, user=user, entity=user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(CurrentUserSerializer(request.user, context={"request": request}).data)


class UserViewSet(AuditedWriteMixin, mixins.ListModelMixin, mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.prefetch_related(
        "groups",
        Prefetch(
            "sector_memberships",
            queryset=UserSectorMembership.objects.effective().select_related("unit", "sector", "function").order_by("-is_primary", "sector__name"),
            to_attr="active_sector_memberships",
        ),
    ).all()
    permission_classes = [IsAdministrator]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "last_name", "username", "email"]
    ordering_fields = ["first_name", "last_name", "username", "email", "is_active", "last_login", "date_joined"]
    ordering = ["first_name", "last_name", "username"]
    audit_label = "usuário"
    audit_fields = ("username", "first_name", "last_name", "email", "is_active", "is_staff", "groups", "user_permissions")

    def perform_create(self, serializer):
        super().perform_create(serializer)
        user = serializer.instance
        NotificationService.create(user=user, title="Conta criada", message="Seu acesso ao sistema foi criado.", type=NotificationType.USER, level=NotificationLevel.SUCCESS, action_url="/perfil")

    def get_serializer_class(self):
        return UserCreateSerializer if self.action == "create" else UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self.request.query_params.get("is_active")
        group = self.request.query_params.get("group")
        if active in {"true", "false"}:
            queryset = queryset.filter(is_active=active == "true")
        if group:
            queryset = queryset.filter(groups__name=group)
        return queryset.distinct()
