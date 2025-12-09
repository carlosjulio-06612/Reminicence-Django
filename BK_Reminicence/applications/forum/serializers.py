from rest_framework import serializers
from .models import Category, Topic, Post

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# Importante: Definimos PostSerializer PRIMERO para que TopicSerializer pueda usarlo
class PostSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    
    class Meta:
        model = Post
        fields = ['id', 'topic', 'author', 'author_username', 'content', 'created_at', 'updated_at']
        read_only_fields = ['author']

class TopicSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    # ESTO ES LO QUE FALTABA: Incluir los posts anidados
    posts = PostSerializer(many=True, read_only=True) 

    class Meta:
        model = Topic
        # Agregamos 'posts' a los campos
        fields = ['id', 'category', 'title', 'author', 'author_username', 'created_at', 'is_closed', 'posts']
        read_only_fields = ['author']

