from django.conf import settings
from rest_framework import generics, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import WatchedLocation
from .serializers import (
    OTPRequestSerializer,
    OTPVerifySerializer,
    UserSerializer,
    WatchedLocationSerializer,
)


class OTPRequestView(APIView):
    """Send a login code to the phone (via the Telegram bot)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "otp"
    serializer_class = OTPRequestSerializer

    def post(self, request):
        s = OTPRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        result = services.request_otp(s.validated_data["phone"])
        result.update(
            sent=result["channel"] != "none",
            expires_in=settings.OTP_TTL_SECONDS,
            bot_url=f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}",
        )
        return Response(result)


class OTPVerifyView(APIView):
    """Exchange phone + code for JWT tokens (creates the account on first login)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "otp_verify"
    serializer_class = OTPVerifySerializer

    def post(self, request):
        s = OTPVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        user, created = services.verify_otp(d["phone"], d["code"], d.get("name", ""))
        if not user.is_active:
            return Response({"detail": "Account disabled."}, status=403)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "is_new": created,
                "user": UserSerializer(user).data,
            }
        )


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class WatchedLocationViewSet(viewsets.ModelViewSet):
    serializer_class = WatchedLocationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return WatchedLocation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
