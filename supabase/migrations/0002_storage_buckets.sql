-- Storage buckets for crawl artifacts and generated reports.
-- Created as private buckets; the backend serves content via signed URLs.

insert into storage.buckets (id, name, public)
values
    ('screenshots', 'screenshots', false),
    ('html',        'html',        false),
    ('reports',     'reports',     false)
on conflict (id) do nothing;
