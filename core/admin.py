from django.contrib import admin

from .models import Community, Membership, Post, Comment, Vote, Profile

admin.site.register(Community)
admin.site.register(Membership)
admin.site.register(Post)
admin.site.register(Comment)
admin.site.register(Vote)
admin.site.register(Profile)