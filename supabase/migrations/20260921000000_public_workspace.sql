create table if not exists public.floorplan_projects (
  project_id text primary key check (project_id = 'shared'),
  payload_base64 text not null check (octet_length(payload_base64) <= 34952536),
  revision bigint not null check (revision >= 1),
  updated_at timestamptz not null default now()
);

alter table public.floorplan_projects enable row level security;

revoke all on table public.floorplan_projects from anon, authenticated;
grant select, insert, update on table public.floorplan_projects to anon;

create policy "public workspace read"
on public.floorplan_projects for select
to anon
using (project_id = 'shared');

create policy "public workspace first save"
on public.floorplan_projects for insert
to anon
with check (project_id = 'shared' and revision = 1);

create policy "public workspace update"
on public.floorplan_projects for update
to anon
using (project_id = 'shared')
with check (project_id = 'shared');

create or replace function public.touch_floorplan_project_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

revoke all on function public.touch_floorplan_project_updated_at() from public;

drop trigger if exists touch_floorplan_project_updated_at on public.floorplan_projects;
create trigger touch_floorplan_project_updated_at
before update on public.floorplan_projects
for each row execute function public.touch_floorplan_project_updated_at();
