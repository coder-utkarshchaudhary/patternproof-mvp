-- Dev-only helper: wipe all audit data and restart identity sequences.
-- Called via Supabase RPC from the POST /api/dev/reset endpoint (debug mode only).
create or replace function public.reset_dev_data()
returns void
language plpgsql
security definer
as $$
begin
    truncate table
        public.ticket_archive,
        public.agent_memory,
        public.tickets,
        public.findings,
        public.reports,
        public.audit_pages,
        public.audits
    restart identity cascade;
end;
$$;
