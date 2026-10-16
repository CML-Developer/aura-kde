const fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
let state = input.state, output, failed = false, writes = [];
const ds = state.targets.map(t => {
    const d = {id:t.containment, screen:t.screen, currentConfigGroup:['Original'], pending:t.plugin,
        get wallpaperPlugin() { return this.pending; },
        set wallpaperPlugin(v) { this.pending = v; },
        get configKeys() { return Object.keys(t.groups[this.currentConfigGroup[1]]).filter(k => t.groups[this.currentConfigGroup[1]][k].present); },
        readConfig(k) { return t.groups[this.currentConfigGroup[1]][k].value; },
        writeConfig(k,v) {
            const p = this.currentConfigGroup[1];
            if (!(p in t.groups)) throw Error('writeConfig touched unknown plugin group');
            change(t,p,k, v === '' ? {present:false,value:null} : {present:true,value:v});
        }
    };
    return d;
});
function change(t,p,k,v) {
    if (input.fail && !failed && t.containment===2) { failed=true; throw Error('injected failure'); }
    writes.push([t.containment,p,k,v]); t.groups[p][k]=v;
}
function ConfigFile(parent,group) {
    const path = typeof parent === 'string' ? [group] : [...parent.path,group];
    function target() { return state.targets.find(t => String(t.containment) === path[1]); }
    return {path, writeEntry(k,v) {change(target(),path[3],k,{present:true,value:v});},
        deleteEntry(k) {change(target(),path[3],k,{present:false,value:null});}, sync() {}};
}
function currentActivity() {return state.activity;}
function desktopsForActivity() {return ds;}
function screenGeometry(screen) {return state.targets.find(t=>t.screen===screen).geometry;}
function print(x) {output=JSON.parse(x);}
eval(input.script);
const beforeCleanup=state.targets.map(t=>t.plugin);
for(let i=0;i<ds.length;i++) {
    if (JSON.stringify(ds[i].currentConfigGroup)!=='["Original"]') throw Error('Config group leaked');
    if (state.targets[i].plugin!==ds[i].pending && ds[i].pending==='org.kde.image')
        state.targets[i].groups['org.kde.image'].PreviewImage={present:true,value:'null'};
    state.targets[i].plugin=ds[i].pending;
}
process.stdout.write(JSON.stringify({state,output,writes,beforeCleanup}));
