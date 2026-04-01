from rest_framework import serializers
from .models import Article, ArticleView


class ArticleSerializer(serializers.ModelSerializer):
    """
    Main article serializer with all fields
    """
    engagement_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'content', 'summary', 'author', 'source_url',
            'published_at', 'created_at', 'updated_at', 'views', 'shares',
            'category', 'tags', 'language', 'engagement_score'
        ]
        read_only_fields = ['views', 'shares', 'created_at', 'updated_at']


class ArticleListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for article lists
    Excludes heavy fields like content and embedding
    """
    engagement_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'summary', 'author', 'published_at',
            'views', 'shares', 'category', 'tags', 'language', 'engagement_score'
        ]


class ArticleSearchSerializer(serializers.ModelSerializer):
    """
    Serializer for search results with similarity score
    """
    similarity_score = serializers.FloatField(read_only=True, required=False)
    engagement_score = serializers.ReadOnlyField()
    
    class Meta:
        model = Article
        fields = [
            'id', 'title', 'summary', 'author', 'published_at',
            'views', 'shares', 'category', 'tags', 'language',
            'engagement_score', 'similarity_score'
        ]


class ArticleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new articles
    """
    
    class Meta:
        model = Article
        fields = [
            'title', 'content', 'summary', 'author', 'source_url',
            'published_at', 'category', 'tags', 'language'
        ]
    
    def validate_title(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Title must be at least 10 characters long")
        return value.strip()
    
    def validate_content(self, value):
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Content must be at least 100 characters long")
        return value.strip()


class SearchQuerySerializer(serializers.Serializer):
    """
    Serializer for search query parameters
    """
    SEARCH_TYPES = [
        ('text', 'Full-text search'),
        ('semantic', 'Semantic/vector search'),
        ('hybrid', 'Hybrid search (text + semantic)'),
    ]
    
    query = serializers.CharField(max_length=500, help_text="Search query")
    search_type = serializers.ChoiceField(
        choices=SEARCH_TYPES,
        default='hybrid',
        help_text="Type of search to perform"
    )
    category = serializers.CharField(max_length=100, required=False, help_text="Filter by category")
    language = serializers.CharField(max_length=10, required=False, help_text="Filter by language")
    limit = serializers.IntegerField(min_value=1, max_value=100, default=20, help_text="Number of results")


class ArticleViewSerializer(serializers.ModelSerializer):
    """
    Serializer for article view tracking
    """
    
    class Meta:
        model = ArticleView
        fields = ['article', 'timestamp', 'ip_address', 'user_agent', 'referrer']
        read_only_fields = ['timestamp']