-- Slice 36: Remove Step-Up Authentication (Management Cookie Only)

-- Step-up is removed from the product contract. Management session cookie + CSRF is sufficient.

alter table if exists approvals
  drop column if exists requires_stepup;

drop table if exists stepup_sessions;
drop table if exists stepup_challenges;

drop type if exists stepup_issued_for;

