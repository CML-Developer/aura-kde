// REQUEST contains two complete, validated snapshots of the keys Aura owns for this operation.
(function () {
    var req = REQUEST, resolved = [], touched = [], switched = [];
    function equal(a,b) { return JSON.stringify(a) === JSON.stringify(b); }
    function read(d, plugin, key) {
        d.currentConfigGroup = ['Wallpaper', plugin, 'General'];
        var present = d.configKeys.indexOf(key) !== -1;
        var value = present ? d.readConfig(key) : null;
        // writeConfig(key,'') leaves the key present with '' in configKeys; normalize to absent.
        if (present && value === '') { present = false; value = null; }
        return {present: present, value: value};
    }
    function write(d, plugin, key, value) {
        d.currentConfigGroup = ['Wallpaper', plugin, 'General'];
        // For absent keys, write empty string; Plasma removes them on next read
        d.writeConfig(key, value.present ? value.value : '');
    }
    try {
        if (currentActivity() !== req.before.activity) throw Error('Activity changed');
        var desktops = desktopsForActivity(currentActivity()).filter(function(d) { return d.screen >= 0; });
        if (desktops.length < 1 || desktops.length > 3) throw Error('Screen count changed');
        req.before.targets.forEach(function(t, index) {
            var d = desktops.filter(function(d) { return d.id === t.containment; })[0];
            if (!d) throw Error('Desktop disappeared');
            var g = screenGeometry(d.screen);
            if (d.screen !== t.screen || d.wallpaperPlugin !== t.plugin ||
                g.x !== t.geometry.x || g.y !== t.geometry.y || g.width !== t.geometry.width || g.height !== t.geometry.height)
                throw Error('Target changed');
            var entry = {d: d, group: d.currentConfigGroup, before: t, after: req.after.targets[index], recovery: req.recovery.targets[index]};
            resolved.push(entry);
            Object.keys(t.groups).forEach(function(p) {
                Object.keys(t.groups[p]).forEach(function(k) {
                    if (!equal(read(d,p,k),t.groups[p][k])) throw Error('Conflict: '+d.id+'/'+p+'/'+k);
                });
            });
        });
        // Prepare destination groups while each original plugin is still active.
        resolved.forEach(function(e) {
            Object.keys(e.after.groups).forEach(function(p) {
                Object.keys(e.after.groups[p]).forEach(function(k) {
                    var old = e.before.groups[p][k], next = e.after.groups[p][k];
                    if (equal(old,next)) return;
                    touched.push({entry:e, plugin:p, key:k, old:old, next:next});
                    write(e.d,p,k,next);
                    if (!equal(read(e.d,p,k),next)) throw Error('Write verification failed');
                });
            });
        });
        resolved.forEach(function(e) {
            if (e.before.plugin !== e.after.plugin) {
                switched.push(e);
                e.d.wallpaperPlugin = e.after.plugin; // Actual activation occurs after script cleanup.
            }
        });
        print(JSON.stringify({ok:true, verification:'pending independent snapshot'}));
    } catch(error) {
        var rollbackErrors = [];
        switched.reverse().forEach(function(e) { e.d.wallpaperPlugin = e.before.plugin; });
        touched.reverse().forEach(function(w) {
            try {
                var actual=read(w.entry.d,w.plugin,w.key);
                if (equal(actual,w.next)) write(w.entry.d,w.plugin,w.key,w.entry.recovery.groups[w.plugin][w.key]);
                else if (!equal(actual,w.old)) throw Error('Rollback conflict');
            } catch(e) { rollbackErrors.push(String(e)); }
        });
        print(JSON.stringify({ok:false,error:String(error),rollbackErrors:rollbackErrors}));
    } finally {
        resolved.forEach(function(e) { e.d.currentConfigGroup=e.group; });
    }
})();
