"use strict";(()=>{var e={};e.id=492,e.ids=[492],e.modules={399:e=>{e.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},1838:(e,t,r)=>{r.r(t),r.d(t,{originalPathname:()=>_,patchFetch:()=>E,requestAsyncStorage:()=>d,routeModule:()=>l,serverHooks:()=>p,staticGenerationAsyncStorage:()=>m});var a={};r.r(a),r.d(a,{GET:()=>c,dynamic:()=>u});var n=r(9303),s=r(8716),o=r(670),i=r(9567);let u="force-dynamic";async function c(){try{let[e,t,r]=await Promise.all([(0,i.Cv)(`
        SELECT object_name, row_count
        FROM (
        SELECT * FROM core.auxiliary_validation_summary
        UNION ALL SELECT * FROM features.feature_mart_validation_summary
        UNION ALL SELECT * FROM features.advanced_feature_mart_validation_summary
        UNION ALL SELECT * FROM features.temporal_production_validation_summary
        UNION ALL SELECT * FROM features.count_state_feature_mart_validation_summary
        ) summary
        ORDER BY object_name
      `),(0,i.Cv)(`
        SELECT
          target_id,
          model_name,
          feature_spec->>'feature_set' AS feature_set,
          round(((metrics->'validation'->>'roc_auc')::numeric), 4) AS roc_auc,
          round(((metrics->'validation'->>'log_loss')::numeric), 4) AS log_loss,
          (metrics->'validation'->>'rows')::integer AS validation_rows,
          created_at
        FROM models.model_registry
        WHERE is_active
        ORDER BY target_id, model_name
      `),(0,i.pP)(`
        SELECT
          count(*) FILTER (WHERE status = 'completed') AS completed_runs,
          count(*) FILTER (WHERE status <> 'completed') AS incomplete_runs,
          max(finished_at) AS last_finished_at
        FROM raw_retrosheet.ingest_runs
      `)]);return Response.json({generated_at:new Date().toISOString(),summary:e,active_models:t,ingest:r})}catch(e){return(0,i.qF)(e)}}let l=new n.AppRouteRouteModule({definition:{kind:s.x.APP_ROUTE,page:"/api/status/route",pathname:"/api/status",filename:"route",bundlePath:"app/api/status/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/status/route.ts",nextConfigOutput:"",userland:a}),{requestAsyncStorage:d,staticGenerationAsyncStorage:m,serverHooks:p}=l,_="/api/status/route";function E(){return(0,o.patchFetch)({serverHooks:p,staticGenerationAsyncStorage:m})}},9567:(e,t,r)=>{r.d(t,{qF:()=>E,R0:()=>l,r:()=>p,Cv:()=>u,pP:()=>d,XB:()=>_,cG:()=>m});let a=require("node:child_process"),n=require("node:path");var s=r.n(n);let o=(0,require("node:util").promisify)(a.execFile),i=s().resolve(process.cwd(),"..");async function u(e){return c(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function c(e,t="[]"){let{stdout:r}=await o("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(r.trim()||t)}async function l(e){return(await c(e))[0]??null}async function d(e){return(await u(e))[0]??null}function m(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function p(e){return`${m(JSON.stringify(e??null))}::jsonb`}async function _(e,t){let r=s().join(i,"scripts",e),{stdout:a,stderr:n}=await o("python3",[r,...t],{cwd:i,maxBuffer:20971520});return[a.trim(),n.trim()].filter(Boolean).join("\n")}function E(e){let t=e instanceof Error?e.message:"Unknown API error";return Response.json({error:t},{status:500})}},9303:(e,t,r)=>{e.exports=r(517)}};var t=require("../../../webpack-runtime.js");t.C(e);var r=e=>t(t.s=e),a=t.X(0,[948],()=>r(1838));module.exports=a})();