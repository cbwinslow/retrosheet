-- Content Management Schema
-- Database schema for generated articles, templates, and content metadata

-- Create content schema
CREATE SCHEMA IF NOT EXISTS content;

-- Set permissions
GRANT USAGE ON SCHEMA content TO PUBLIC;
GRANT CREATE ON SCHEMA content TO PUBLIC;

-- Generated articles table
CREATE TABLE IF NOT EXISTS content.articles (
    article_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    template_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    model_outputs JSONB,
    context_data JSONB,
    generation_metadata JSONB,
    
    -- Generation tracking
    model_used TEXT,
    tokens_used INTEGER,
    generation_time_seconds FLOAT,
    quality_score FLOAT,
    
    -- Status and timestamps
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'review', 'published', 'archived')),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Content metadata
    word_count INTEGER GENERATED ALWAYS AS (array_length(string_to_array(content, ' '), 1)) STORED,
    character_count INTEGER GENERATED ALWAYS AS (length(content)) STORED,
    
    -- Foreign keys (optional relationships)
    game_pk INTEGER,
    player_id TEXT,
    team_id TEXT,
    
    -- Constraints
    CONSTRAINT articles_title_not_empty CHECK (length(trim(title)) > 0),
    CONSTRAINT articles_content_not_empty CHECK (length(trim(content)) > 0),
    CONSTRAINT articles_generation_time_positive CHECK (generation_time_seconds IS NULL OR generation_time_seconds > 0),
    CONSTRAINT articles_quality_score_range CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1))
);

-- Template definitions table
CREATE TABLE IF NOT EXISTS content.templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,
    content_type TEXT NOT NULL,
    
    -- Template metadata
    variables JSONB,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT templates_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT templates_content_not_empty CHECK (length(trim(template_content)) > 0),
    CONSTRAINT templates_version_positive CHECK (version > 0)
);

-- Content generation logs table
CREATE TABLE IF NOT EXISTS content.generation_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES content.articles(article_id) ON DELETE SET NULL,
    template_id UUID REFERENCES content.templates(template_id) ON DELETE SET NULL,
    
    -- Request details
    request_data JSONB NOT NULL,
    template_name TEXT NOT NULL,
    content_type TEXT NOT NULL,
    
    -- Response details
    response_content TEXT,
    model_used TEXT,
    tokens_used INTEGER,
    generation_time_seconds FLOAT,
    
    -- Status and error handling
    status TEXT NOT NULL CHECK (status IN ('success', 'error', 'timeout', 'cancelled')),
    error_message TEXT,
    error_details JSONB,
    
    -- Quality metrics
    quality_score FLOAT,
    validation_results JSONB,
    
    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT generation_logs_time_positive CHECK (generation_time_seconds IS NULL OR generation_time_seconds > 0),
    CONSTRAINT generation_logs_quality_range CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1))
);

-- Scheduled tasks table
CREATE TABLE IF NOT EXISTS content.scheduled_tasks (
    task_id TEXT PRIMARY KEY,
    template_name TEXT NOT NULL,
    context_data JSONB,
    content_type TEXT,
    
    -- Scheduling details
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    
    -- Execution tracking
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Error handling
    error_message TEXT,
    last_error_at TIMESTAMP WITH TIME ZONE,
    
    -- Result tracking
    article_id UUID REFERENCES content.articles(article_id) ON DELETE SET NULL,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT scheduled_tasks_retry_count_valid CHECK (retry_count >= 0 AND retry_count <= max_retries),
    CONSTRAINT scheduled_tasks_max_retries_positive CHECK (max_retries > 0)
);

