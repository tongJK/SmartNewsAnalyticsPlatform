-- Initialize PostgreSQL with required extensions for Smart News Analytics Platform

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- Enable TimescaleDB (already available in timescaledb image)
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Enable vector extension (pgvector)
-- Note: This might need to be installed separately depending on the image
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE smart_news'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'smart_news');

-- Connect to the smart_news database
\c smart_news;

-- Enable extensions in the smart_news database
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "btree_gist";
CREATE EXTENSION IF NOT EXISTS "timescaledb";

-- Create custom functions for vector similarity (if pgvector is not available)
-- This is a fallback implementation using arrays
CREATE OR REPLACE FUNCTION cosine_similarity(a float[], b float[])
RETURNS float AS $$
DECLARE
    dot_product float := 0;
    norm_a float := 0;
    norm_b float := 0;
    i int;
BEGIN
    IF array_length(a, 1) != array_length(b, 1) THEN
        RETURN 0;
    END IF;
    
    FOR i IN 1..array_length(a, 1) LOOP
        dot_product := dot_product + (a[i] * b[i]);
        norm_a := norm_a + (a[i] * a[i]);
        norm_b := norm_b + (b[i] * b[i]);
    END LOOP;
    
    IF norm_a = 0 OR norm_b = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN dot_product / (sqrt(norm_a) * sqrt(norm_b));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create index for array similarity searches
CREATE OR REPLACE FUNCTION array_similarity_index(embedding float[])
RETURNS text AS $$
BEGIN
    -- Simple hash-based indexing for embeddings
    RETURN md5(array_to_string(embedding, ','));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Print success message
DO $$
BEGIN
    RAISE NOTICE 'Smart News Analytics Platform database initialized successfully!';
    RAISE NOTICE 'Available extensions:';
    RAISE NOTICE '- TimescaleDB for time-series data';
    RAISE NOTICE '- Full-text search with pg_trgm';
    RAISE NOTICE '- Custom vector similarity functions';
END $$;