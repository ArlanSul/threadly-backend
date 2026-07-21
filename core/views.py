from django.contrib.auth.models import User
from rest_framework import viewsets, generics, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Community, Membership, Post, Comment, Vote, Profile
from .serializers import (
    RegisterSerializer, CommunitySerializer, PostListSerializer,
    PostDetailSerializer, CommentSerializer, VoteSerializer, 
)
from .permissions import IsAuthorOrReadOnly


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class CommunityViewSet(viewsets.ModelViewSet):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    lookup_field = 'name'
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'display_name', 'description']

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def join(self, request, name=None):
        community = self.get_object()
        Membership.objects.get_or_create(user=request.user, community=community)
        return Response({'joined': True})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def leave(self, request, name=None):
        community = self.get_object()
        Membership.objects.filter(user=request.user, community=community).delete()
        return Response({'joined': False})

class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'body']

    def get_queryset(self):
        qs = Post.objects.all()
        community_name = self.request.query_params.get('community')
        if community_name:
            qs = qs.filter(community__name=community_name)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostListSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        qs = Comment.objects.all()
        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
    
class VoteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.validated_data.get('post')
        comment = serializer.validated_data.get('comment')
        value = serializer.validated_data['value']

        lookup = {'user': request.user, 'post': post, 'comment': comment}
        existing = Vote.objects.filter(**lookup).first()

        if existing and existing.value == value:
            existing.delete()
            return Response({'status': 'removed'})
        elif existing:
            existing.value = value
            existing.save()
            return Response({'status': 'updated', 'value': value})
        else:
            Vote.objects.create(**lookup, value=value)
            return Response({'status': 'created', 'value': value}, status=status.HTTP_201_CREATED)