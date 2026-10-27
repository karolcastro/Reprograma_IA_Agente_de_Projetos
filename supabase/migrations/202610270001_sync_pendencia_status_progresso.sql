-- ProjectFlow AI: sincronizar status e progresso de pendências.
-- Regra: aberta + progresso > 0 => em_andamento.
-- Concluída => progresso 100; progresso 100 exige status concluida.
-- Esta migração é idempotente para a função e normaliza os dados legados.
create or replace function app_private.validar_progresso_pendencia()
returns trigger
language plpgsql
set search_path to ''
as $function$
begin
  if new.status = 'concluida' then
    new.progresso := 100;
  elsif new.progresso = 100 then
    raise exception 'Progresso 100 exige status concluida';
  elsif new.status = 'aberta' and new.progresso > 0 then
    new.status := 'em_andamento';
  end if;
  return new;
end;
$function$;

-- Corrigir somente os registros contraditórios existentes.
update public.pendencias
set status = 'em_andamento'
where status = 'aberta'
  and progresso > 0;
