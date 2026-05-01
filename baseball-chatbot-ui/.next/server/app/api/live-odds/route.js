"use strict";(()=>{var e={};e.id=782,e.ids=[782],e.modules={399:e=>{e.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},517:e=>{e.exports=require("next/dist/compiled/next-server/app-route.runtime.prod.js")},2834:(e,r,t)=>{t.r(r),t.d(r,{originalPathname:()=>_,patchFetch:()=>g,requestAsyncStorage:()=>d,routeModule:()=>m,serverHooks:()=>p,staticGenerationAsyncStorage:()=>l});var a={};t.r(a),t.d(a,{GET:()=>u,dynamic:()=>c});var o=t(9303),n=t(8716),s=t(670),i=t(9567);let c="force-dynamic";async function u(){try{let e=await (0,i.Cv)(`
      SELECT
        games.game_id,
        games.game_date,
        games.away_team_id AS away_team,
        games.home_team_id AS home_team,
        games.park_id AS venue,
        round(COALESCE(models.metrics_roc_auc, 0.5)::numeric, 3) AS model_confidence,
        CASE WHEN games.home_win THEN 0.58 ELSE 0.42 END AS home_win_prob,
        CASE WHEN games.home_win THEN 0.42 ELSE 0.58 END AS away_win_prob,
        (games.home_score + games.away_score)::numeric AS over_under,
        (games.home_score - games.away_score)::numeric AS spread,
        'completed' AS status,
        games.day_night AS game_time
      FROM core.games games
      CROSS JOIN LATERAL (
        SELECT max((metrics->'validation'->>'roc_auc')::numeric) AS metrics_roc_auc
        FROM models.model_registry
        WHERE target_id = 'game_home_win'
          AND is_active
      ) models
      WHERE games.season = 2025
      ORDER BY games.game_date DESC, games.game_id DESC
      LIMIT 12
    `);return Response.json({games:e})}catch(e){return(0,i.qF)(e)}}let m=new o.AppRouteRouteModule({definition:{kind:n.x.APP_ROUTE,page:"/api/live-odds/route",pathname:"/api/live-odds",filename:"route",bundlePath:"app/api/live-odds/route"},resolvedPagePath:"/home/cbwinslow/workspace/retrosheet/baseball-chatbot-ui/app/api/live-odds/route.ts",nextConfigOutput:"",userland:a}),{requestAsyncStorage:d,staticGenerationAsyncStorage:l,serverHooks:p}=m,_="/api/live-odds/route";function g(){return(0,s.patchFetch)({serverHooks:p,staticGenerationAsyncStorage:l})}},9567:(e,r,t)=>{t.d(r,{qF:()=>g,R0:()=>m,r:()=>p,Cv:()=>c,pP:()=>d,XB:()=>_,cG:()=>l});let a=require("node:child_process"),o=require("node:path");var n=t.n(o);let s=(0,require("node:util").promisify)(a.execFile),i=n().resolve(process.cwd(),"..");async function c(e){return u(`SELECT COALESCE(jsonb_agg(row_to_json(result)), '[]'::jsonb)::text FROM (${e}) result;`,"[]")}async function u(e,r="[]"){let{stdout:t}=await s("psql",["-h",process.env.PGHOST||"localhost","-p",process.env.PGPORT||"5432","-d",process.env.PGDATABASE||"retrosheet","-X","-A","-t","-v","ON_ERROR_STOP=1","-c",e],{cwd:i,maxBuffer:20971520});return JSON.parse(t.trim()||r)}async function m(e){return(await u(e))[0]??null}async function d(e){return(await c(e))[0]??null}function l(e){return null==e?"NULL":`'${String(e).replace(/'/g,"''")}'`}function p(e){return`${l(JSON.stringify(e??null))}::jsonb`}async function _(e,r){let t=n().join(i,"scripts",e),{stdout:a,stderr:o}=await s("python3",[t,...r],{cwd:i,maxBuffer:20971520});return[a.trim(),o.trim()].filter(Boolean).join("\n")}function g(e){let r=e instanceof Error?e.message:"Unknown API error";return Response.json({error:r},{status:500})}},9303:(e,r,t)=>{e.exports=t(517)}};var r=require("../../../webpack-runtime.js");r.C(e);var t=e=>r(r.s=e),a=r.X(0,[948],()=>t(2834));module.exports=a})();