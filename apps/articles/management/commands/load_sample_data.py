from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from apps.articles.models import Article
from apps.analytics.models import ArticleMetrics


class Command(BaseCommand):
    help = 'Load sample data for testing the Smart News Analytics Platform'

    def add_arguments(self, parser):
        parser.add_argument(
            '--articles',
            type=int,
            default=20,
            help='Number of sample articles to create'
        )

    def handle(self, *args, **options):
        num_articles = options['articles']
        
        self.stdout.write(f'Creating {num_articles} sample articles...')
        
        # Sample article data
        sample_articles = [
            {
                'title': 'Artificial Intelligence Revolutionizes Healthcare Industry',
                'content': 'Recent advances in artificial intelligence are transforming healthcare delivery. Machine learning algorithms can now diagnose diseases with unprecedented accuracy, while AI-powered robots assist in complex surgeries. This technological revolution promises to improve patient outcomes and reduce healthcare costs globally.',
                'category': 'technology',
                'tags': ['AI', 'healthcare', 'machine learning', 'technology'],
                'author': 'Dr. Sarah Johnson'
            },
            {
                'title': 'Climate Change: New Research Shows Accelerating Ice Melt',
                'content': 'Scientists have discovered that polar ice caps are melting at twice the previously estimated rate. This alarming finding suggests that sea level rise could occur much faster than anticipated, threatening coastal cities worldwide. Urgent action is needed to address this climate emergency.',
                'category': 'environment',
                'tags': ['climate change', 'environment', 'polar ice', 'sea level'],
                'author': 'Environmental Research Team'
            },
            {
                'title': 'Breakthrough in Quantum Computing Achieved',
                'content': 'Researchers at leading universities have achieved a major breakthrough in quantum computing, demonstrating quantum supremacy in solving complex mathematical problems. This advancement could revolutionize cryptography, drug discovery, and financial modeling in the coming decades.',
                'category': 'technology',
                'tags': ['quantum computing', 'technology', 'research', 'breakthrough'],
                'author': 'Prof. Michael Chen'
            },
            {
                'title': 'Global Economy Shows Signs of Recovery',
                'content': 'Economic indicators suggest a strong recovery is underway following recent global challenges. Employment rates are rising, consumer confidence is improving, and international trade is rebounding. Economists remain cautiously optimistic about sustained growth.',
                'category': 'business',
                'tags': ['economy', 'business', 'recovery', 'employment'],
                'author': 'Financial Times Staff'
            },
            {
                'title': 'Space Exploration: Mars Mission Reveals New Discoveries',
                'content': 'The latest Mars rover mission has uncovered evidence of ancient water systems and potential signs of past microbial life. These findings bring us closer to understanding whether life once existed on the Red Planet and inform future human exploration missions.',
                'category': 'science',
                'tags': ['space', 'Mars', 'exploration', 'science'],
                'author': 'NASA Research Team'
            },
            {
                'title': 'Renewable Energy Adoption Reaches Record Highs',
                'content': 'Solar and wind energy installations have reached unprecedented levels globally. Countries are rapidly transitioning away from fossil fuels, driven by falling costs and environmental concerns. This shift is creating new jobs and reducing carbon emissions worldwide.',
                'category': 'environment',
                'tags': ['renewable energy', 'solar', 'wind', 'environment'],
                'author': 'Green Energy Consortium'
            },
            {
                'title': 'Medical Breakthrough: Gene Therapy Shows Promise',
                'content': 'Clinical trials for a new gene therapy treatment have shown remarkable success in treating previously incurable genetic disorders. Patients are experiencing significant improvements, offering hope to millions suffering from rare diseases.',
                'category': 'health',
                'tags': ['gene therapy', 'medical', 'health', 'treatment'],
                'author': 'Medical Research Institute'
            },
            {
                'title': 'Cybersecurity Threats Evolve with AI Technology',
                'content': 'As artificial intelligence becomes more sophisticated, cybercriminals are adapting their tactics. Security experts warn of new AI-powered attacks while developing advanced defense systems to protect critical infrastructure and personal data.',
                'category': 'technology',
                'tags': ['cybersecurity', 'AI', 'technology', 'security'],
                'author': 'Cybersecurity Weekly'
            },
            {
                'title': 'Education Revolution: Online Learning Transforms Schools',
                'content': 'The shift to digital education has permanently changed how students learn. Interactive online platforms, virtual reality classrooms, and AI tutors are enhancing educational outcomes and making quality education more accessible globally.',
                'category': 'education',
                'tags': ['education', 'online learning', 'technology', 'schools'],
                'author': 'Education Today'
            },
            {
                'title': 'Sustainable Agriculture Feeds Growing Population',
                'content': 'Innovative farming techniques are helping feed the worlds growing population while protecting the environment. Vertical farms, precision agriculture, and drought-resistant crops are revolutionizing food production and reducing environmental impact.',
                'category': 'agriculture',
                'tags': ['agriculture', 'sustainability', 'farming', 'food'],
                'author': 'Agricultural Science Journal'
            }
        ]
        
        created_articles = []
        
        for i in range(num_articles):
            # Use sample data or generate variations
            if i < len(sample_articles):
                data = sample_articles[i]
            else:
                # Generate variations of existing articles
                base = sample_articles[i % len(sample_articles)]
                data = {
                    'title': f"{base['title']} - Update {i - len(sample_articles) + 1}",
                    'content': f"Updated: {base['content']} This is an updated version with new insights and developments.",
                    'category': base['category'],
                    'tags': base['tags'],
                    'author': base['author']
                }
            
            # Create article with random published date (last 30 days)
            published_at = timezone.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            article = Article.objects.create(
                title=data['title'],
                content=data['content'],
                category=data['category'],
                tags=data['tags'],
                author=data['author'],
                published_at=published_at,
                views=random.randint(10, 1000),
                shares=random.randint(0, 50)
            )
            
            created_articles.append(article)
            
            # Create some sample metrics for each article
            for days_ago in range(random.randint(1, 7)):
                metric_time = published_at + timedelta(days=days_ago)
                if metric_time <= timezone.now():
                    ArticleMetrics.objects.create(
                        article=article,
                        timestamp=metric_time,
                        views_count=random.randint(5, 100),
                        shares_count=random.randint(0, 10),
                        comments_count=random.randint(0, 5),
                        read_time_avg=random.uniform(30, 300),  # 30 seconds to 5 minutes
                        bounce_rate=random.uniform(0.2, 0.8),
                        traffic_source=random.choice(['direct', 'social', 'search', 'referral']),
                        referrer_domain=random.choice(['google.com', 'facebook.com', 'twitter.com', 'direct'])
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(created_articles)} articles with sample metrics!'
            )
        )
        
        # Display summary
        self.stdout.write('\nSample data summary:')
        self.stdout.write(f'- Total articles: {Article.objects.count()}')
        self.stdout.write(f'- Total metrics records: {ArticleMetrics.objects.count()}')
        self.stdout.write(f'- Categories: {", ".join(Article.objects.values_list("category", flat=True).distinct())}')
        
        self.stdout.write('\nYou can now:')
        self.stdout.write('1. Start the development server: python manage.py runserver')
        self.stdout.write('2. Visit the API at: http://localhost:8000/api/')
        self.stdout.write('3. Access admin at: http://localhost:8000/admin/ (admin/admin)')
        self.stdout.write('4. Test search: POST to http://localhost:8000/api/articles/search/')