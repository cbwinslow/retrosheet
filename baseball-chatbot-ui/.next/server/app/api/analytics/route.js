"use strict";(()=>{var e={};e.id=567,e.ids=[567],e.modules={399:e=>{e.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},3353:(e,r,t)=>{t.r(r),t.d(r,{originalPathname:()=>m,patchFetch:()=>g,requestAsyncStorage:()=>l,routeModule:()=>_,serverHooks:()=>p,staticGenerationAsyncStorage:()=>d});var a={};t.r(a),t.d(a,{GET:()=>u,dynamic:()=>c});var o=t(9303),n=t(8716),s=t(670),i=t(9567);let c="force-dynamic";async function u(){try{let[e,r,t,a,o]=await Promise.all([(0,i.pP)(`
          SELECT
            count(*) AS total_active_models,
            round(avg((metrics->'validation'->>'roc_auc')::numeric), 4) AS avg_roc_auc,
            max((metrics->'validation'->>'roc_auc')::numeric) AS best_roc_auc,
            max(created_at) AS latest_model_created_at
          FROM models.model_registry
          WHERE is_active
        `),(0,i.Cv)(`
          SELECT
            target_id,
            model_name,
            model_family,
            feature_spec->>'feature_set' AS feature_set,
            (metrics->'validation'->>'rows')::integer AS validation_rows,
            round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
            round(((metrics->'validation'->>'accuracy')::numeric), 4) AS accuracy,
            round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
            round(((metrics->'validation'->>'brier_score')::numeric), 4) AS brier_score,
            jsonb_array_length(feature_spec->'numeric_features') + jsonb_array_length(feature_spec->'categorical_features') AS feature_count,
            created_at
          FROM models.model_registry
          WHERE is_active
          ORDER BY target_id, roc_auc DESC
        `),(0,i.Cv)(`
          SELECT
            season,
            player_id,
            player_name,
            plate_appearances,
            hits,
            home_runs,
            batting_average,
            on_base_percentage_proxy,
            slugging_percentage,
            round((COALESCE(on_base_percentage_proxy, 0) + COALESCE(slugging_percentage, 0))::numeric, 4) AS ops_proxy
          FROM features.player_production_season
          WHERE season = 2025
            AND plate_appearances >= 400
          ORDER BY ops_proxy DESC
          LIMIT 15
        `),(0,i.Cv)(`
          SELECT
            season,
            player_id,
            player_name,
            batters_faced,
            strikeouts,
            walks_allowed,
            home_runs_allowed,
            strikeout_rate,
            walk_allowed_rate,
            command_power_score_proxy
          FROM features.pitcher_production_season
          WHERE season = 2025
            AND batters_faced >= 400
          ORDER BY command_power_score_proxy DESC
          LIMIT 15
        `),(0,i.Cv)(`
          SELECT
            target_id,
            count(*) AS active_models,
            round(avg((metrics->'validation'->>'roc_auc')::numeric), 4) AS avg_roc_auc,
            round(max((metrics->'validation'->>'roc_auc')::numeric), 4) AS best_roc_auc
          FROM models.model_registry
          WHERE is_active
          GROUP BY target_id
          ORDER BY target_id
        `)]);return Response.json({generated_at:new Date().toISOString(),overall:e,model_metrics:r,target_summary:o,batter_leaders:t,pitcher_leaders:a})}catch(e){return(0,i.qF)(e)}}let _=new o.AppRouteRouteModule({definition:{kind:n.x.APP_ROUTE,page:"/api/analytics/route",pathname:"/api/analytics",filename:"route",bundlePath:"app/api/analytics/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/analytics/route.ts",nextConfigOutput:"",userland:a}),{requestAsyncStorage:l,staticGenerationAsyncStorage:d,serverHooks:p}=_,m="/api/analytics/route";function g(){return(0,s.patchFetch)({serverHooks:p,staticGenerationAsyncStorage:d})}},9567:(e,r,t)=>{t.d(r,{qF:()=>g,R0:()=>_,r:()=>p,Cv:()=>c,pP:()=>l,XB:()=>m,cG:()=>d});let a=require("node:child_process"),o=require("node:path");var n=t.n(o);let s=(0,require("node:util").promisify)(a.execFile),i=n().resolve(process.cwd(),"..");async function c(e){return u(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function u(e,r="[]"){let{stdout:t}=await s("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(t.trim()||r)}async function _(e){return(await u(e))[0]??null}async function l(e){return(await c(e))[0]??null}function d(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function p(e){return`${d(JSON.stringify(e??null))}::jsonb`}async function m(e,r){let t=n().join(i,"scripts",e),{stdout:a,stderr:o}=await s("python3",[t,...r],{cwd:i,maxBuffer:20971520});return[a.trim(),o.trim()].filter(Boolean).join("\n")}function g(e){let r=e instanceof Error?e.message:"Unknown API error";return Response.json({error:r},{status:500})}},9303:(e,r,t)=>{e.exports=t(517)}};var r=require("../../../webpack-runtime.js");r.C(e);var t=e=>r(r.s=e),a=r.X(0,[948],()=>t(3353));module.exports=a})();