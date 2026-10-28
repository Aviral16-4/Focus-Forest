
from flask import Flask, request, redirect, session, render_template_string, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pathlib import Path
import sqlite3
import secrets
import os
import re

app = Flask(__name__)
DB = Path(__file__).with_name("focus_forest.db")

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

with connect() as con:
    con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE COLLATE NOCASE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS progress(
            user_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    row = con.execute(
        "SELECT value FROM settings WHERE name='secret'"
    ).fetchone()
    if row is None:
        con.execute(
            "INSERT INTO settings VALUES('secret', ?)",
            (secrets.token_hex(32),)
        )
    SECRET = os.environ.get("FOCUS_FOREST_SECRET")
    if not SECRET:
        SECRET = con.execute(
            "SELECT value FROM settings WHERE name='secret'"
        ).fetchone()["value"]

app.secret_key = SECRET
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

LOGIN = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Focus Forest — Grow with every task</title>
<style>
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;
background:linear-gradient(135deg,#e4efd9,#f8f7ed);font:15px system-ui;color:#24452f;padding:20px}
.wrap{width:min(900px,100%);display:grid;grid-template-columns:1fr 1fr;
background:#fffef9;border-radius:25px;overflow:hidden;box-shadow:0 20px 70px #183b241b}
.art{background:linear-gradient(145deg,#1e422c,#568b54);color:white;padding:40px;display:flex;flex-direction:column;justify-content:space-between;min-height:500px}
.logo{font-size:23px;font-weight:900}.tagline{color:#d8e8d3;font-size:12px}
.art h1{font-size:42px;line-height:1.1;margin-bottom:12px}
.art p{color:#e0ebdb;line-height:1.8}
.trees{font-size:42px;letter-spacing:5px;margin-top:25px}
.form{padding:40px;display:flex;flex-direction:column;justify-content:center}
h2{margin:7px 0}.muted{color:#778777;font-size:13px}
.tabs{display:flex;background:#edf2e8;border-radius:10px;padding:4px;margin:22px 0 15px}
.tabs button{flex:1;border:0;padding:11px;border-radius:8px;background:transparent;cursor:pointer}
.tabs button.active{background:white;color:#315e3c;font-weight:bold}
label{font-size:12px;font-weight:bold}
input{width:100%;padding:12px;margin:6px 0 15px;border:1px solid #dce5d7;border-radius:10px;font:inherit}
input:focus{outline:2px solid #b5d6a9}
.submit{width:100%;padding:13px;border:0;border-radius:10px;background:#376b4b;color:white;font-weight:bold;cursor:pointer}
.hidden{display:none}.notice{padding:11px;background:#fff0e8;color:#984d35;border-radius:9px;margin:10px 0;font-size:13px}
@media(max-width:650px){.wrap{grid-template-columns:1fr}.art{min-height:230px;padding:25px}.art h1{font-size:30px}.trees{font-size:28px;margin-top:5px}.form{padding:25px}}
</style>
</head>
<body>
<div class="wrap">
<section class="art">
<div><div class="logo">🌱 Focus Forest</div><div class="tagline">GROW WITH EVERY TASK</div></div>
<div><h1>Your goals deserve to grow.</h1>
<p>Build better study habits. Complete your tasks. Unlock plants. Create your own forest, one small win at a time.</p>
<div class="trees">🌳 🌲 🌿 🌼</div></div>
<div class="tagline">Small steps. A stronger you.</div>
</section>
<section class="form">
<div class="muted">YOUR PERSONAL PRODUCTIVITY SPACE</div>
<h2 id="heading">Welcome back</h2>
<p class="muted" id="subtitle">Log in to continue growing your forest.</p>
{% for message in get_flashed_messages() %}
<div class="notice">{{ message }}</div>
{% endfor %}
<div class="tabs">
<button id="lt" class="active" onclick="show('login')" type="button">Log in</button>
<button id="rt" onclick="show('register')" type="button">Create account</button>
</div>
<form id="login" method="post" action="/login">
<label>Username</label>
<input name="username" minlength="3" maxlength="24" required autocomplete="username" placeholder="Your username">
<label>Password</label>
<input name="password" type="password" required autocomplete="current-password" placeholder="Your password">
<button class="submit">Enter my forest →</button>
</form>
<form id="register" class="hidden" method="post" action="/register">
<label>Choose a username</label>
<input name="username" required minlength="3" maxlength="24" pattern="[A-Za-z0-9_]+" placeholder="Letters, numbers or underscores">
<label>Create a password</label>
<input id="pw" name="password" type="password" required minlength="8" autocomplete="new-password" placeholder="At least 8 characters">
<label>Confirm password</label>
<input id="confirm" name="confirm" type="password" required minlength="8" autocomplete="new-password" placeholder="Repeat your password">
<button class="submit">Create my account 🌱</button>
</form>
<p class="muted">Each account has its own saved study progress.</p>
</section>
</div>
<script>
function show(which){
let login=which==='login';
document.getElementById('login').classList.toggle('hidden',!login);
document.getElementById('register').classList.toggle('hidden',login);
document.getElementById('lt').classList.toggle('active',login);
document.getElementById('rt').classList.toggle('active',!login);
document.getElementById('heading').textContent=login?'Welcome back':'Join Focus Forest';
document.getElementById('subtitle').textContent=login?'Log in to continue growing your forest.':'Create your account and plant your first seed.';
}
document.getElementById('register').addEventListener('submit',e=>{
if(document.getElementById('pw').value!==document.getElementById('confirm').value){
e.preventDefault();alert('Passwords do not match.');
}
});
</script>
</body>
</html>
"""

APP_PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Focus Forest</title>
<style>
:root{--bg:#f3f5eb;--card:#fffef9;--ink:#203b2b;--green:#376b4b;--muted:#748273;--line:#dfe7d9}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px system-ui}
button,input,select{font:inherit}button{cursor:pointer}
.layout{display:grid;grid-template-columns:220px 1fr;min-height:100vh}
aside{background:#203d2d;color:white;padding:22px 14px;display:flex;flex-direction:column;gap:22px}
.brand{font-size:20px;font-weight:900;padding:5px}
.brand small{display:block;font-size:11px;color:#c5d9c1;font-weight:400}
nav{display:grid;gap:6px}nav button{text-align:left;background:transparent;color:#d9e7d5;border:0;padding:12px;border-radius:10px}
nav button.active,nav button:hover{background:#365b40;color:white}
.tip{margin-top:auto;background:#2d4e36;border-radius:12px;padding:14px;font-size:12px;line-height:1.8}
main{padding:28px;max-width:1450px;width:100%;margin:auto}
header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:22px}
.eyebrow{font-size:11px;letter-spacing:2px;color:var(--green);font-weight:800}
h1{font-size:30px;margin:5px 0}h2{font-size:25px;margin:0 0 5px}h3{font-size:16px;margin:0}
.muted{color:var(--muted);font-size:12px}
.profile,.pill{background:#e7efe0;padding:8px 12px;border-radius:30px;font-size:12px}
a{color:inherit}.page{display:none}.page.active{display:block}
.hero{background:linear-gradient(120deg,#20482f,#508453);color:white;border-radius:20px;padding:26px;display:flex;justify-content:space-between;align-items:center;gap:20px}
.hero h2{font-size:32px;line-height:1.15}.hero p{color:#d9e7d6;max-width:490px}.hero .big{font-size:85px}
.btn{background:var(--green);color:white;border:0;border-radius:9px;padding:10px 14px;font-weight:750}
.btn.light{background:#e6efdf;color:#244b30}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:16px 0}
.card,.stat{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:16px;box-shadow:0 6px 22px #243d2910}
.stat strong{display:block;font-size:27px;margin-top:5px}
.columns{display:grid;grid-template-columns:1.1fr .9fr;gap:15px}
.cardhead{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}
.tasklist{display:grid;gap:8px}.task{display:flex;gap:9px;align-items:center;border:1px solid var(--line);border-radius:10px;background:white;padding:10px}
.task.done{opacity:.65}.task.done .tasktitle{text-decoration:line-through}
.taskbody{flex:1;min-width:0}.tasktitle{font-weight:750;overflow-wrap:anywhere}
.meta{font-size:10px;color:var(--muted);margin-top:4px}
.check{width:24px;height:24px;border:1px solid #a8b9a3;background:white;border-radius:7px;color:white}
.done .check{background:var(--green)}
.small{border:0;background:transparent;padding:5px;color:var(--muted)}
.field{padding:10px;border:1px solid var(--line);border-radius:9px;background:white;min-width:0;width:100%;color:var(--ink)}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.toolbar>*{flex:1}.bar{height:9px;border-radius:20px;background:#e5ecdf;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,#6b9b60,#bbd990)}
.forest{min-height:200px;position:relative;overflow:hidden;border-radius:14px;margin-top:12px;display:flex;align-items:flex-end;justify-content:center;flex-wrap:wrap;gap:10px;padding:25px 10px 15px;background:linear-gradient(#dcebd9,#bdd9b5 60%,#83b26e 60%,#4f8751);isolation:isolate}
.forest:before{content:"";position:absolute;top:14px;right:12%;width:58px;height:58px;border-radius:50%;background:#fff1ac;box-shadow:0 0 35px #fff4be;z-index:-1}
.forest:after{content:"";position:absolute;left:-10%;right:-10%;bottom:-45%;height:80%;border-radius:50%;background:#52894e;z-index:-1}
.tree{z-index:1;text-align:center;animation:sway 3.8s ease-in-out infinite;transform-origin:bottom}
.tree:nth-child(even){animation-delay:-1.5s}.tree .emoji{font-size:clamp(35px,4vw,57px);display:block;animation:leaf 3s ease-in-out infinite}
.tree small{font-size:9px;background:#ffffffc9;padding:3px 5px;border-radius:15px}
@keyframes sway{50%{transform:rotate(2deg) translateY(-3px)}}
@keyframes leaf{50%{transform:rotate(-3deg)}}
.scene-night{background:linear-gradient(#111f43,#384d70 60%,#294c3b 60%,#17392d)}
.scene-night:before{background:#e5eaff;box-shadow:0 0 30px #c7dcff}
.scene-rain{background:linear-gradient(#8398a3,#b4c7c6 60%,#72986a 60%,#426a43)}
.scene-rain:before{opacity:0}
.scene-snow{background:linear-gradient(#cbdce5,#eef4f4 60%,#d9e5d1 60%,#a2bea0)}
.scene-snow:before{opacity:0}
.scene-storm{background:linear-gradient(#4e5a6a,#7a8b91 60%,#577a5b 60%,#34553a)}
.scene-fog{background:linear-gradient(#b8c9c5,#e1e7df 60%,#91ad8c 60%,#71956c)}
.cloud{position:absolute;top:18%;left:-25%;width:90px;height:25px;border-radius:30px;background:#ffffffa8;animation:clouds 35s linear infinite;z-index:0}
.cloud:before,.cloud:after{content:"";position:absolute;border-radius:50%;background:inherit;width:40px;height:35px;top:-15px;left:15px}
.cloud:after{left:40px;width:48px;height:42px;top:-20px}
@keyframes clouds{to{left:115%}}
.particle{position:absolute;top:-20px;z-index:0;animation:fall 2s linear infinite;color:#e8f5ff}
@keyframes fall{to{transform:translateY(300px) translateX(15px)}}
.progress{display:flex;justify-content:space-between;margin:12px 0 6px;font-size:12px}
.gridplants{display:grid;grid-template-columns:1fr 1fr;gap:7px}
.plant{display:flex;gap:8px;align-items:center;padding:9px;border:1px solid var(--line);border-radius:9px;background:white;font-size:12px}
.locked{opacity:.45;filter:grayscale(1)}
.ranklist{display:grid;gap:8px}.rank{display:grid;grid-template-columns:35px 1fr auto;gap:8px;align-items:center;background:white;border:1px solid var(--line);border-radius:10px;padding:11px}
.ranknum{background:#edf2e8;border-radius:8px;padding:6px;text-align:center;font-weight:bold}
.achievements{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.achievement{min-height:165px;transition:.2s}.achievement:hover{transform:translateY(-3px)}
.achievement.unlocked{background:linear-gradient(145deg,#fffef9,#eaf5e5);border-color:#b6d3a8}
.medal{font-size:30px}.achievement strong{display:block;margin:7px 0}.achievement p{font-size:12px;color:var(--muted)}
.abar{height:7px;background:#e5ecdf;border-radius:10px;overflow:hidden}.abar div{height:100%;background:#77a76b}
.modalback{display:none;position:fixed;inset:0;background:#102319a8;z-index:5;align-items:center;justify-content:center;padding:15px}
.modalback.show{display:flex}.modal{background:var(--card);padding:22px;border-radius:16px;width:min(500px,100%);max-height:92vh;overflow:auto}
.formgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.group{display:grid;gap:5px}.group.full{grid-column:1/-1}.group label{font-size:11px;font-weight:800;color:var(--muted)}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:#203d2d;color:white;padding:12px 18px;border-radius:10px;z-index:10;display:none}
@media(max-width:900px){.columns{grid-template-columns:1fr}.achievements{grid-template-columns:repeat(2,1fr)}}
@media(max-width:650px){.layout{grid-template-columns:1fr}aside{padding:12px;gap:10px}.brand{font-size:17px}nav{display:flex;overflow:auto}nav button{white-space:nowrap;padding:9px}main{padding:15px 10px}.profile{font-size:10px}.hero{padding:18px}.hero h2{font-size:25px}.hero .big{font-size:48px}.stats{grid-template-columns:repeat(2,1fr)}.stat{padding:12px}.stat strong{font-size:23px}.achievements{grid-template-columns:1fr 1fr}.formgrid{grid-template-columns:1fr}.group.full{grid-column:auto}}
</style>
</head>
<body>
<div class="layout">
<aside>
<div class="brand">🌱 Focus Forest<small>Grow with every task</small></div>
<nav>
<button class="active" data-page="dashboard">⌂ Dashboard</button>
<button data-page="planner">☷ Study planner</button>
<button data-page="forest">🌳 My forest</button>
<button data-page="leaderboard">🏆 Leaderboard</button>
<button data-page="achievements">✦ Achievements</button>
</nav>
<div class="tip">🌿 <b>Little by little</b><br>Every task is a seed. Keep showing up and your forest will grow.<br><br><button class="btn light" onclick="openModal()">＋ Add a task</button></div>
</aside>
<main>
<header><div><div class="eyebrow" id="dateLabel"></div><h1 id="heading">Good to see you, grower 🌿</h1></div><div class="profile">👤 <b>{{ username }}</b> · <span id="level">Level 1</span> · <a href="/logout">Log out</a></div></header>

<section class="page active" id="page-dashboard">
<div class="hero"><div><span class="pill">YOUR DAILY RESET</span><h2>Small steps.<br>A growing world.</h2><p>Focus on what matters today. Every task you finish helps your little corner of the world bloom.</p><button class="btn light" onclick="go('planner')">View my tasks →</button></div><div class="big" id="heroTree">🌳</div></div>
<div class="stats">
<div class="stat"><span class="muted">✓ Tasks completed</span><strong id="statDone">0</strong><span class="muted" id="statOpen"></span></div>
<div class="stat"><span class="muted">✨ Growth XP</span><strong id="statXP">0</strong><span class="muted">Every action adds up</span></div>
<div class="stat"><span class="muted">🔥 Day streak</span><strong id="statStreak">0 days</strong><span class="muted">Consistency over perfection</span></div>
<div class="stat"><span class="muted">🌱 Plants unlocked</span><strong id="statPlants">1</strong><span class="muted">Your garden is growing</span></div>
</div>
<div class="columns">
<div class="card"><div class="cardhead"><div><h3>Today's priorities</h3><div class="muted" id="todaySub">One task at a time.</div></div><button class="small" onclick="go('planner')">View all →</button></div><div id="dashboardTasks" class="tasklist"></div><br><button class="btn" onclick="openModal()">＋ Add new task</button></div>
<div class="card"><div class="cardhead"><div><h3>Your forest is growing</h3><div class="muted">Your effort, made visible.</div></div><button class="small" onclick="go('forest')">Explore →</button></div><div class="progress"><span>Today's progress</span><b id="progressText">0%</b></div><div class="bar"><div class="fill" id="progressBar" style="width:0%"></div></div><div id="miniForest" class="forest"></div><p class="muted">Next unlock: <b id="nextUnlock">Daisy</b></p></div>
</div>
</section>

<section class="page" id="page-planner">
<h2>Your study planner</h2><p class="muted">Make the next step clear. Finish tasks to grow your forest.</p>
<div class="toolbar"><input class="field" id="search" placeholder="Search tasks..." oninput="renderTasks()"><select class="field" id="status" onchange="renderTasks()"><option value="all">All tasks</option><option value="open">To do</option><option value="done">Completed</option></select><button class="btn" onclick="openModal()">＋ New task</button></div>
<div class="card"><div class="cardhead"><h3 id="taskCount">All tasks</h3><span class="pill" id="plannerXP">0 XP</span></div><div id="plannerTasks" class="tasklist"></div></div>
</section>

<section class="page" id="page-forest">
<h2>Your little corner of nature 🌳</h2><p class="muted">Earn XP, unlock plants, and choose the garden vibe that feels like you.</p>
<div class="card" style="margin-bottom:14px"><div class="cardhead"><div><h3 id="weatherTitle">Checking local weather...</h3><div class="muted" id="weatherDetail">Your forest adapts to local conditions.</div></div><button class="btn" onclick="loadWeather(true)">↻ Refresh weather</button></div><div class="muted" id="weatherSource">Weather requires location permission and internet access.</div></div>
<div class="toolbar"><label style="align-self:center">Garden mood</label><select id="theme" class="field" onchange="changeTheme(this.value)"><option value="spring">Spring meadow 🌼</option><option value="mystic">Mystic forest 🌙</option><option value="tropical">Tropical garden 🌴</option><option value="autumn">Autumn grove 🍂</option></select><span class="pill" id="forestXP">0 XP</span></div>
<div class="columns"><div class="card"><div class="cardhead"><div><h3>My forest</h3><div class="muted" id="forestCount">1 plant unlocked</div></div><button class="btn" onclick="decorate()">✨ Decoration · 20 XP</button></div><div class="forest bigforest" id="bigForest"></div><p class="muted">Plants unlock as your XP grows. Decorations cost 20 XP.</p></div><div class="card"><h3>Plant collection</h3><p class="muted">Keep growing to unlock them all.</p><div class="gridplants" id="collection"></div></div></div>
</section>

<section class="page" id="page-leaderboard">
<h2>Grow together 🏆</h2><p class="muted">Friendly competition. The sample players are fictional.</p><div class="card"><div class="cardhead"><h3>Forest growers</h3><div><button class="btn" onclick="setPeriod('week')">This week</button> <button class="btn" onclick="setPeriod('all')">All time</button></div></div><div id="ranks" class="ranklist"></div><p class="muted">A shared leaderboard across devices requires a hosted database.</p></div>
</section>

<section class="page" id="page-achievements">
<h2>Little wins, big growth ✨</h2><p class="muted">Collect milestones at your own pace.</p><div id="badges" class="achievements"></div>
</section>
</main>
</div>

<div class="modalback" id="modal" onclick="if(event.target===this)closeModal()"><div class="modal">
<div class="cardhead"><h3 id="modalTitle">Plant a new task 🌱</h3><button class="small" onclick="closeModal()">✕</button></div>
<form id="taskForm"><input type="hidden" id="editId"><div class="formgrid">
<div class="group full"><label>Task name *</label><input class="field" id="title" required maxlength="120" placeholder="e.g. Revise neural networks"></div>
<div class="group"><label>Subject / category</label><input class="field" id="subject" maxlength="50" placeholder="e.g. Deep Learning"></div>
<div class="group"><label>Priority</label><select class="field" id="priority"><option value="high">High</option><option value="medium" selected>Medium</option><option value="low">Low</option></select></div>
<div class="group"><label>Due date</label><input class="field" id="due" type="date"></div>
<div class="group"><label>Estimated minutes</label><input class="field" id="minutes" type="number" min="5" max="1440" value="30"></div>
<div class="group full"><label>Notes</label><input class="field" id="description" maxlength="300" placeholder="What does done look like?"></div>
</div><div style="display:flex;justify-content:flex-end;gap:8px;margin-top:15px"><button type="button" class="btn light" onclick="closeModal()">Cancel</button><button class="btn">Save task</button></div></form>
</div></div>
<div id="toast" class="toast"></div>

<script>
const USER={{ username|tojson }};
const KEY='focusForest.user.'+USER;
const $=id=>document.getElementById(id);
const plants=[['Tiny Sprout','🌱',0],['Daisy Patch','🌼',50],['Pine Tree','🌲',100],['Cherry Blossom','🌸',180],['Palm Tree','🌴',280],['Magic Mushroom','🍄',400],['Sunflower','🌻',550],['Autumn Maple','🍁',750],['Moonlit Tree','🌳',1000]];
const demo=[['Maya Chen',860],['Arjun Mehta',720],['Luna Park',640],['Noah Wilson',510],['Isha Rao',390]];
function today(){let d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0')}
function fresh(){return {tasks:[],xp:0,days:[],theme:'spring',decorations:0}}
function load(){try{let s=JSON.parse(localStorage.getItem(KEY));if(s&&Array.isArray(s.tasks))return {...fresh(),...s}}catch(e){}return fresh()}
let state=load(),period='all',weather={mode:new Date().getHours()>=6&&new Date().getHours()<18?'day':'night',kind:'clear',temp:null,wind:0,place:'Local area',desc:'Local conditions'},toastTimer;
function persist(){try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){notify('Browser storage is unavailable')}renderAll()}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function notify(s){$('toast').textContent=s;$('toast').style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').style.display='none',2300)}
function completed(){return state.tasks.filter(t=>t.done)}
function plantsOpen(){return plants.filter(p=>p[2]<=state.xp)}
function streak(){let days=[...new Set(state.days)].sort().reverse();if(!days.length)return 0;let d=new Date(today()+'T12:00:00');if(days[0]!==today()){d.setDate(d.getDate()-1);if(days[0]!==d.toISOString().slice(0,10))return 0}let n=0;for(let day of days){if(day===d.toISOString().slice(0,10)){n++;d.setDate(d.getDate()-1)}else break}return n}
function progress(){let a=state.tasks.filter(t=>t.due===today());return a.length?Math.round(a.filter(t=>t.done).length/a.length*100):0}
function taskHTML(t,compact=false){return `<div class="task ${t.done?'done':''}"><button class="check" onclick="toggleTask('${t.id}')">${t.done?'✓':''}</button><div class="taskbody"><div class="tasktitle">${esc(t.title)}</div><div class="meta"><span>${esc(t.priority.toUpperCase())} · ${esc(t.subject||'General')} · ${t.minutes} min</span>${t.due?' · 📅 '+esc(t.due):''}</div>${!compact&&t.description?`<div class="muted">${esc(t.description)}</div>`:''}</div>${compact?'':`<button class="small" onclick="editTask('${t.id}')">✎</button><button class="small" onclick="deleteTask('${t.id}')">⌫</button>`}</div>`}
function renderTasks(){let list=[...state.tasks].sort((a,b)=>Number(a.done)-Number(b.done));$('dashboardTasks').innerHTML=list.filter(t=>t.due===today()||!t.due).slice(0,4).map(t=>taskHTML(t,true)).join('')||'<div class="muted">No tasks yet. Plant your first seed!</div>';let q=$('search').value.toLowerCase(),status=$('status').value;list=list.filter(t=>(t.title+' '+t.subject+' '+t.description).toLowerCase().includes(q)&&(status==='all'||(status==='done'?t.done:!t.done)));$('plannerTasks').innerHTML=list.map(t=>taskHTML(t)).join('')||'<div class="muted">No matching tasks.</div>';$('taskCount').textContent=list.length+' tasks';$('plannerXP').textContent=state.xp+' XP'}
function scene(trees){let particles='';if(['rain','storm'].includes(weather.kind)){for(let i=0;i<35;i++)particles+=`<i class="particle" style="left:${i*3%100}%;animation-delay:-${i%8*.2}s">╱</i>`}if(weather.kind==='snow'){for(let i=0;i<25;i++)particles+=`<i class="particle" style="left:${i*4%100}%;animation-duration:${4+i%4}s">❄</i>`}let cls='forest scene-'+weather.mode+(weather.kind!=='clear'?' scene-'+weather.kind:'');return `<div class="${cls}"><div class="cloud"></div><div class="cloud" style="top:35%;animation-delay:-17s;opacity:.5"></div>${particles}${weather.mode==='night'?'<span style="position:absolute;top:8%;left:10%;color:white">✦　·　✧　·　✦</span>':''}${trees}</div>`}
function renderForest(){let open=plantsOpen();let trees=open.map((p,i)=>`<div class="tree" style="animation-delay:-${i*.4}s"><span class="emoji">${p[1]}</span><small>${p[0]}</small></div>`).join('')+'<div class="tree"><span class="emoji">🪨</span><small>Stone</small></div>'.repeat(Math.min(state.decorations,8));$('miniForest').outerHTML=scene(trees).replace('<div class="forest','<div id="miniForest" class="forest');$('bigForest').outerHTML=scene(trees).replace('<div class="forest','<div id="bigForest" class="forest');$('forestCount').textContent=open.length+' of '+plants.length+' plants unlocked';$('forestXP').textContent=state.xp+' XP';$('collection').innerHTML=plants.map(p=>`<div class="plant ${state.xp>=p[2]?'':'locked'}"><span class="emoji">${state.xp>=p[2]?p[1]:'🔒'}</span><div><b>${p[0]}</b><div class="muted">${state.xp>=p[2]?'Unlocked':p[2]+' XP'}</div></div></div>`).join('');let next=plants.find(p=>p[2]>state.xp);$('nextUnlock').textContent=next?`${next[2]-state.xp} XP · ${next[0]}`:'All plants unlocked';$('heroTree').textContent=open[open.length-1][1];$('theme').value=state.theme}
function renderRanks(){let users=demo.map(u=>({name:u[0],xp:period==='week'?Math.round(u[1]*.35):u[1]}));users.push({name:USER,xp:state.xp,me:true});users.sort((a,b)=>b.xp-a.xp);$('ranks').innerHTML=users.map((u,i)=>`<div class="rank" style="${u.me?'border-color:#8db786;background:#f1f8ed':''}"><div class="ranknum">${i===0?'👑':i+1}</div><div><b>${esc(u.name)}${u.me?' (you)':''}</b><div class="muted">🌱 Growing every day</div></div><b>${u.xp} XP</b></div>`).join('')}
function renderBadges(){let n=completed().length,s=streak(),p=plantsOpen().length,h=completed().filter(t=>t.priority==='high').length;let b=[['🌱','First Seed','Complete 1 task',n,1,'COMMON'],['🌿','Getting Grounded','Complete 5 tasks',n,5,'COMMON'],['🌳','Forest Builder','Complete 15 tasks',n,15,'RARE'],['🏆','Task Champion','Complete 30 tasks',n,30,'EPIC'],['🔥','Three-Day Spark','Build a 3-day streak',s,3,'RARE'],['⚡','Week Warrior','Build a 7-day streak',s,7,'EPIC'],['📚','Deep Focus','Complete 10 tasks',n,10,'RARE'],['🌼','Bloom Time','Earn 50 XP',state.xp,50,'COMMON'],['✨','XP Collector','Earn 250 XP',state.xp,250,'RARE'],['💎','XP Legend','Earn 1000 XP',state.xp,1000,'LEGENDARY'],['🌲','Evergreen','Earn 100 XP',state.xp,100,'COMMON'],['🏡','Garden Keeper','Unlock 5 plant types',p,5,'EPIC'],['🌺','Botanical Master','Unlock all plants',p,9,'LEGENDARY'],['🎯','Priority Pro','Complete 5 high-priority tasks',h,5,'RARE'],['🧠','Consistent Mind','Complete 50 tasks',n,50,'LEGENDARY'],['🪴','Decoration Lover','Add 3 decorations',state.decorations,3,'RARE']];$('badges').innerHTML=b.map(x=>{let pct=Math.min(100,Math.round(x[3]/x[4]*100)),ok=x[3]>=x[4];return `<div class="card achievement ${ok?'unlocked':''}"><div class="medal">${x[0]}</div><strong>${x[1]}</strong><p>${x[2]}</p><div class="muted">${x[5]} · ${ok?'✓ UNLOCKED':x[3]+' / '+x[4]}</div><div class="abar"><div style="width:${pct}%"></div></div></div>`}).join('')}
function renderAll(){renderTasks();renderForest();renderRanks();renderBadges();let n=completed().length;$('statDone').textContent=n;$('statXP').textContent=state.xp;$('statStreak').textContent=streak()+' days';$('statPlants').textContent=plantsOpen().length;$('statOpen').textContent=(state.tasks.length-n)+' tasks remaining';$('progressText').textContent=progress()+'%';$('progressBar').style.width=progress()+'%';$('todaySub').textContent=state.tasks.filter(t=>t.due===today()&&t.done).length+' of '+state.tasks.filter(t=>t.due===today()).length+' due today completed';$('level').textContent='Level '+(Math.floor(state.xp/100)+1);$('dateLabel').textContent=new Date().toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'})}
function go(page){document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id==='page-'+page));document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('active',b.dataset.page===page));let labels={dashboard:'Good to see you, grower 🌿',planner:'One task at a time ✍️',forest:'Look what you are growing 🌳',leaderboard:'Grow together 🏆',achievements:'Little wins, big growth ✨'};$('heading').textContent=labels[page];window.scrollTo({top:0,behavior:'smooth'})}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>go(b.dataset.page));
function openModal(id=null){$('taskForm').reset();$('editId').value='';$('due').value=today();$('minutes').value=30;$('modalTitle').textContent='Plant a new task 🌱';if(id){let t=state.tasks.find(x=>x.id===id);if(!t)return;$('editId').value=id;$('title').value=t.title;$('subject').value=t.subject;$('priority').value=t.priority;$('due').value=t.due;$('minutes').value=t.minutes;$('description').value=t.description||'';$('modalTitle').textContent='Edit task'}$('modal').classList.add('show')}
function closeModal(){$('modal').classList.remove('show')}
$('taskForm').onsubmit=e=>{e.preventDefault();let id=$('editId').value,data={title:$('title').value.trim(),subject:$('subject').value.trim()||'General',priority:$('priority').value,due:$('due').value,minutes:+$('minutes').value||30,description:$('description').value.trim()};if(!data.title)return;if(id){Object.assign(state.tasks.find(t=>t.id===id),data);notify('Task updated')}else{state.tasks.push({...data,id:Date.now().toString(),done:false,reward:0});notify('New seed planted 🌱')}closeModal();persist()};
function editTask(id){openModal(id)}
function deleteTask(id){let t=state.tasks.find(x=>x.id===id);if(!t||!confirm('Delete this task?'))return;if(t.done)state.xp=Math.max(0,state.xp-(t.reward||0));state.tasks=state.tasks.filter(x=>x.id!==id);persist();notify('Task deleted')}
function toggleTask(id){let t=state.tasks.find(x=>x.id===id);if(!t)return;if(!t.done){t.done=true;t.reward=t.priority==='high'?50:t.priority==='medium'?25:10;state.xp+=t.reward;if(!state.days.includes(today()))state.days.push(today());notify('Well done! +'+t.reward+' XP 🌱')}else{t.done=false;state.xp=Math.max(0,state.xp-(t.reward||0));t.reward=0;notify('Task reopened')}persist()}
function setPeriod(p){period=p;renderRanks()}
function changeTheme(t){state.theme=t;persist();notify('Garden mood updated')}
function decorate(){if(state.xp<20){notify('You need 20 XP first!');return}state.xp-=20;state.decorations++;persist();notify('Decoration added 🪨')}
async function loadWeather(show=false){let h=new Date().getHours();weather.mode=h>=6&&h<18?'day':'night';weather.kind='clear';weather.temp=null;weather.desc=weather.mode==='night'?'Clear night':'Clear skies';weather.wind=0;try{if(!navigator.geolocation)throw Error();let pos=await new Promise((ok,no)=>navigator.geolocation.getCurrentPosition(ok,no,{timeout:8000,maximumAge:600000}));let url=`https://api.open-meteo.com/v1/forecast?latitude=${pos.coords.latitude}&longitude=${pos.coords.longitude}&current=temperature_2m,is_day,weather_code,wind_speed_10m&timezone=auto`;let r=await fetch(url);if(!r.ok)throw Error();let d=(await r.json()).current;weather.mode=d.is_day?'day':'night';weather.temp=d.temperature_2m;weather.wind=d.wind_speed_10m||0;let c=d.weather_code;weather.kind=c>=95?'storm':(c>=71&&c<=77||c===85||c===86)?'snow':(c>=51&&c<=67||c>=80&&c<=82)?'rain':(c===45||c===48)?'fog':c===0?'clear':'cloudy';weather.desc=({clear:'Clear skies',cloudy:'Cloudy',rain:'Rainy',snow:'Snowy',fog:'Foggy',storm:'Thunderstorm'})[weather.kind]||'Changing skies';$('weatherSource').textContent='Live weather from Open-Meteo';}catch(e){$('weatherSource').textContent='Live weather unavailable; showing local day/night.'}let icons={clear:weather.mode==='night'?'🌙':'☀️',cloudy:'⛅',rain:'🌧️',snow:'🌨️',fog:'🌫️',storm:'⛈️'};$('weatherTitle').textContent=(weather.mode==='night'?'Night forest':'Daytime forest')+' · '+weather.desc+(weather.temp===null?'':' · '+Math.round(weather.temp)+'°C');$('weatherDetail').textContent=weather.temp!==null&&weather.temp<=12?'Chilly air · your forest is feeling cool.':weather.wind>=25?'A breezy day in your forest.':'Your forest follows the local weather.';document.querySelectorAll('.forest').forEach(el=>{el.classList.remove('scene-night','scene-rain','scene-snow','scene-storm','scene-fog');if(weather.mode==='night')el.classList.add('scene-night');if(['rain','snow','storm','fog'].includes(weather.kind))el.classList.add('scene-'+weather.kind)});if(show)notify('Weather refreshed 🌦️');}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
renderAll();loadWeather();setInterval(()=>{if((new Date().getHours()>=6&&new Date().getHours()<18?'day':'night')!==weather.mode)loadWeather()},60000);
</script>
</body>
</html>
"""

@app.get("/")
def home():
    if "user_id" not in session:
        return render_template_string(LOGIN)
    with connect() as con:
        row = con.execute(
            "SELECT data FROM progress WHERE user_id=?",
            (session["user_id"],)
        ).fetchone()
    # The browser stores this user's planner data under their username.
    # The database account is used for registration and login.
    return render_template_string(APP_PAGE, username=session["username"])

@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm", "")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,24}", username):
        flash("Use 3–24 letters, numbers or underscores for your username.")
        return redirect("/")
    if len(password) < 8:
        flash("Password must be at least 8 characters.")
        return redirect("/")
    if password != confirm:
        flash("Passwords do not match.")
        return redirect("/")
    try:
        with connect() as con:
            cur = con.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                (username, generate_password_hash(password))
            )
            con.execute("INSERT INTO progress(user_id,data) VALUES(?,?)",
                        (cur.lastrowid, "{}"))
            user_id = cur.lastrowid
    except sqlite3.IntegrityError:
        flash("That username already exists. Choose another.")
        return redirect("/")
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    return redirect("/")

@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    with connect() as con:
        user = con.execute(
            "SELECT id,username,password FROM users WHERE username=? COLLATE NOCASE",
            (username,)
        ).fetchone()
    if user is None or not check_password_hash(user["password"], password):
        flash("Incorrect username or password.")
        return redirect("/")
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect("/")

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    print("Focus Forest is starting!")
    print("Open http://127.0.0.1:5000 in your browser.")
    app.run(debug=True)
