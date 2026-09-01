create extension if not exists pgcrypto;

create table if not exists public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  cv_name text,
  cv_text text,
  profile_data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.jobs (
  id text not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  titulo text not null,
  empresa text,
  descripcion text,
  modalidad text,
  link text,
  fuente text,
  puntaje integer not null default 0 check (puntaje between 0 and 100),
  area text,
  razon text,
  match_breakdown jsonb not null default '{}'::jsonb,
  published_at timestamptz,
  favorite boolean not null default false,
  hidden boolean not null default false,
  hidden_at timestamptz,
  first_seen timestamptz not null default now(),
  last_seen timestamptz not null default now(),
  primary key (user_id, id)
);

create table if not exists public.applications (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  estado text not null default 'Guardada',
  notas text not null default '',
  updated_at timestamptz not null default now(),
  primary key (user_id, job_id),
  foreign key (user_id, job_id) references public.jobs(user_id, id) on delete cascade
);

create table if not exists public.letters (
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id text not null,
  modo text not null default 'local',
  contenido text not null,
  updated_at timestamptz not null default now(),
  primary key (user_id, job_id),
  foreign key (user_id, job_id) references public.jobs(user_id, id) on delete cascade
);

create table if not exists public.search_runs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued','running','completed','failed')),
  mode text not null default 'rapida',
  sources jsonb not null default '[]'::jsonb,
  terms jsonb not null default '[]'::jsonb,
  progress jsonb not null default '{}'::jsonb,
  result jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.jobs enable row level security;
alter table public.applications enable row level security;
alter table public.letters enable row level security;
alter table public.search_runs enable row level security;

-- Re-running this migration in a fresh project is supported. Policies are created only when absent.
do $$
declare
  t text;
  op text;
  pname text;
begin
  foreach t in array array['profiles','jobs','applications','letters','search_runs'] loop
    foreach op in array array['select','insert','update','delete'] loop
      pname := t || '_' || op || '_own';
      if not exists (
        select 1 from pg_policies where schemaname='public' and tablename=t and policyname=pname
      ) then
        if op = 'select' then
          execute format('create policy %I on public.%I for select to authenticated using ((select auth.uid()) = user_id)', pname, t);
        elsif op = 'insert' then
          execute format('create policy %I on public.%I for insert to authenticated with check ((select auth.uid()) = user_id)', pname, t);
        elsif op = 'update' then
          execute format('create policy %I on public.%I for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id)', pname, t);
        else
          execute format('create policy %I on public.%I for delete to authenticated using ((select auth.uid()) = user_id)', pname, t);
        end if;
      end if;
    end loop;
  end loop;
end $$;

grant usage on schema public to authenticated;
grant select, insert, update, delete on public.profiles, public.jobs, public.applications, public.letters, public.search_runs to authenticated;

create index if not exists jobs_user_score_idx on public.jobs(user_id, puntaje desc);
create index if not exists jobs_user_last_seen_idx on public.jobs(user_id, last_seen desc);
create index if not exists applications_user_estado_idx on public.applications(user_id, estado);
create index if not exists search_runs_user_created_idx on public.search_runs(user_id, created_at desc);
