"use strict";(()=>{var e={};e.id=744,e.ids=[744],e.modules={517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},8940:(e,t,n)=>{n.r(t),n.d(t,{headerHooks:()=>h,originalPathname:()=>f,patchFetch:()=>E,requestAsyncStorage:()=>_,routeModule:()=>p,serverHooks:()=>m,staticGenerationAsyncStorage:()=>d,staticGenerationBailout:()=>g});var r={};n.r(r),n.d(r,{POST:()=>l,dynamic:()=>u});var a=n(5419),s=n(9108),o=n(9678),i=n(3023);let u="force-dynamic";async function c({message:e,intent:t,response:n,tools:r,rowCount:a}){await (0,i.R0)(`
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
        ${(0,i.cG)(n)},
        ${(0,i.r)(r)},
        ${a},
        ${(0,i.r)({source:"web_command_center"})}
      )
      RETURNING query_log_id
    )
    SELECT COALESCE(jsonb_agg(row_to_json(inserted)), '[]'::jsonb)::text
    FROM inserted
  `)}async function l(e){try{let{message:t=""}=await e.json(),n=t.toLowerCase();if(n.includes("model")||n.includes("auc")||n.includes("performance")){let e=await (0,i.Cv)(`
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
      `),n="Here are the strongest active model registrations by validation ROC AUC.",r=["models.model_registry"];return await c({message:t,intent:{name:"active_models"},response:n,tools:r,rowCount:e.length}),Response.json({response:n,tools_used:r,table:e})}if(n.includes("left")||n.includes("inning")||n.includes("simulate")){let e=await (0,i.pP)(`
        SELECT
          count(*) AS historical_half_innings,
          round(avg(runs_scored)::numeric, 3) AS expected_runs,
          round(avg((runs_scored > 0)::integer)::numeric, 3) AS run_probability,
          round(avg(all_left_handed_batters_hit::integer)::numeric, 3) AS all_left_handed_batters_hit_probability
        FROM features.half_inning_outcome_summary
        WHERE season BETWEEN 2021 AND 2025
          AND left_handed_pa > 0
      `),n="Using historical half-innings from 2021-2025 where at least one left-handed batter appeared, here is the scenario baseline.",r=["features.half_inning_outcome_summary"];return await c({message:t,intent:{name:"left_handed_half_inning"},response:n,tools:r,rowCount:e?1:0}),Response.json({response:n,tools_used:r,table:e?[e]:[]})}if(n.includes("batter")||n.includes("hitter")||n.includes("player")){let e=await (0,i.Cv)(`
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
      `),n="Top 2025 hitters by our current OPS proxy.",r=["features.player_production_season"];return await c({message:t,intent:{name:"top_hitters"},response:n,tools:r,rowCount:e.length}),Response.json({response:n,tools_used:r,table:e})}let r=await (0,i.pP)(`
      SELECT
        (SELECT count(*) FROM core.games) AS games,
        (SELECT count(*) FROM core.plate_appearances) AS plate_appearances,
        (SELECT count(*) FROM features.player_production_season) AS player_seasons,
        (SELECT count(*) FROM models.model_registry WHERE is_active) AS active_models
    `),a="I can inspect model performance, hitter/pitcher production, half-inning scenarios, and warehouse status. Try: “show active models”, “simulate left-handed batters this inning”, or “top hitters”.",s=["warehouse_status"];return await c({message:t,intent:{name:"warehouse_status"},response:a,tools:s,rowCount:r?1:0}),Response.json({response:a,tools_used:s,table:r?[r]:[]})}catch(e){return(0,i.qF)(e)}}let p=new a.AppRouteRouteModule({definition:{kind:s.x.APP_ROUTE,page:"/api/chat/route",pathname:"/api/chat",filename:"route",bundlePath:"app/api/chat/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/chat/route.ts",nextConfigOutput:"",userland:r}),{requestAsyncStorage:_,staticGenerationAsyncStorage:d,serverHooks:m,headerHooks:h,staticGenerationBailout:g}=p,f="/api/chat/route";function E(){return(0,o.patchFetch)({serverHooks:m,staticGenerationAsyncStorage:d})}},3023:(e,t,n)=>{n.d(t,{qF:()=>h,R0:()=>l,r:()=>d,Cv:()=>u,pP:()=>p,XB:()=>m,cG:()=>_});let r=require("node:child_process"),a=require("node:path");var s=n.n(a);let o=(0,require("node:util").promisify)(r.execFile),i=s().resolve(process.cwd(),"..");async function u(e){return c(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function c(e,t="[]"){let{stdout:n}=await o("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(n.trim()||t)}async function l(e){return(await c(e))[0]??null}async function p(e){return(await u(e))[0]??null}function _(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function d(e){return`${_(JSON.stringify(e??null))}::jsonb`}async function m(e,t){let n=s().join(i,"scripts",e),{stdout:r,stderr:a}=await o("python3",[n,...t],{cwd:i,maxBuffer:20971520});return[r.trim(),a.trim()].filter(Boolean).join("\n")}function h(e){let t=e instanceof Error?e.message:"Unknown API error";return Response.json({error:t},{status:500})}},5419:(e,t,n)=>{e.exports=n(517)}};var t=require("../../../webpack-runtime.js");t.C(e);var n=e=>t(t.s=e),r=t.X(0,[638],()=>n(8940));module.exports=r})();