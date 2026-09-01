alter table public.jobs
  add column if not exists match_breakdown jsonb not null default '{}'::jsonb;

comment on column public.jobs.match_breakdown is
  'Desglose explicable del puntaje de compatibilidad calculado por el motor de matching.';
