INSERT INTO sources (name, feed_url, language) VALUES
    ('BBC World',            'https://feeds.bbci.co.uk/news/world/rss.xml',                 'en'),
    ('BBC Technology',       'https://feeds.bbci.co.uk/news/technology/rss.xml',            'en'),
    ('Al Jazeera',           'https://www.aljazeera.com/xml/rss/all.xml',                   'en'),
    ('Deutsche Welle',       'https://rss.dw.com/rdf/rss-en-all',                           'en'),
    ('Sky News World',       'https://feeds.skynews.com/feeds/rss/world.xml',               'en'),
    ('Arab News',            'https://www.arabnews.com/rss.xml',                            'en'),
    ('NPR',                  'https://feeds.npr.org/1001/rss.xml',                         'en'),
    ('The Guardian World',   'https://www.theguardian.com/world/rss',                       'en'),
    ('CNN Top Stories',      'http://rss.cnn.com/rss/edition.rss',                         'en'),
    ('NYT World',            'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',      'en'),
    ('France 24',            'https://www.france24.com/fr/rss',                            'fr'),
    ('RFI',                  'https://www.rfi.fr/fr/rss',                                  'fr'),
    ('France TV Info',       'https://www.francetvinfo.fr/titres.rss',                      'fr'),
    ('BBC Arabic',           'https://feeds.bbci.co.uk/arabic/news/rss.xml',                'ar'),
    ('BBC Arabic Middle East','https://feeds.bbci.co.uk/arabic/middleeast/rss.xml',         'ar'),
    ('Asharq Al-Awsat',      'https://aawsat.com/feed/',                                    'ar'),
    ('Sky News Arabia',      'https://www.skynewsarabia.com/rss',                           'ar'),
    ('Hespress',             'https://www.hespress.com/rss',                                'ar')
ON CONFLICT (feed_url) DO NOTHING;

SELECT cron.schedule(
    'wassla-ingest',
    '*/15 * * * *',
    $$SELECT net.http_post(
        url := 'http://pipeline:8000/ingest/run',
        body := jsonb_build_object('max_items', 50),
        headers := jsonb_build_object(
            'Content-Type', 'application/json',
            'X-Ingest-Token', current_setting('app.ingest_token')
        ),
        timeout_milliseconds := 300000
    )$$
);
