from rest_framework import viewsets, permissions
from .permissions import IsOwnerOrReadOnly
from .models import Category, Topic, Post
from .serializers import CategorySerializer, TopicSerializer, PostSerializer

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]

class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.all().order_by('-created_at')
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(author=self.request.user)

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    def perform_create(self, serializer): serializer.save(author=self.request.user)