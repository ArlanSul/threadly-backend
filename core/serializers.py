from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Community, Membership, Post, Comment, Vote, Profile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        Profile.objects.create(user=user)
        return user

class CommunitySerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ['id', 'name', 'display_name', 'description', 'created_by',
                  'created_at', 'member_count', 'is_member']
        read_only_fields = ['created_by']

    def get_member_count(self, obj):
        return obj.memberships.count()

    def get_is_member(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.memberships.filter(user=request.user).exists()

    def create(self, validated_data):
        request = self.context['request']
        community = Community.objects.create(created_by=request.user, **validated_data)
        Membership.objects.create(user=request.user, community=community)
        return community

class PostListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    community = serializers.SlugRelatedField(slug_field='name', queryset=Community.objects.all())
    score = serializers.IntegerField(source='score_agg', default=0, read_only=True)
    comment_count = serializers.IntegerField(source='comment_count_agg', default=0, read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'community', 'author', 'title', 'body', 'image',
                  'created_at', 'score', 'comment_count']
        read_only_fields = ['author']
        my_vote = serializers.SerializerMethodField()

        def get_my_vote(self, obj):
            request = self.context.get('request')
            if not request or not request.user.is_authenticated:
                return None
            vote = obj.votes.filter(user=request.user).first()
            return vote.value if vote else None

    def get_score(self, obj):
        return sum(v.value for v in obj.votes.all())

    def get_comment_count(self, obj):
        return obj.comments.count()

class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    score = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'parent', 'body', 'created_at', 'score', 'replies']
        read_only_fields = ['author']
        my_vote = serializers.SerializerMethodField()

        def get_my_vote(self, obj):
            request = self.context.get('request')
            if not request or not request.user.is_authenticated:
                return None
            vote = obj.votes.filter(user=request.user).first()
            return vote.value if vote else None

    def get_score(self, obj):
        return sum(v.value for v in obj.votes.all())

    def get_replies(self, obj):
        children = obj.replies.all()
        return CommentSerializer(children, many=True, context=self.context).data

class PostDetailSerializer(PostListSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ['comments']

    def get_comments(self, obj):
        top_level = obj.comments.filter(parent=None)
        return CommentSerializer(top_level, many=True, context=self.context).data

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'value', 'post', 'comment']

    def validate(self, data):
        post = data.get('post')
        comment = data.get('comment')
        if bool(post) == bool(comment):
            raise serializers.ValidationError('Provide exactly one of post or comment.')
        return data