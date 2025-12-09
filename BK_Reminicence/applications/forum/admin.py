from django.contrib import admin
from .models import Category, Topic, Post

# Configuración para Categorías
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

# Configuración para Temas
class PostInline(admin.TabularInline):
    model = Post
    extra = 1

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'created_at', 'is_closed')
    list_filter = ('category', 'is_closed', 'created_at')
    search_fields = ('title', 'author__username')
    inlines = [PostInline] # Esto permite ver las respuestas dentro del tema

# Configuración para Posts (Opcional, por si quieres verlos sueltos)
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('short_content', 'topic', 'author', 'created_at')
    
    def short_content(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content