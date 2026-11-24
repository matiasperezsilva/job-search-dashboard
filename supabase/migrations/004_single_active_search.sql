-- Preserve historical search rows while consolidating duplicate active runs.
begin;

lock table public.search_runs in share row exclusive mode;

with active as (
  select id, row_number() over (partition by user_id order by updated_at desc, id desc) as position
  from public.search_runs
  where status in ('queued', 'running')
)
update public.search_runs as runs
set status = 'failed', error = 'La búsqueda se cerró porque ya había otra activa.', updated_at = now()
from active
where runs.id = active.id and active.position > 1;

create unique index if not exists search_runs_one_active_per_user_idx
  on public.search_runs (user_id)
  where status in ('queued', 'running');

commit;
