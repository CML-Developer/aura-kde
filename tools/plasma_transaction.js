// REQUEST is injected as JSON, never interpolated executable text.
(function () {
    var keys = ['SteamLibraryPath', 'WallpaperWorkShopId', 'WallpaperSource'];
    var request = REQUEST;
    var targets = request.before.targets;
    var restore = request.restore;
    var resolved = [];
    var touched = [];
    function equal(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
    function value(d, key) {
        if (d.configKeys.indexOf(key) < 0) throw new Error('Missing key: ' + key);
        return d.readConfig(key);
    }
    function original(t, k) { return t.values[k].value; }
    function matchesIdentity(d, t) {
        var g = screenGeometry(d.screen), expected = t.geometry;
        return d.id === t.containment && d.screen === t.screen && d.wallpaperPlugin === t.plugin &&
            g.x === expected.x && g.y === expected.y && g.width === expected.width && g.height === expected.height;
    }
    try {
        if (currentActivity() !== request.before.activity) throw new Error('Activity changed');
        var desktopsNow = desktopsForActivity(currentActivity()).filter(function (d) { return d.screen >= 0; });
        if (desktopsNow.length !== 2) throw new Error('Screen count changed');
        // Preflight both destinations and every key before the first write.
        targets.forEach(function (t) {
            var d = desktopsNow.filter(function (d) { return d.id === t.containment; })[0];
            if (!d || !matchesIdentity(d, t)) throw new Error('Target identity changed');
            resolved.push({d: d, group: d.currentConfigGroup, t: t});
            d.currentConfigGroup = ['Wallpaper', t.plugin, 'General'];
            keys.forEach(function (k) {
                var actual = value(d, k), old = original(t, k), restored = request.restored[String(t.containment)][k];
                if (restore ? (!equal(actual, old) && !equal(actual, restored) && !equal(actual, request.proposed[k])) : (!equal(actual, old) && !equal(actual, restored)))
                    throw new Error('Conflict: ' + t.containment + '/' + k);
            });
        });
        resolved.forEach(function (entry) {
            keys.forEach(function (k) {
                var next = restore ? request.restored[String(entry.t.containment)][k] : request.proposed[k];
                var prior = value(entry.d, k);
                if (equal(prior, next)) return;
                var recovery = equal(prior, original(entry.t, k)) ? request.restored[String(entry.t.containment)][k] : prior;
                touched.push({d: entry.d, key: k, prior: prior, recovery: recovery, next: next});
                entry.d.writeConfig(k, next);
                if (!equal(value(entry.d, k), next)) throw new Error('Write verification failed');
            });
        });
        print(JSON.stringify({ok: true, restored: restore, writes: touched.length}));
    } catch (error) {
        var rollbackErrors = [];
        for (var i = touched.length - 1; i >= 0; --i) {
            var item = touched[i];
            try {
                var actual = value(item.d, item.key);
                if (equal(actual, item.next)) {
                    item.d.writeConfig(item.key, item.recovery);
                    if (!equal(value(item.d, item.key), item.recovery)) throw new Error('Rollback verification failed');
                } else if (!equal(actual, item.prior)) throw new Error('Rollback conflict');
            } catch (e) { rollbackErrors.push(String(e)); }
        }
        print(JSON.stringify({ok: false, error: String(error), rollbackErrors: rollbackErrors}));
    } finally {
        resolved.forEach(function (entry) { entry.d.currentConfigGroup = entry.group; });
    }
})();
