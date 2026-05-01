"use strict";(()=>{var e={};e.id=744,e.ids=[744],e.modules={399:e=>{e.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},3487:(e,t,r)=>{r.r(t),r.d(t,{originalPathname:()=>h,patchFetch:()=>g,requestAsyncStorage:()=>d,routeModule:()=>p,serverHooks:()=>m,staticGenerationAsyncStorage:()=>_});var n={};r.r(n),r.d(n,{POST:()=>l,dynamic:()=>u});var a=r(9303),s=r(8716),o=r(670),i=r(9567);let u="force-dynamic";async function c({message:e,intent:t,response:r,tools:n,rowCount:a}){await (0,i.R0)(`
    WITH inserted AS (
      INSERT INTO chat.query_logs (
        user_question,
        parsed_intent,
        response_summary,
        tools_used,
        result_row_count,
        metadata
      )
      VALUES (
        ${(0,i.cG)(e)},
        ${(0,i.r)(t)},
        ${(0,i.cG)(r)},
        ${(0,i.r)(n)},
        ${a},
        ${(0,i.r)({source:"web_command_center"})}
      )
      RETURNING query_log_id
    )
    SELECT COALESCE(jsonb_agg(row_to_json(inserted)), '[]'::jsonb)::text
    FROM inserted
  `)}async function l(e){try{let{message:t=""}=await e.json(),r=t.toLowerCase();if(r.includes("model")||r.includes("auc")||r.includes("performance")){let e=await (0,i.Cv)(`
        SELECT
          target_id,
          model_name,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 3) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 3) AS log_loss
        FROM models.model_registry
        WHERE is_active
        ORDER BY roc_auc DESC
        LIMIT 8
      `),r="Here are the strongest active model registrations by validation ROC AUC.",n=["models.model_registry"];return await c({message:t,intent:{name:"active_models"},response:r,tools:n,rowCount:e.length}),Response.json({response:r,tools_used:n,table:e})}if(r.includes("left")||r.includes("inning")||r.includes("simulate")){let e=await (0,i.pP)(`
        SELECT
          count(*) AS historical_half_innings,
          round(avg(runs_scored)::numeric, 3) AS expected_runs,
          round(avg((runs_scored > 0)::integer)::numeric, 3) AS run_probability,
          round(avg(all_left_handed_batters_hit::integer)::numeric, 3) AS all_left_handed_batters_hit_probability
        FROM features.half_inning_outcome_summary
        WHERE season BETWEEN 2021 AND 2025
          AND left_handed_pa > 0
      `),r="Using historical half-innings from 2021-2025 where at least one left-handed batter appeared, here is the scenario baseline.",n=["features.half_inning_outcome_summary"];return await c({message:t,intent:{name:"left_handed_half_inning"},response:r,tools:n,rowCount:e?1:0}),Response.json({response:r,tools_used:n,table:e?[e]:[]})}if(r.includes("batter")||r.includes("hitter")||r.includes("player")){let e=await (0,i.Cv)(`
        SELECT
          player_id,
          player_name,
          plate_appearances,
          hits,
          home_runs,
          batting_average,
          on_base_percentage_proxy,
          slugging_percentage,
          round((COALESCE(on_base_percentage_proxy, 0) + COALESCE(slugging_percentage, 0))::numeric, 3) AS ops_proxy
        FROM features.player_production_season
        WHERE season = 2025
          AND plate_appearances >= 400
        ORDER BY ops_proxy DESC
        LIMIT 10
      `),r="Top 2025 hitters by our current OPS proxy.",n=["features.player_production_season"];return await c({message:t,intent:{name:"top_hitters"},response:r,tools:n,rowCount:e.length}),Response.json({response:r,tools_used:n,table:e})}let n=await (0,i.pP)(`
      SELECT
        (SELECT count(*) FROM core.games) AS games,
        (SELECT count(*) FROM core.plate_appearances) AS plate_appearances,
        (SELECT count(*) FROM features.player_production_season) AS player_seasons,
        (SELECT count(*) FROM models.model_registry WHERE is_active) AS active_models
    `),a="I can inspect model performance, hitter/pitcher production, half-inning scenarios, and warehouse status. Try: “show active models”, “simulate left-handed batters this inning”, or “top hitters”.",s=["warehouse_status"];return await c({message:t,intent:{name:"warehouse_status"},response:a,tools:s,rowCount:n?1:0}),Response.json({response:a,tools_used:s,table:n?[n]:[]})}catch(e){return(0,i.qF)(e)}}let p=new a.AppRouteRouteModule({definition:{kind:s.x.APP_ROUTE,page:"/api/chat/route",pathname:"/api/chat",filename:"route",bundlePath:"app/api/chat/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/chat/route.ts",nextConfigOutput:"",userland:n}),{requestAsyncStorage:d,staticGenerationAsyncStorage:_,serverHooks:m}=p,h="/api/chat/route";function g(){return(0,o.patchFetch)({serverHooks:m,staticGenerationAsyncStorage:_})}},9567:(e,t,r)=>{r.d(t,{qF:()=>h,R0:()=>l,r:()=>_,Cv:()=>u,pP:()=>p,XB:()=>m,cG:()=>d});let n=require("node:child_process"),a=require("node:path");var s=r.n(a);let o=(0,require("node:util").promisify)(n.execFile),i=s().resolve(process.cwd(),"..");async function u(e){return c(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function c(e,t="[]"){let{stdout:r}=await o("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(r.trim()||t)}async function l(e){return(await c(e))[0]??null}async function p(e){return(await u(e))[0]??null}function d(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function _(e){return`${d(JSON.stringify(e??null))}::jsonb`}async function m(e,t){let r=s().join(i,"scripts",e),{stdout:n,stderr:a}=await o("python3",[r,...t],{cwd:i,maxBuffer:20971520});return[n.trim(),a.trim()].filter(Boolean).join("\n")}function h(e){let t=e instanceof Error?e.message:"Unknown API error";return Response.json({error:t},{status:500})}},9303:(e,t,r)=>{e.exports=r(517)}};var t=require("../../../webpack-runtime.js");t.C(e);var r=e=>t(t.s=e),n=t.X(0,[948],()=>r(3487));module.exports=n})();