from django.db import connections
from django.db.utils import OperationalError
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    database = serializers.CharField()

class HealthCheckView(APIView):
    def get(self, request):
        db_status = "ok"
        try:
            connections["default"].cursor()
        except OperationalError:
            db_status = "fail"

        return Response({
            "status": "ok",
            "message": "Application is running smoothly",
            "database": db_status
        }, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        return HealthCheckResponseSerializer