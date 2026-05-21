alter table public.users enable row level security;
create policy users_self_read on public.users for select using (auth.uid() = id);
create policy users_self_update on public.users for update using (auth.uid() = id);

alter table public.user_settings enable row level security;
create policy user_settings_self_all on public.user_settings for all using (auth.uid() = user_id);

alter table public.jobs enable row level security;
create policy jobs_self_all on public.jobs for all using (auth.uid() = user_id);

alter table public.job_items enable row level security;
create policy job_items_self_read on public.job_items
  for select using (
    exists (select 1 from public.jobs where jobs.id = job_items.job_id and jobs.user_id = auth.uid())
  );

alter table public.usage_daily enable row level security;
create policy usage_daily_self_read on public.usage_daily for select using (auth.uid() = user_id);
