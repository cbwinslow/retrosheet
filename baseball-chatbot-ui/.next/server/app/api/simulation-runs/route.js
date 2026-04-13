"use strict";(()=>{var e={};e.id=421,e.ids=[421],e.modules={517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},5333:(e,r,t)=>{t.r(r),t.d(r,{headerHooks:()=>m,originalPathname:()=>h,patchFetch:()=>b,requestAsyncStorage:()=>p,routeModule:()=>c,serverHooks:()=>_,staticGenerationAsyncStorage:()=>d,staticGenerationBailout:()=>f});var n={};t.r(n),t.d(n,{GET:()=>l,dynamic:()=>u});var i=t(5419),o=t(9108),s=t(9678),a=t(3023);let u="force-dynamic";async function l(){try{let e=await (0,a.Cv)(`
      SELECT
        simulation_run_id,
        requested_at,
        run_name,
        run_mode,
        filters,
        historical_half_innings,
        round(expected_runs, 4) AS expected_runs,
        round(run_probability, 4) AS run_probability,
        round(all_left_handed_batters_hit_probability, 4) AS all_left_handed_batters_hit_probability,
        sample_size,
        notes
      FROM predictions.recent_simulation_runs
      LIMIT 25
    `);return Response.json({runs:e})}catch(e){return(0,a.qF)(e)}}let c=new i.AppRouteRouteModule({definition:{kind:o.x.APP_ROUTE,page:"/api/simulation-runs/route",pathname:"/api/simulation-runs",filename:"route",bundlePath:"app/api/simulation-runs/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/simulation-runs/route.ts",nextConfigOutput:"",userland:n}),{requestAsyncStorage:p,staticGenerationAsyncStorage:d,serverHooks:_,headerHooks:m,staticGenerationBailout:f}=c,h="/api/simulation-runs/route";function b(){return(0,s.patchFetch)({serverHooks:_,staticGenerationAsyncStorage:d})}},3023:(e,r,t)=>{t.d(r,{qF:()=>f,R0:()=>c,r:()=>_,Cv:()=>u,pP:()=>p,XB:()=>m,cG:()=>d});let n=require("node:child_process"),i=require("node:path");var o=t.n(i);let s=(0,require("node:util").promisify)(n.execFile),a=o().resolve(process.cwd(),"..");async function u(e){return l(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function l(e,r="[]"){let{stdout:t}=await s("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:a,maxBuffer:20971520});return JSON.parse(t.trim()||r)}async function c(e){return(await l(e))[0]??null}async function p(e){return(await u(e))[0]??null}function d(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function _(e){return`${d(JSON.stringify(e??null))}::jsonb`}async function m(e,r){let t=o().join(a,"scripts",e),{stdout:n,stderr:i}=await s("python3",[t,...r],{cwd:a,maxBuffer:20971520});return[n.trim(),i.trim()].filter(Boolean).join("\n")}function f(e){let r=e instanceof Error?e.message:"Unknown API error";return Response.json({error:r},{status:500})}},5419:(e,r,t)=>{e.exports=t(517)}};var r=require("../../../webpack-runtime.js");r.C(e);var t=e=>r(r.s=e),n=r.X(0,[638],()=>t(5333));module.exports=n})();