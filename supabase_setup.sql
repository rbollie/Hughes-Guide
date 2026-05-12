-- Hughes Guide — Supabase setup
-- Run this once in your Supabase project's SQL Editor.

-- Single key-value table. All app state lives in JSONB blobs keyed by name.
create table if not exists public.hughes_guide_kv (
    key         text primary key,
    value       jsonb,
    updated_at  timestamptz not null default now()
);

-- Auto-update updated_at on every row change
create or replace function public.touch_hughes_guide_kv()
returns trigger language plpgsql as $$
begin
    new.updated_at = now();
    return new;
end $$;

drop trigger if exists trg_touch_hughes_guide_kv on public.hughes_guide_kv;
create trigger trg_touch_hughes_guide_kv
    before update on public.hughes_guide_kv
    for each row execute function public.touch_hughes_guide_kv();

-- Row Level Security
-- The app uses the SERVICE ROLE key, which bypasses RLS entirely — so policies
-- below are optional. If you ever switch the app to use the ANON key (e.g. for
-- public read access), enable RLS and adjust policies to suit your security needs.
--
-- alter table public.hughes_guide_kv enable row level security;
-- create policy "service_role full access" on public.hughes_guide_kv
--     for all using (auth.role() = 'service_role') with check (auth.role() = 'service_role');
