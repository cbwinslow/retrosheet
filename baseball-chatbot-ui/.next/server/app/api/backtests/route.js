"use strict";(()=>{var e={};e.id=67,e.ids=[67],e.modules={517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},8171:(e,t,r)=>{r.r(t),r.d(t,{headerHooks:()=>p,originalPathname:()=>S,patchFetch:()=>f,requestAsyncStorage:()=>d,routeModule:()=>l,serverHooks:()=>m,staticGenerationAsyncStorage:()=>_,staticGenerationBailout:()=>E});var a={};r.r(a),r.d(a,{GET:()=>u,dynamic:()=>c});var o=r(5419),s=r(9108),n=r(9678),i=r(3023);let c="force-dynamic";async function u(){try{let[e,t,r]=await Promise.all([(0,i.pP)(`
        SELECT
          count(*) AS registered_models,
          count(*) FILTER (WHERE is_active) AS active_models,
          count(*) FILTER (WHERE feature_spec->>'sweep' = 'true') AS sweep_candidates,
          round(max((metrics->'validation'->>'roc_auc')::numeric), 4) AS best_validation_roc_auc,
          max(created_at) AS latest_registered_at
        FROM models.model_registry
        WHERE target_id = 'game_home_win' OR target_id LIKE 'pa_%'
      `),(0,i.Cv)(`
        WITH ranked AS (
          SELECT
            target_id,
            model_name,
            model_family,
            model_version,
            is_active,
            feature_spec->>'feature_set' AS feature_set,
            COALESCE(feature_spec->>'sweep', 'false') AS is_sweep,
            round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
            round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
            (metrics->'validation'->>'rows')::integer AS validation_rows,
            row_number() OVER (
              PARTITION BY target_id
              ORDER BY (metrics->'validation'->>'roc_auc')::numeric DESC NULLS LAST
            ) AS rank
          FROM models.model_registry
          WHERE target_id = 'game_home_win' OR target_id LIKE 'pa_%'
            AND metrics->'validation' ? 'roc_auc'
        )
        SELECT *
        FROM ranked
        WHERE rank <= 5
        ORDER BY target_id, rank
      `),(0,i.Cv)(`
        SELECT
          target_id,
          model_name,
          model_version,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
          created_at
        FROM models.model_registry
        WHERE feature_spec->>'sweep' = 'true'
        ORDER BY created_at DESC
        LIMIT 20
      `)]);return Response.json({overview:e,leaderboard:t,sweep_candidates:r})}catch(e){return(0,i.qF)(e)}}let l=new o.AppRouteRouteModule({definition:{kind:s.x.APP_ROUTE,page:"/api/backtests/route",pathname:"/api/backtests",filename:"route",bundlePath:"app/api/backtests/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/backtests/route.ts",nextConfigOutput:"",userland:a}),{requestAsyncStorage:d,staticGenerationAsyncStorage:_,serverHooks:m,headerHooks:p,staticGenerationBailout:E}=l,S="/api/backtests/route";function f(){return(0,n.patchFetch)({serverHooks:m,staticGenerationAsyncStorage:_})}},3023:(e,t,r)=>{r.d(t,{qF:()=>E,R0:()=>l,r:()=>m,Cv:()=>c,pP:()=>d,XB:()=>p,cG:()=>_});let a=require("node:child_process"),o=require("node:path");var s=r.n(o);let n=(0,require("node:util").promisify)(a.execFile),i=s().resolve(process.cwd(),"..");async function c(e){return u(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function u(e,t="[]"){let{stdout:r}=await n("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(r.trim()||t)}async function l(e){return(await u(e))[0]??null}async function d(e){return(await c(e))[0]??null}function _(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function m(e){return`${_(JSON.stringify(e??null))}::jsonb`}async function p(e,t){let r=s().join(i,"scripts",e),{stdout:a,stderr:o}=await n("python3",[r,...t],{cwd:i,maxBuffer:20971520});return[a.trim(),o.trim()].filter(Boolean).join("\n")}function E(e){let t=e instanceof Error?e.message:"Unknown API error";return Response.json({error:t},{status:500})}},5419:(e,t,r)=>{e.exports=r(517)}};var t=require("../../../webpack-runtime.js");t.C(e);var r=e=>t(t.s=e),a=t.X(0,[638],()=>r(8171));module.exports=a})();