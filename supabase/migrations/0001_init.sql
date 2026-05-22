-- Pattern Proof — initial schema
-- Relational core (audits / pages / findings / reports) + JSONB document
-- store (agent_memory). Taxonomy values are stored as TEXT and validated in
-- the application layer (see app/models/taxonomy.py) so the taxonomy can grow
-- without enum migrations.

-- ── audits ────────────────────────────────────────────────────────────────
create table if not exists public.audits (
    id                bigint generated always as identity primary key,
    url               text        not null,
    status            text        not null default 'queued',
    progress_message  text,
    error_message     text,
    created_at        timestamptz not null default now(),
    completed_at      timestamptz
);
create index if not exists audits_created_at_idx on public.audits (created_at desc);

-- ── audit_pages ─────────────────────────────────────────────────────────────
create table if not exists public.audit_pages (
    id                  bigint generated always as identity primary key,
    audit_id            bigint not null references public.audits (id) on delete cascade,
    page_url            text   not null,
    page_title          text,
    screenshot_path     text,
    html_snapshot_path  text,
    crawl_depth         int    not null default 0,
    created_at          timestamptz not null default now()
);
create index if not exists audit_pages_audit_id_idx on public.audit_pages (audit_id);

-- ── findings ─────────────────────────────────────────────────────────────────
create table if not exists public.findings (
    id                        bigint generated always as identity primary key,
    audit_id                  bigint not null references public.audits (id) on delete cascade,
    page_id                   bigint references public.audit_pages (id) on delete set null,
    category                  text   not null,
    dp_type                   text   not null,
    ccpa_pattern              text,
    severity                  text   not null,
    title                     text   not null,
    description               text   not null,
    explanation               text,
    evidence_screenshot_path  text,
    page_url                  text,
    bounding_box              jsonb,
    confidence_score          double precision,
    is_dynamic                boolean not null default false,
    created_at                timestamptz not null default now()
);
create index if not exists findings_audit_id_idx on public.findings (audit_id);

-- ── reports ──────────────────────────────────────────────────────────────────
create table if not exists public.reports (
    id            bigint generated always as identity primary key,
    audit_id      bigint not null unique references public.audits (id) on delete cascade,
    summary       text   not null,
    score         int    not null,           -- 0-100, 100 = clean
    pdf_path      text,
    "references"  jsonb  not null default '[]'::jsonb,
    generated_at  timestamptz not null default now()
);

-- ── agent_memory (the "NoSQL"/document layer) ─────────────────────────────────
-- Free-form JSONB scratchpad: planner tickets, agent notes, raw crawl payloads,
-- per-page LLM outputs, etc. One row per memory item.
create table if not exists public.agent_memory (
    id          bigint generated always as identity primary key,
    audit_id    bigint not null references public.audits (id) on delete cascade,
    agent       text   not null,             -- manager | planner | crawler | static_detector | report
    kind        text   not null,             -- ticket | note | raw | page_output
    payload     jsonb  not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);
create index if not exists agent_memory_audit_id_idx on public.agent_memory (audit_id);
create index if not exists agent_memory_lookup_idx   on public.agent_memory (audit_id, agent, kind);
create index if not exists agent_memory_payload_gin  on public.agent_memory using gin (payload);

-- Note: the backend connects with the service-role key (bypasses RLS). RLS
-- policies for end-user/multi-tenant access are deferred (out of MVP scope).
