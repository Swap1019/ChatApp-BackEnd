from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import (
    IsAuthenticated,
)
from user.serializers import (
    UserSerializer,
)
from user.models import User



class HomeView(RetrieveAPIView):
    queryset = User.objects.all() 
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