-- Content performance metrics table
CREATE TABLE IF NOT EXISTS content.content_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES content.articles(article_id) ON DELETE CASCADE,
    
    -- Engagement metrics
    views INTEGER DEFAULT 0,
    unique_views INTEGER DEFAULT 0,
    read_time_seconds FLOAT,
    bounce_rate FLOAT,
    
    -- Interaction metrics
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    click_through_rate FLOAT,
    
    -- Quality metrics
    readability_score FLOAT,
    sentiment_score FLOAT,
    factual_accuracy_score FLOAT,
    
    -- Business metrics
    revenue_generated NUMERIC(10, 2) DEFAULT 0,
    conversion_rate FLOAT,
    
    -- Timestamps
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT content_metrics_views_non_negative CHECK (views >= 0),
    CONSTRAINT content_metrics_unique_views_valid CHECK (unique_views >= 0 AND unique_views <= views),
    CONSTRAINT content_metrics_read_time_positive CHECK (read_time_seconds IS NULL OR read_time_seconds > 0),
    CONSTRAINT content_metrics_bounce_rate_valid CHECK (bounce_rate IS NULL OR (bounce_rate >= 0 AND bounce_rate <= 1)),
    CONSTRAINT content_metrics_rates_valid CHECK (
        click_through_rate IS NULL OR (click_through_rate >= 0 AND click_through_rate <= 1)
    ),
    CONSTRAINT content_metrics_scores_valid CHECK (
        readability_score IS NULL OR (readability_score >= 0 AND readability_score <= 1)
    ),
    CONSTRAINT content_metrics_sentiment_valid CHECK (
        sentiment_score IS NULL OR (sentiment_score >= -1 AND sentiment_score <= 1)
    ),
    CONSTRAINT content_metrics_accuracy_valid CHECK (
        factual_accuracy_score IS NULL OR (factual_accuracy_score >= 0 AND factual_accuracy_score <= 1)
    ),
    CONSTRAINT content_metrics_conversion_valid CHECK (
        conversion_rate IS NULL OR (conversion_rate >= 0 AND conversion_rate <= 1)
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_articles_status ON content.articles(status);
CREATE INDEX IF NOT EXISTS idx_articles_template ON content.articles(template_name);
CREATE INDEX IF NOT EXISTS idx_articles_generated_at ON content.articles(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_game_pk ON content.articles(game_pk) WHERE game_pk IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_articles_player_id ON content.articles(player_id) WHERE player_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_articles_content_type ON content.articles(content_type);

CREATE INDEX IF NOT EXISTS idx_templates_name ON content.templates(name);
CREATE INDEX IF NOT EXISTS idx_templates_active ON content.templates(is_active);
CREATE INDEX IF NOT EXISTS idx_templates_content_type ON content.templates(content_type);

CREATE INDEX IF NOT EXISTS idx_generation_logs_status ON content.generation_logs(status);
CREATE INDEX IF NOT EXISTS idx_generation_logs_template ON content.generation_logs(template_name);
CREATE INDEX IF NOT EXISTS idx_generation_logs_started_at ON content.generation_logs(started_at DESC);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_status ON content.scheduled_tasks(status);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_scheduled_time ON content.scheduled_tasks(scheduled_time);
CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_template ON content.scheduled_tasks(template_name);

CREATE INDEX IF NOT EXISTS idx_content_metrics_article ON content.content_metrics(article_id);
CREATE INDEX IF NOT EXISTS idx_content_metrics_measured_at ON content.content_metrics(measured_at DESC);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION content.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_articles_updated_at BEFORE UPDATE ON content.articles
    FOR EACH ROW EXECUTE FUNCTION content.update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON content.templates
    FOR EACH ROW EXECUTE FUNCTION content.update_updated_at_column();

CREATE TRIGGER update_scheduled_tasks_updated_at BEFORE UPDATE ON content.scheduled_tasks
    FOR EACH ROW EXECUTE FUNCTION content.update_updated_at_column();

-- Create template usage trigger
CREATE OR REPLACE FUNCTION content.increment_template_usage()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE content.templates 
    SET usage_count = usage_count + 1,
        last_used_at = NOW()
    WHERE name = NEW.template_name;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER increment_template_usage_trigger AFTER INSERT ON content.articles
    FOR EACH ROW EXECUTE FUNCTION content.increment_template_usage();

-- Insert default templates
INSERT INTO content.templates (name, description, template_content, content_type, variables) VALUES
(
    'game-preview',
    'Game preview article template',
    '# {{ title }}

## {{ game.home_team }} vs {{ game.away_team }}

**Game Time:** {{ game.game_time }}  
**Venue:** {{ game.venue }}

### Preview

The {{ game.home_team }} host the {{ game.away_team }} today in what should be an exciting matchup. Our models give the {{ game.home_team if game.home_win_prob > 0.5 else game.away_team }} a {{ (game.home_win_prob if game.home_win_prob > 0.5 else (1 - game.home_win_prob)) | percentage }} chance to win.

### Key Factors

- **Home Field Advantage:** Playing at {{ game.venue }}
- **Expected Runs:** {{ game.total_runs_expected }} total runs projected
- **Win Probability:** {{ game.home_win_prob | percentage }} for home team

### Prediction

Our hierarchical prediction system favors the {{ game.home_team if game.home_win_prob > 0.5 else game.away_team }} in this contest. The model accounts for recent performance, pitching matchups, and historical trends.

*This analysis was generated using advanced statistical models and real-time data.*',
    'game-preview',
    '["title", "game"]'
),
(
    'player-analysis',
    'Player performance analysis template',
    '# {{ title }}

## {{ player.name }} Performance Analysis

**Team:** {{ player.team }}  
**Current Season Stats:** {{ player.avg | number }} AVG, {{ player.hr }} HR, {{ player.rbi }} RBI  
**OPS:** {{ player.ops | number }}

### Season Overview

{{ player.name }} is having a {{ "strong" if player.ops > 0.900 else "solid" if player.ops > 0.800 else "struggling" }} season with an OPS of {{ player.ops | number }}. The {{ player.avg | percentage }} batting average and {{ player.hr }} home runs show {{ player.name }}''s power and contact abilities.

### Key Metrics

- **Batting Average:** {{ player.avg | number }}
- **Home Runs:** {{ player.hr }}
- **RBI:** {{ player.rbi }}
- **On-base Plus Slugging:** {{ player.ops | number }}

### Analysis

Based on these metrics, {{ player.name }} is performing at a {{ "elite" if player.ops > 0.900 else "above-average" if player.ops > 0.800 else "below-average" }} level offensively. The combination of power and contact makes {{ player.name }} a valuable contributor to the {{ player.team }}.

*This analysis uses advanced statistics and historical performance data.*',
    'player-analysis',
    '["title", "player"]'
) ON CONFLICT (name) DO NOTHING;

-- Grant permissions on tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA content TO PUBLIC;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA content TO PUBLIC;

-- Create views for common queries
CREATE OR REPLACE VIEW content.published_articles AS
SELECT 
    article_id,
    title,
    template_name,
    content_type,
    published_at,
    word_count,
    character_count,
    game_pk,
    player_id,
    team_id
FROM content.articles
WHERE status = 'published'
ORDER BY published_at DESC;

CREATE OR REPLACE VIEW content.template_usage_stats AS
SELECT 
    t.name,
    t.description,
    t.content_type,
    t.usage_count,
    t.last_used_at,
    COUNT(a.article_id) as total_articles,
    AVG(a.word_count) as avg_word_count,
    AVG(a.generation_time_seconds) as avg_generation_time
FROM content.templates t
LEFT JOIN content.articles a ON t.name = a.template_name
WHERE t.is_active = true
GROUP BY t.template_id, t.name, t.description, t.content_type, t.usage_count, t.last_used_at
ORDER BY t.usage_count DESC;

COMMIT;
