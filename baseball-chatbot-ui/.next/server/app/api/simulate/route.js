"use strict";(()=>{var e={};e.id=284,e.ids=[284],e.modules={517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},4255:(e,n,t)=>{t.r(n),t.d(n,{headerHooks:()=>p,originalPathname:()=>h,patchFetch:()=>f,requestAsyncStorage:()=>c,routeModule:()=>l,serverHooks:()=>m,staticGenerationAsyncStorage:()=>d,staticGenerationBailout:()=>g});var i={};t.r(i),t.d(i,{POST:()=>_,dynamic:()=>u});var r=t(5419),a=t(9108),s=t(9678),o=t(3023);let u="force-dynamic";async function _(e){try{let n=await e.json(),t=[`season BETWEEN ${Number(n.season||2021)-4} AND ${Number(n.season||2025)}`];n.inning&&t.push(`inning = ${Number(n.inning)}`),"boolean"==typeof n.is_bottom_inning&&t.push(`is_bottom_inning = ${n.is_bottom_inning?"true":"false"}`),n.batting_team_id&&t.push(`batting_team_id = ${(0,o.cG)(n.batting_team_id.toUpperCase())}`),n.fielding_team_id&&t.push(`fielding_team_id = ${(0,o.cG)(n.fielding_team_id.toUpperCase())}`),n.left_handed_only&&t.push("left_handed_pa > 0");let i=t.join(" AND "),[r,a,s]=await Promise.all([(0,o.pP)(`
        SELECT
          count(*) AS historical_half_innings,
          round(avg(runs_scored)::numeric, 4) AS expected_runs,
          round(avg((runs_scored > 0)::integer)::numeric, 4) AS run_probability,
          round(avg(all_left_handed_batters_hit::integer)::numeric, 4) AS all_left_handed_batters_hit_probability,
          round(avg((home_runs > 0)::integer)::numeric, 4) AS home_run_in_half_inning_probability,
          round(avg(hits)::numeric, 4) AS expected_hits,
          round(avg(walks)::numeric, 4) AS expected_walks,
          round(avg(strikeouts)::numeric, 4) AS expected_strikeouts
        FROM features.half_inning_outcome_summary
        WHERE ${i}
      `),(0,o.Cv)(`
        SELECT
          runs_scored,
          count(*) AS half_innings,
          round(count(*)::numeric / sum(count(*)) OVER (), 4) AS probability
        FROM features.half_inning_outcome_summary
        WHERE ${i}
        GROUP BY runs_scored
        ORDER BY runs_scored
      `),(0,o.Cv)(`
        SELECT
          game_id,
          season,
          game_date,
          inning,
          is_bottom_inning,
          batting_team_id,
          fielding_team_id,
          plate_appearances,
          hits,
          walks,
          strikeouts,
          home_runs,
          runs_scored,
          all_left_handed_batters_hit
        FROM features.half_inning_outcome_summary
        WHERE ${i}
        ORDER BY game_date DESC, game_id DESC
        LIMIT 25
      `)]),u=await (0,o.R0)(`
      WITH inserted AS (
        INSERT INTO predictions.simulation_runs (
          run_name,
          run_mode,
          filters,
          summary,
          run_distribution,
          sample_size,
          notes
        )
        VALUES (
          ${(0,o.cG)(`Historical ${n.season||2025} inning ${n.inning||"all"} scenario`)},
          'historical_backtest_distribution',
          ${(0,o.r)(n)},
          ${(0,o.r)(r)},
          ${(0,o.r)(a)},
          ${r?.historical_half_innings??"NULL"},
          'Saved from the Next.js Sim Lab.'
        )
        RETURNING simulation_run_id, requested_at, run_name
      )
      SELECT COALESCE(jsonb_agg(row_to_json(inserted)), '[]'::jsonb)::text
      FROM inserted
    `);return Response.json({filters:n,mode:"historical_backtest_distribution",simulation_run:u,summary:r,run_distribution:a,recent_examples:s})}catch(e){return(0,o.qF)(e)}}let l=new r.AppRouteRouteModule({definition:{kind:a.x.APP_ROUTE,page:"/api/simulate/route",pathname:"/api/simulate",filename:"route",bundlePath:"app/api/simulate/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/simulate/route.ts",nextConfigOutput:"",userland:i}),{requestAsyncStorage:c,staticGenerationAsyncStorage:d,serverHooks:m,headerHooks:p,staticGenerationBailout:g}=l,h="/api/simulate/route";function f(){return(0,s.patchFetch)({serverHooks:m,staticGenerationAsyncStorage:d})}},3023:(e,n,t)=>{t.d(n,{qF:()=>g,R0:()=>l,r:()=>m,Cv:()=>u,pP:()=>c,XB:()=>p,cG:()=>d});let i=require("node:child_process"),r=require("node:path");var a=t.n(r);let s=(0,require("node:util").promisify)(i.execFile),o=a().resolve(process.cwd(),"..");async function u(e){return _(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function _(e,n="[]"){let{stdout:t}=await s("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:o,maxBuffer:20971520});return JSON.parse(t.trim()||n)}async function l(e){return(await _(e))[0]??null}async function c(e){return(await u(e))[0]??null}function d(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function m(e){return`${d(JSON.stringify(e??null))}::jsonb`}async function p(e,n){let t=a().join(o,"scripts",e),{stdout:i,stderr:r}=await s("python3",[t,...n],{cwd:o,maxBuffer:20971520});return[i.trim(),r.trim()].filter(Boolean).join("\n")}function g(e){let n=e instanceof Error?e.message:"Unknown API error";return Response.json({error:n},{status:500})}},5419:(e,n,t)=>{e.exports=t(517)}};var n=require("../../../webpack-runtime.js");n.C(e);var t=e=>n(n.s=e),i=n.X(0,[638],()=>t(4255));module.exports=i})();