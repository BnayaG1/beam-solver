# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r"c:\Users\User\Desktop\beam_canvas_component\index.html")
t = p.read_text(encoding="utf-8")

CHAIN_JS = r'''
function fmtX(v){return Math.round(v*1000)/1000;}
function ensureChain(){if(!G.chain)G.chain={active:false,cursorXw:null,marks:[],previewXw:null};}
function resetChain(){G.chain={active:true,cursorXw:G.L,marks:[],previewXw:null};markCanvasDirty();drawAll();syncChainPanel();}
function startChainFromRight(){ensureChain();G.chain.active=true;if(!G.chain.marks.length)G.chain.cursorXw=G.L;else G.chain.cursorXw=G.chain.marks[G.chain.marks.length-1].x;G.chain.previewXw=null;markCanvasDirty();syncChainPanel();drawAll();}
function addChainSegment(dist){ensureChain();if(!G.chain.active)startChainFromRight();var d=Math.max(0,parseFloat(dist)||0);if(d<1e-9)return;var x=Math.max(0,G.chain.cursorXw-d);G.chain.marks.push({id:uid(),seg:d,x:x});G.chain.cursorXw=x;G.chain.previewXw=null;markCanvasDirty();drawAll();syncChainPanel();}
function nearRightEnd(xw){return xw>=G.L-0.2*G.L;}
function drawChainDim(g){ensureChain();if(!G.chain.active&&!G.chain.marks.length)return;var yD=g.y+64,yB=g.y+8;
var xR=xPix(G.L),x0=xPix(0);ctx.strokeStyle="#0f766e";ctx.fillStyle="#0f766e";ctx.lineWidth=1.5;ctx.font="11px sans-serif";
ctx.beginPath();ctx.moveTo(xR,yD);ctx.lineTo(x0,yD);ctx.stroke();
function tick(px,lab,onBeam){ctx.beginPath();ctx.moveTo(px,yD);ctx.lineTo(px,yD-10);ctx.stroke();ctx.beginPath();ctx.moveTo(px,g.y);ctx.lineTo(px,g.y-14);ctx.strokeStyle="#0f766e";ctx.stroke();
ctx.fillStyle="#0f766e";ctx.textAlign="center";ctx.fillText(lab,px,yD-14);if(onBeam!==false){ctx.beginPath();ctx.arc(px,g.y,4,0,Math.PI*2);ctx.fill();}}
ctx.fillText("ימין (L="+fmtX(G.L)+")",xR,yD+16);tick(xR,"0",true);
var prevX=G.L;for(var i=0;i<G.chain.marks.length;i++){var m=G.chain.marks[i],px=xPix(m.x);
var mid=xPix((prevX+m.x)/2);ctx.fillStyle="#047857";ctx.fillText(fmtX(m.seg),mid,yD-26);tick(px,fmtX(m.x),true);prevX=m.x;}
var cur=G.chain.cursorXw!=null?G.chain.cursorXw:G.L;
if(G.chain.previewXw!=null&&G.tool==="chain_r"){var pp=xPix(G.chain.previewXw);ctx.setLineDash([5,4]);ctx.strokeStyle="#14b8a6";
ctx.beginPath();ctx.moveTo(xPix(cur),yD);ctx.lineTo(pp,yD);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#0d9488";
var pd=Math.max(0,cur-G.chain.previewXw);ctx.fillText("? "+fmtX(pd),xPix((cur+G.chain.previewXw)/2),yD-26);}}
function syncChainPanel(){var el=document.getElementById("chainPanel");if(!el)return;var on=G.tool==="chain_r";el.classList.toggle("on",on);
if(!on)return;var st=document.getElementById("chainStatus");if(!st)return;ensureChain();
var rem=G.chain.active&&G.chain.cursorXw!=null?G.chain.cursorXw:0;
st.textContent=G.chain.active?"מיקום שמאלי נוכחי: x="+fmtX(rem)+" m | נשאר עד הקצה השמאלי: "+fmtX(rem)+" m":"לחץ על הקצה הימני של הקורה (ליד L) כדי להתחיל, או לחץ התחל מימין.";
var inp=document.getElementById("chainDistInp");if(inp&&document.activeElement!==inp)inp.placeholder=G.chain.active?"מרחק שמאלה [m]":"...";}
'''

inserts = [
    (
        "#btnApply:hover{background:#047857}",
        "#btnApply:hover{background:#047857}\n#chainPanel{display:none;flex-wrap:wrap;gap:10px;padding:12px;border:2px solid #0f766e;border-radius:10px;background:#ecfdf5;direction:rtl;align-items:flex-end}\n#chainPanel.on{display:flex}\n#chainPanel h4{width:100%;margin:0;color:#0f766e;font-size:14px}\n#chainPanel label{display:flex;flex-direction:column;gap:4px;font-weight:600;font-size:13px}\n#chainPanel input{width:100px;padding:6px}\n#chainPanel button{padding:8px 14px;border-radius:8px;border:2px solid #0f766e;background:#fff;cursor:pointer;font-weight:600}\n#chainPanel button:hover{background:#d1fae5}\n#chainPanel .chain-status{flex-basis:100%;font-size:12px;color:#475569;line-height:1.5}",
    ),
    (
        '<button type="button" data-tool="del">מחק נבחר</button>',
        '<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">מחק נבחר</button>',
    ),
    (
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">',
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">',
    ),
    (
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>',
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>',
    ),
    (
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">',
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">',
    ),
]

# Fix duplicate - only do del button replace once
if 'data-tool="chain_r"' not in t:
    t = t.replace(
        '<button type="button" data-tool="del">מחק נבחר</button>',
        '<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">מחק נבחר</button>',
    )

if "#chainPanel" not in t:
    t = t.replace(
        "#btnApply:hover{background:#047857}",
        inserts[0][1],
    )

if 'id="chainPanel"' not in t:
    t = t.replace(
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">מחק נבחר</button>\n</motion_n">',
        '<motion_n">מומנט שלילי</button>\n<button type="button" data-tool="chain_r">מרחקים מימין</button>\n<button type="button" data-tool="del">מחק נבחר</button>\n</motion_n">',
    )
    # simpler insert after palette closing
    t = t.replace(
        '</div><motion_n">',
        '</motion_n">',
    )

if 'id="chainPanel"' not in t:
    t = t.replace(
        '</div><div id="main">',
        '</div><div id="chainPanel"><h4>סימון מרחקים מהקצה הימני (שמאלה)</h4>'
        '<p class="chain-status" id="chainStatus">בחר כלי ולחץ על הקצה הימני של הקורה.</p>'
        '<label>מרחק קטע שמאלה [m]<input type="number" id="chainDistInp" step="0.1" min="0" placeholder="למשל 2.5"/></label>'
        '<button type="button" id="chainAddBtn">הוסף נקודה</button>'
        '<button type="button" id="chainStartBtn">התחל מימין</button>'
        '<button type="button" id="chainResetBtn">איפוס סימונים</button></motion_n">'
        '<motion_n">',
    )
    t = t.replace('</motion_n">', '</div><div id="main">', 1)
    # botched - let me read file and fix manually

print("aborting messy script")
