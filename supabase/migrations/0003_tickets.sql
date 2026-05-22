-- Pattern Proof — tickets + ticket_archive
-- Planner-generated task tickets (and pipeline-stage tickets) are written here
-- while an audit is in flight. On completion/failure they are moved to
-- ticket_archive so the tickets table only ever contains live work.

-- ── tickets ──────────────────────────────────────────────────────────────────
create table if not exists public.tickets (
    id           bigint generated always as identity primary key,
    audit_id     bigint not null references public.audits (id) on delete cascade,
    title        text   not null,
    detail       text,
    priority     text   not null default 'normal',  -- low | normal | high
    ticket_type  text   not null default 'planner', -- planner | stage
    assigned_to  text,                               -- agent name
    status       text   not null default 'pending', -- pending | in_progress | completed | failed
    created_at   timestamptz not null default now(),
    started_at   timestamptz,
    completed_at timestamptz
);

create index if not exists tickets_audit_id_idx on public.tickets (audit_id);
create index if not exists tickets_status_idx   on public.tickets (status);

-- ── ticket_archive ────────────────────────────────────────────────────────────
-- Immutable log of every finished ticket. original_id is stored for reference
-- but NOT a FK (the source row is deleted before archiving completes).
create table if not exists public.ticket_archive (
    id           bigint generated always as identity primary key,
    original_id  bigint not null,
    audit_id     bigint not null,
    title        text   not null,
    detail       text,
    priority     text   not null default 'normal',
    ticket_type  text   not null default 'planner',
    assigned_to  text,
    final_status text   not null,                   -- completed | failed | cancelled
    result       jsonb  not null default '{}'::jsonb,
    created_at   timestamptz not null,
    completed_at timestamptz,
    archived_at  timestamptz not null default now()
);

create index if not exists ticket_archive_audit_id_idx on public.ticket_archive (audit_id);
