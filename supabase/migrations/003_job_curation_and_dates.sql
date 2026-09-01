alter table public.jobs
  add column if not exists published_at timestamptz,
  add column if not exists favorite boolean not null default false,
  add column if not exists hidden boolean not null default false,
  add column if not exists hidden_at timestamptz;

create index if not exists jobs_user_hidden_score_idx on public.jobs(user_id, hidden, puntaje desc);
create index if not exists jobs_user_favorite_idx on public.jobs(user_id, favorite) where favorite = true;
create index if not exists jobs_user_published_idx on public.jobs(user_id, published_at desc);
