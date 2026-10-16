// Read-only inspection. currentConfigGroup only selects the group to read.
(function () {
    var activity = currentActivity();
    var result = {schema: 1, activity: activity, targets: []};
    var all = desktopsForActivity(activity);
    var wanted = ['SteamLibraryPath', 'WallpaperWorkShopId', 'WallpaperSource'];
    for (var i = 0; i < all.length; ++i) {
        var d = all[i];
        if (d.screen < 0) continue;
        var geo = screenGeometry(d.screen);
        var target = {containment: d.id, screen: d.screen, plugin: d.wallpaperPlugin,
                      geometry: {x: geo.x, y: geo.y, width: geo.width, height: geo.height},
                      values: {}};
        var previous = d.currentConfigGroup;
        try {
            d.currentConfigGroup = ['Wallpaper', d.wallpaperPlugin, 'General'];
            var keys = d.configKeys;
            for (var j = 0; j < wanted.length; ++j) {
                var key = wanted[j];
                var present = keys.indexOf(key) !== -1;
                target.values[key] = {present: present, value: present ? d.readConfig(key) : null};
            }
        } finally {
            d.currentConfigGroup = previous;
        }
        result.targets.push(target);
    }
    print(JSON.stringify(result));
})();
