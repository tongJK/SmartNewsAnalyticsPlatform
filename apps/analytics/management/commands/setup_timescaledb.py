"""
Management command to set up TimescaleDB hypertables and optimization
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
import logging

logger = logging.getLogger('analytics')


class Command(BaseCommand):
    help = 'Set up TimescaleDB hypertables and optimization for time-series analytics'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of hypertables (destructive)'
        )
        parser.add_argument(
            '--compression',
            action='store_true',
            help='Enable compression policies'
        )
        parser.add_argument(
            '--retention',
            type=int,
            default=365,
            help='Data retention period in days (default: 365)'
        )
    
    def handle(self, *args, **options):
        self.stdout.write("🔧 Setting up TimescaleDB hypertables...")
        
        try:
            with connection.cursor() as cursor:
                # Check if TimescaleDB extension is available
                cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'timescaledb';")
                if not cursor.fetchone():
                    raise CommandError("TimescaleDB extension is not installed")
                
                self.stdout.write("✅ TimescaleDB extension found")
                
                # Set up hypertables
                self._setup_hypertables(cursor, options['force'])
                
                # Configure compression if requested
                if options['compression']:
                    self._setup_compression(cursor)
                
                # Set up retention policies
                self._setup_retention_policies(cursor, options['retention'])
                
                # Create continuous aggregates
                self._setup_continuous_aggregates(cursor)
                
                # Show status
                self._show_status(cursor)
                
                self.stdout.write(
                    self.style.SUCCESS("🚀 TimescaleDB setup completed successfully!")
                )
                
        except Exception as e:
            raise CommandError(f"Failed to set up TimescaleDB: {e}")
    
    def _setup_hypertables(self, cursor, force=False):
        """Set up hypertables for time-series tables"""
        self.stdout.write("📊 Setting up hypertables...")
        
        hypertables = [
            {
                'table': 'article_metrics',
                'time_column': 'timestamp',
                'chunk_interval': '1 day',
                'description': 'Article engagement metrics'
            },
            {
                'table': 'user_engagement',
                'time_column': 'timestamp', 
                'chunk_interval': '1 day',
                'description': 'User behavior tracking'
            },
            {
                'table': 'trending_topics',
                'time_column': 'timestamp',
                'chunk_interval': '1 hour',
                'description': 'Trending topics detection'
            }
        ]
        
        for ht in hypertables:
            try:
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, [ht['table']])
                
                if not cursor.fetchone()[0]:
                    self.stdout.write(f"⚠️  Table {ht['table']} does not exist, skipping...")
                    continue
                
                # Check if already a hypertable
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM timescaledb_information.hypertables 
                        WHERE hypertable_name = %s
                    );
                """, [ht['table']])
                
                is_hypertable = cursor.fetchone()[0]
                
                if is_hypertable and not force:
                    self.stdout.write(f"✅ {ht['table']} is already a hypertable")
                    continue
                
                if is_hypertable and force:
                    self.stdout.write(f"🔄 Recreating hypertable {ht['table']}...")
                    # Note: This is destructive and should be used carefully
                    cursor.execute(f"DROP TABLE IF EXISTS {ht['table']} CASCADE;")
                
                # Create hypertable
                cursor.execute(f"""
                    SELECT create_hypertable('{ht['table']}', '{ht['time_column']}', 
                        if_not_exists => TRUE);
                """)
                
                # Set chunk time interval
                cursor.execute(f"""
                    SELECT set_chunk_time_interval('{ht['table']}', INTERVAL '{ht['chunk_interval']}');
                """)
                
                self.stdout.write(f"✅ Created hypertable: {ht['table']} ({ht['description']})")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Failed to create hypertable {ht['table']}: {e}")
                )
    
    def _setup_compression(self, cursor):
        """Set up compression policies for hypertables"""
        self.stdout.write("🗜️  Setting up compression policies...")
        
        compression_configs = [
            {
                'table': 'article_metrics',
                'compress_after': '7 days',
                'segment_by': 'article_id',
                'order_by': 'timestamp DESC'
            },
            {
                'table': 'user_engagement',
                'compress_after': '3 days',
                'segment_by': 'article_id',
                'order_by': 'timestamp DESC'
            },
            {
                'table': 'trending_topics',
                'compress_after': '1 day',
                'segment_by': 'topic',
                'order_by': 'timestamp DESC'
            }
        ]
        
        for config in compression_configs:
            try:
                # Enable compression on the hypertable
                cursor.execute(f"""
                    ALTER TABLE {config['table']} SET (
                        timescaledb.compress,
                        timescaledb.compress_segmentby = '{config['segment_by']}',
                        timescaledb.compress_orderby = '{config['order_by']}'
                    );
                """)
                
                # Add compression policy
                cursor.execute(f"""
                    SELECT add_compression_policy('{config['table']}', INTERVAL '{config['compress_after']}');
                """)
                
                self.stdout.write(f"✅ Compression enabled for {config['table']} (after {config['compress_after']})")
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Compression setup failed for {config['table']}: {e}")
                )
    
    def _setup_retention_policies(self, cursor, retention_days):
        """Set up data retention policies"""
        self.stdout.write(f"🗑️  Setting up retention policies ({retention_days} days)...")
        
        tables = ['article_metrics', 'user_engagement', 'trending_topics']
        
        for table in tables:
            try:
                cursor.execute(f"""
                    SELECT add_retention_policy('{table}', INTERVAL '{retention_days} days');
                """)
                
                self.stdout.write(f"✅ Retention policy set for {table} ({retention_days} days)")
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Retention policy failed for {table}: {e}")
                )
    
    def _setup_continuous_aggregates(self, cursor):
        """Set up continuous aggregates for real-time dashboards"""
        self.stdout.write("📈 Setting up continuous aggregates...")
        
        aggregates = [
            {
                'name': 'hourly_article_stats',
                'query': """
                    SELECT 
                        time_bucket('1 hour', timestamp) AS hour,
                        article_id,
                        SUM(views_count) as total_views,
                        SUM(shares_count) as total_shares,
                        AVG(read_time_avg) as avg_read_time,
                        COUNT(*) as data_points
                    FROM article_metrics
                    GROUP BY hour, article_id
                """,
                'refresh_interval': '30 minutes'
            },
            {
                'name': 'daily_engagement_stats',
                'query': """
                    SELECT 
                        time_bucket('1 day', timestamp) AS day,
                        COUNT(DISTINCT session_id) as unique_sessions,
                        AVG(time_spent) as avg_time_spent,
                        AVG(scroll_depth) as avg_scroll_depth,
                        COUNT(*) as total_interactions
                    FROM user_engagement
                    GROUP BY day
                """,
                'refresh_interval': '1 hour'
            }
        ]
        
        for agg in aggregates:
            try:
                # Drop existing aggregate if it exists
                cursor.execute(f"DROP MATERIALIZED VIEW IF EXISTS {agg['name']} CASCADE;")
                
                # Create continuous aggregate
                cursor.execute(f"""
                    CREATE MATERIALIZED VIEW {agg['name']}
                    WITH (timescaledb.continuous) AS
                    {agg['query']};
                """)
                
                # Add refresh policy
                cursor.execute(f"""
                    SELECT add_continuous_aggregate_policy('{agg['name']}',
                        start_offset => INTERVAL '2 hours',
                        end_offset => INTERVAL '30 minutes',
                        schedule_interval => INTERVAL '{agg['refresh_interval']}');
                """)
                
                self.stdout.write(f"✅ Continuous aggregate created: {agg['name']}")
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"⚠️  Continuous aggregate failed for {agg['name']}: {e}")
                )
    
    def _show_status(self, cursor):
        """Show TimescaleDB status and statistics"""
        self.stdout.write("\n📊 TimescaleDB Status:")
        
        try:
            # Show hypertables
            cursor.execute("""
                SELECT 
                    hypertable_name,
                    num_chunks,
                    table_size,
                    index_size,
                    total_size
                FROM timescaledb_information.hypertables
                ORDER BY hypertable_name;
            """)
            
            hypertables = cursor.fetchall()
            if hypertables:
                self.stdout.write("\n🏗️  Hypertables:")
                for ht in hypertables:
                    name, chunks, table_size, index_size, total_size = ht
                    self.stdout.write(f"  • {name}: {chunks} chunks, {self._format_bytes(total_size)} total")
            
            # Show compression stats
            cursor.execute("""
                SELECT 
                    chunk_name,
                    compression_status,
                    uncompressed_heap_size,
                    compressed_heap_size
                FROM timescaledb_information.chunks
                WHERE compression_status = 'Compressed'
                LIMIT 5;
            """)
            
            compressed_chunks = cursor.fetchall()
            if compressed_chunks:
                self.stdout.write("\n🗜️  Compression Status (sample):")
                for chunk in compressed_chunks:
                    name, status, uncompressed, compressed = chunk
                    if uncompressed and compressed:
                        ratio = (1 - compressed / uncompressed) * 100
                        self.stdout.write(f"  • {name}: {ratio:.1f}% compression")
            
            # Show continuous aggregates
            cursor.execute("""
                SELECT view_name, materialized_only
                FROM timescaledb_information.continuous_aggregates;
            """)
            
            aggregates = cursor.fetchall()
            if aggregates:
                self.stdout.write("\n📈 Continuous Aggregates:")
                for agg in aggregates:
                    self.stdout.write(f"  • {agg[0]}")
            
        except Exception as e:
            self.stdout.write(f"⚠️  Could not retrieve status: {e}")
    
    def _format_bytes(self, bytes_value):
        """Format bytes to human readable format"""
        if not bytes_value:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} PB"